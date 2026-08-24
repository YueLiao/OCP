# 上游合并工单（刷新版，基于真实三方合并模拟）

**生成日期**: 2026-08-24
**上游目标**: `upstream/main = 6157c8b`（"formating attacks and variables"，2026-07-31）
**fork 点**: `513963a`（"update operators"，2026-06-01）
**分叉**: agent +192 commit / upstream +11 commit
**数据来源**: 在 agent 仓库里 `git merge-tree --write-tree HEAD upstream/main` 的真实模拟
（已把 `../OCP` 加为 `upstream` remote）。

> 备注: `git fetch upstream` 无新增，GitHub 上游仍停在 6157c8b，**分叉 10 天来没有增长**
> （与旧 checklist 的 21/19/29 完全一致）。若之后 GitHub 再动，重跑
> `git fetch upstream && git merge-tree --write-tree --name-only HEAD upstream/main` 即可刷新。

---

## 0. 一页速览

| 桶 | 文件数 | 人工成本 |
|---|---|---|
| **git 自动合**（两边都动但不冲突） | 5 | 0（OCP.py, SHACAL2BooleanFunctions, matrix, modular_operators, rocca） |
| **AUTO-ADOPT**（仅上游动，直接采纳） | 19 | 低（导入/注册/回归） |
| **真冲突**（需手工） | 17 | 见下分级 |
| **modify/delete 决策** | 1 | 决策（speedy.py） |
| **only-agent**（仅 agent 动，无需处理） | 29 | 0 |

**核心 .py 冲突面 = 17 文件**，其中真正 HARD 只有 3 个。其余多是"一边巨改、另一边极小"→ 取大的一边 + 回贴小的一边。

---

## 1. 高价值：AUTO-ADOPT 的 19 个文件（净新能力，先吃）

仅上游改动、agent 没碰 → 直接采纳，风险低、价值高。其中包含**净新能力**:

**新分析驱动（agent 会因此获得新分析类型）**
- `attacks/integral_cryptanalysis.py`（16 个函数，two-subset 积分区分器）
- `attacks/impossible_differential.py`（不可能差分）
- `attacks/zero_corr_linear.py`（零相关线性）
- `tools/sbox_division_trails.py`（支撑积分）

**新密码（5 个）**
- `primitives/lblock.py` / `rectangle.py` / `simeck.py` / `siphash.py` / `twine.py`

**基础设施/`__init__`**
- `attacks/__init__.py`、`operators/__init__.py`、`primitives/__init__.py`、`solving/__init__.py`、
  `tools/__init__.py`、`variables/__init__.py`、`implementations/__init__.py`、
  `visualisations/__init__.py`、`visualisations/visualisations.py`、`implementations/implementations.py`

> 动作: 直接 checkout 上游版本 → 跑回归。注意 `__init__.py` 里新增的导出/注册要和 agent 的已有条目合并（这几个 `__init__` 也在冲突判定之外，通常干净）。

---

## 2. 真冲突文件（17 个），按难度分级

每个都标注**两侧改动规模** + **各自意图**。规律: 上游 = docstring/格式化 + 两个特性；agent = 标准化重构 + bugfix。

### 🟢 TRIVIAL（一侧极小，取大侧 + 回贴小侧改动）

| 文件 | 上游 | agent | 动作 |
|---|---|---|---|
| `primitives/aes.py` | +19/-6 | +7/-3 | 取上游 + 回贴 agent 少量 |
| `primitives/shacal2.py` | +1/-0 | +7/-1 | 取 agent + 并入上游 1 行 |
| `primitives/trivium.py` | +1/-0 | +7/-1 | 取 agent + 并入上游 1 行 |
| `attacks/attacks.py` | +128/-18 | +3/-2 | 取上游（新分析 dispatch）+ 回贴 agent 3 行 |
| `operators/operators.py` | +10/-3 | +459/-458 | 取 agent（大重构）+ graft 上游 10 行 |
| `tools/sat_search.py` | +10/-3 | +183/-186 | 取 agent + graft 上游 10 行 |

### 🟡 EASY–MEDIUM（上游多为 additive/格式化，agent 重构；对齐即可）

| 文件 | 上游 | agent | 说明 |
|---|---|---|---|
| `operators/Sbox.py` | +91/-0 | +285/-160 | 上游**纯新增**（线性+积分的 sbox 约束），agent 重构；additive 冲突少，逐块并入 |
| `operators/boolean_operators.py` | +14/-0 | +154/-185 | 上游 additive，取 agent + 并入 |
| `attacks/attack_trace.py` | +173/-83 | +32/-22 | 上游大幅格式化+特性，取上游 + 回贴 agent 小改 |
| `variables/variables.py` | +105/-29 | +17/-8 | 上游格式化，基础文件谨慎；取上游 + 回贴 agent |
| `tools/model_objective.py` | +17/-16 | +47/-25 | 中等，对齐目标函数处理 |

### 🟠 MEDIUM（两侧都实质改动 / 需 graft 新特性）

| 文件 | 上游 | agent | 说明 |
|---|---|---|---|
| `operators/AESround.py` | +36/-11 | +40/-26 | **已知项**: AESround S-box 规则（`GOAL_MODEL_VERSION_RULES`）；两侧中等 |
| `solving/solving.py` | +93/-13 | +225/-86 | **graft OR-Tools CPSAT 求解器**进 agent 已重构的 solving（槽位已 scaffold） |

### 🔴 HARD（3 个真难项，两侧都巨改 + 语义耦合）

| 文件 | 上游 | agent | 说明 |
|---|---|---|---|
| `tools/model_constraints.py` | +18/-48 | **+239/-647** | **B1 版本-配置解耦**（最难）。agent 做了标准化巨重构，上游要并入 two-subset 积分约束。冲突最重。 |
| `attacks/linear_cryptanalysis.py` | +148/-78 | +62/-214 | **A2 线性 ELP 共享助手**改动。agent 重构了约束/配置管线，上游改了 ELP 度量。 |
| `attacks/differential_cryptanalysis.py` | +146/-74 | +59/-210 | agent 重构（-210 行）vs 上游格式化+特性；与 A2 对称，一起做。 |

---

## 3. modify/delete 决策项

- **`primitives/speedy.py`**: 上游在 `a3c8d32` **删除**了（纯删，非改名），agent 有 SPEEDY 工作
  （bit-linear diffusion / MC，见 memory）。**建议: 保留 agent 版**（上游可能因不完整而删）。
  合并时选 "keep HEAD"。

---

## 4. 建议执行顺序（分批、每批可回归）

1. **批 1 · 轻量同步（几天，先做，解锁 core 优化 + harness 自省）**
   - AUTO-ADOPT 的 19 个文件全采纳（新分析 + 5 新密码 + `__init__`）。
   - 5 个 git 自动合文件让 git 处理。
   - 🟢 TRIVIAL 6 个 + speedy 决策。
   - 跑 core 回归 + agent 端到端。

2. **批 2 · 对齐 additive/格式化（🟡 EASY–MEDIUM 5 个）**
   - Sbox / boolean_operators / attack_trace / variables / model_objective。

3. **批 3 · graft 两个特性（🟠 MEDIUM）**
   - `operators/AESround.py`（AESround S-box 规则）
   - `solving/solving.py`（CPSAT 求解器）

4. **批 4 · 两个 HARD（B1 + A2）**
   - `tools/model_constraints.py`（B1 版本-配置解耦）
   - `attacks/linear_cryptanalysis.py` + `attacks/differential_cryptanalysis.py`（A2 线性 ELP + 差分对称重构）
   - 需最细的回归: 差分/线性 trail 对比（新旧结果一致性）。

**两个决策点**（旧 checklist 已标，仍需你拍板）:
- CardEnc: 硬失败 vs 警告。
- 线性 ELP 度量的取舍。

---

## 5. 工作量估计

- 批 1–2: ~2–3 天（多为采纳 + 小回贴 + 回归）。
- 批 3: ~1–2 天（两个特性 graft）。
- 批 4: ~3–5 天（3 个 HARD + trail 对比回归）。
- **合计 ~1–1.5 周**（含回归），与旧 checklist 估计一致 —— 因为分叉没增长。

> **对 harness 自省层的意义**: 只要**批 1**(采纳新分析驱动 + `gen_predefined_constraints`/`config_model`
> 所在的 tools 对齐) 完成，自省层照到的 OCP 面就是完整的（含积分/CPSAT/新密码），
> 不会 ground 在残缺面上。若暂不做积分分析,可只做批 1–2 就开始自省层,批 3–4 增量补 + 重跑自省。

---

## 附: 复现命令

```bash
cd OCP-agent
git remote add upstream ../OCP        # 已添加
git fetch upstream
git merge-tree --write-tree --name-only HEAD upstream/main   # 冲突文件清单
# 真实开合并:
git merge upstream/main               # 然后按本工单分批解冲突
```
