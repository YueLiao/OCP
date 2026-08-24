# OCP-Agent 通用能力层设计方案

**副标题**: "OCP Agent API + code_plan 通用 skill" — 从 O(N) 固定 skill 转向 O(1) 通用底座

**状态**: proposal（待评审）

---

## 0. 问题与目标

### 现状
`agent/core.py` 的流程是: `parse_user_request` 把请求分类进固定的 8 个 skill 之一
（`SkillName` 枚举: instantiation / code_generation / visualization / differential /
linear / definition / dialogue / extraction），填参数后执行。

**LLM 的能力被这张菜单封顶。** 菜单外的需求做不了；每来一类新需求就要新增一个 skill
= O(N) 打地鼠，永远追不上"任何需求"。

两个真实例子暴露了两种缺口:
- **newLED = LED 换 Skinny Sbox**: 引擎零件全在（`led.py` + `skinny.py`），但没有"派生变体"的 skill —— **缺 skill**。
- **GIFT 10 轮差分 + 强制明文 MSB 有差分**: 引擎早就支持变量约束
  （`attacks/differential_cryptanalysis.py:49-51`: `['v_1_0_0 = 1', ...]`），
  但 agent 没把自然语言翻成变量约束 —— **参数没接通/没翻译**。

### 目标
用**一次架构投入**覆盖开放式需求，且**不牺牲可靠性**:
> 通用性在上层（LLM 规划 + 写代码），可靠性在底层（受控 API + 确定性验证）。

---

## 1. 设计原则

1. **可靠性光谱，能窄则窄**:
   `固定 skill（可靠/窄） → 参数化 skill → 受控 API 代码（curated/安全） → 自由 Python（通用/险）`。
   常见路径用可靠 skill；长尾需求落到"受控 API 代码"；**绝不开放裸 Python**。
2. **一切产物过验证闸门**: 密码 → KAT；分析 → 引擎实跑。不验证不持久化、不谎报"done"。
   （复用本项目已建的 persist-gate。）
3. **curated API 而非自由代码**: 既安全，LLM 也更容易写对（可调函数有限、文档齐全）。
4. **保留现有可靠 skill**: `code_plan` 是通用兜底，不是替代；常见路径仍走确定性 skill。
5. **代码可复现、可编辑**: 生成的代码写进 job record，用户可查/可改（类比现有的 Editable JSON）。

---

## 2. 架构总览

新增两个组件，复用一批已有零件。

```
用户消息
   │  parse_user_request
   ▼
 intent ──► 命中可靠 skill?  ──是──► 照旧执行（differential / instantiation / ...）
   │                          否
   ▼
 CODE_PLAN skill
   │  1. grounding: API 文档 + 相关密码源码(RAG) + few-shot
   ▼
 LLM 输出 {plan, code}   （code 只调 ocp_api.*）
   │  2. 受控命名空间执行（无 import / os / 文件 / dunder）
   ▼
 执行结果 / traceback
   │  3. 出错 → 喂 Tier-1a concise traceback → 自修（≤N 次）
   ▼
 4. 验证: 产出密码 → KAT；跑了分析 → 引擎已实跑
   ▼
 5. 通过 → 持久化/返回；否则诚实失败 + traceback
```

**复用的已有零件**: `safe_eval_program` 的沙箱思路、KAT/persist 闸门、
Tier-1a `_concise_traceback`、参考预言机、`extract_ocp_round_states`、
session/registry、`CIPHER_CATALOG`。

---

## 3. 组件 A — OCP Agent API（工具面）

一个 curated、全文档化的 facade 模块 `agent/ocp_api.py`，把现有 OCP 内部能力
包装成一组**纯函数、显式入参、无副作用（除显式 register）**的安全接口。
**这些 docstring 本身就是 LLM 的 grounding。**

### 3.1 目录与自省
```python
def list_ciphers() -> list[str]                      # 从 CIPHER_CATALOG + 自定义目录
def describe_cipher(name) -> dict                     # 版本/类型/轮数/组件概览
def get_cipher_spec(name, version=None) -> dict       # 可编辑的 spec dict
```

### 3.2 构造与改造
```python
def instantiate(name, version=None, rounds=None) -> cipher
def mutate_spec(base_spec, replace: dict, rename: str) -> spec
    # replace 支持: {"sbox": <table|已知盒名>, "permutation": [...],
    #                "matrix": [...], "rounds": n, "key_schedule": ...}
def build_from_spec(spec) -> cipher
def verify_kat(cipher, vectors=None) -> {"passed": p, "total": t, "all_passed": bool}
def register_cipher(spec) -> {"registered": bool, "path": ...}   # 仅在 KAT 通过后
```

### 3.3 分析
```python
def run_differential(cipher, goal="DIFFERENTIALPATH_PROB",
                     constraints=None, input_diff=None, output_diff=None,
                     model_type="milp", solver=None) -> trails
def run_linear(cipher, ...) -> trails
def inspect_trail(trails) -> dict
def inspect_round_states(cipher, inputs) -> list      # extract_ocp_round_states
```

### 3.4 约束编译器（语义 → 变量约束，本方案的关键翻译层）
```python
def active_bit(cipher, where="plaintext", index="MSB") -> "v_1_0_j = 1"
def fix_difference(cipher, where, hexmask) -> list[str]
def no_difference(cipher, where, index) -> "v_1_0_j = 0"
def at_least_active_sboxes(cipher, k) -> str          # 计数约束
```
这层把 `"MSB of plaintext has a difference"` 编译成引擎认识的
`v_1_0_<idx> = 1`（`<idx>` 从实例化后密码的状态几何算出），
覆盖"固定差分 / 某位无差分 / 至少 k 个活跃 S 盒"等常见语义。

### 3.5 属性约束
- 全部纯函数、显式入参；**无 os/文件/网络**。
- 每个返回结构化数据 + `verified`/`error` 字段。
- 完整 docstring（= grounding 来源）。

---

## 4. 组件 B — code_plan skill

新增 `SkillName.CODE_PLAN`。

```python
param_schema = {"task": "自然语言需求", "context": "可选补充"}
```

### execute() 步骤
1. **构建 grounded prompt**: task + `ocp_api` 的签名/docstring + （RAG）task 里点名的
   密码源码（如 `led.py`）+ 2~3 个 few-shot（task→plan→code）。
2. **LLM 返回** `{plan: [...], code: "<只调 ocp_api.* 的 python>"}`。
3. **受控执行**: 在一个命名空间里 `exec`，该命名空间**只注入** `ocp_api.*` + 安全 builtins，
   **去掉 `__builtins__`、禁 import、禁 dunder 属性、禁文件/os**。捕获返回值 + stdout + traceback。
4. **出错自修**: 附上 Tier-1a `_concise_traceback`，重提示让它改（≤N 次）。
5. **验证**: 产出密码 → `verify_kat`；跑了分析 → 引擎已实跑。持久化以验证为闸门。
6. **返回** SkillResult（summary + artifacts + 生成的 code 存 job record）。

### 安全模型（诚实说明）
- **不允许自由 Python**。执行器 = "curated 命名空间 exec": 只有 `ocp_api.*` 白名单可调，
  这是可靠性光谱里的"受控 API 代码"层 —— 足够编排多次 OCP 调用，又受限到安全。
- 这比 `safe_eval_program` 宽（后者禁 def、太窄，编排多步不够用），但比裸 exec 严
  （无 import/os/文件/dunder）。
- **更重的可选项**: 真正的子进程沙箱（进程隔离 + 资源限额）。留作 opt-in。

---

## 5. Grounding（提升 LLM 命中率 — 能力轴 A）

1. **注入 API docstring**（从 `ocp_api` 自动生成）。
2. **RAG 源码**: task 点名某密码 → 把它的 primitive 源码塞进上下文（"代码即真相"，BONC 教训）。
3. **Few-shot**: 覆盖"改造 + 约束分析"的 2~3 个范例。
4. **Agentic 自修循环**: traceback 反馈（复用 `_concise_traceback`）。

---

## 6. 三个走查（证明覆盖两例 + 长尾）

**newLED（改造）**
```
code_plan →
  spec = get_cipher_spec("LED")
  spec = mutate_spec(spec, replace={"sbox": "SKINNY_Sbox4"}, rename="newLED")
  c = build_from_spec(spec)
  verify_kat(c)          # 换了 Sbox 已非 LED，需新 KAT，否则标"未验证"
  register_cipher(spec)  # 仅 KAT 通过后
```

**GIFT 10 轮差分 + 强制 MSB**
```
code_plan →
  c = instantiate("GIFT", rounds=10)
  con = active_bit(c, "plaintext", "MSB")           # -> "v_1_0_j = 1"
  run_differential(c, constraints=["INPUT_NOT_ZERO", con])
```

**长尾（我从没预置过的需求）**: "比较 GIFT 与 newLED 在 8 轮下的活跃 S 盒数"
```
code_plan →
  for name in ["GIFT", "newLED"]:
      c = instantiate(name, rounds=8)
      t = run_differential(c, goal="DIFFERENTIAL_SBOXCOUNT")
      ... 汇总
```
**零新增 skill。** 这就是 O(1) 的意义。

---

## 7. 可靠性与守卫

- **验证闸门**（复用）: 未验证的密码不持久化。
- **约束校验**: 约束字符串在求解前先对照密码变量命名空间检查（拼错 → 明确报错，而非静默算错）。
- **改造守卫**: 沿用 repair 的硬约束到 `mutate_spec`（不改 test_vectors、不删混淆/扩散层）。
- **有界自修**（≤N）+ 诚实失败（带 traceback）。
- **可复现**: 生成的代码写进 job record，用户可查/可编辑/可重跑。

---

## 8. 分阶段落地（低风险、每阶段独立可交付）

| 阶段 | 内容 | 立即解锁 |
|---|---|---|
| **0** | `ocp_api.py` facade（包已有内部能力，不动引擎）+ 单测 | 基础 |
| **1** | 约束编译器（active_bit / fix_difference / at_least_active_sboxes） | GIFT/MSB 例（甚至走现有 differential skill 就行） |
| **2** | `mutate_spec` + register-with-KAT | newLED 例 |
| **3** | `code_plan` skill + 受控执行器 + grounding + 自修循环 | 长尾任意需求 |
| **4** | 无匹配可靠 skill 时优先 code_plan；常见路径仍走可靠 skill | 全面通用 |

每阶段各自可测、各自可上线，全程 KAT/引擎闸门。

---

## 9. 本方案刻意不做的

- **不开放自由任意 Python**（安全）—— 只给 curated API。
- **不替换现有可靠 skill**（常见路径保持确定性）。
- **不动 OCP 引擎**（只做 facade）；引擎级缺口（ARX 模加等，见 BONC 讨论）是另一件事。
- **不移除不可逆步骤的人工确认**（注册/持久化仍可要求确认）。

---

## 10. 待你拍板的开放问题

1. **执行器**: curated 命名空间 exec（轻）vs 子进程沙箱（更安全）？
2. **code_plan 是否自动执行**，还是先出示 plan+code 让用户确认（类比现有的 cipher draft 确认流）？
3. **RAG 注入多少源码**（token 预算）？

---

## 附: 与本项目已有哲学的一致性

本方案是用户反复强调原则的直接延伸:
> "预定义函数应通用/广用；当无合适预定义时，让 LLM 写代码（KAT 兜底）。"

- 通用件（instantiate/run_differential/约束编译器）= 预定义。
- 长尾 = LLM 写代码（受控 API）。
- KAT/引擎 = 兜底闸门。

参见 `memory/define-pipeline-hygiene.md` 的 GUIDING RULE 与 BONC 讨论（"代码即真相"）。
