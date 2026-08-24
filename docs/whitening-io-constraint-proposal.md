# 方向 B 设计提案：让 IO 约束支持"带子密钥的 XOR"以在轮外表达 whitening

## 目标

把 whitening（轮外的轮密钥加）表达为 primitive 的输入/输出连接本身，而不是占用一整轮：

- pre-whitening：`plaintext ⊕ WK` 进入第一轮的输入（FUTURE：`S = X ⊕ K0`）。
- post-whitening：最后一轮的输出 `⊕ WK` 成为密文（PRESENT：末尾加 `K_32`）。

这样 `nbr_rounds` 保持论文真实轮数，不虚增、不浪费 layer slot。对比方向 A（whitening = 额外一轮）见文末权衡。

## 现有机制（精确）

- IO 约束在 `Primitive` 里用 `Equal` 建立：
  - `_append_input_links`（primitives.py:327）：`op.Equal([external], [func_var])`
  - `_append_output_links`（primitives.py:331）：`op.Equal([func_var], [external])`
- `Block_cipher.__init__`（primitives.py:479）的连接：
  - 明文 → PERMUTATION 第 1 轮输入（:490）
  - 密钥 → KEY_SCHEDULE 第 1 轮输入（:493）
  - PERMUTATION 末轮输出 → 密文（:496）
- **代码生成绕过 IO 约束**：`generate_implementation`（implementations.py:94-106）并不遍历 `inputs_constraints`，而是直接把 primitive 输入赋给函数首层变量（`func_var = input[w]`），输出同理直接 `output[w] = func_var`。也就是说 codegen **假设** IO link 一定是 Equal。
- `clean_graph`（primitives.py:350-380）只把纯 Equal 链标记为 ghost；XOR 约束天然保留，不会被清理。

## 设计

### 1. 约束层：新增带子密钥的 IO link

在 `Primitive` 加两个方法（与现有 `_append_input_links`/`_append_output_links` 并列）：

- `_append_input_links_xor(external_vars, key_vars, function_vars, id_prefix)`
  生成 `op.XOR([external_var, key_var], [function_var])`（逐 word）。
- `_append_output_links_xor(function_vars, key_vars, external_vars, id_prefix)`
  生成 `op.XOR([function_var, key_var], [external_var])`。

`Block_cipher.__init__` 增加两个可选参数 `pre_whitening_keys` / `post_whitening_keys`（各为一组 word 变量，长度 = 状态字数，`None` 表示无）。当提供时，对应的 IO 连接改用 XOR 变体：

```
if pre_whitening_keys is None:
    self._append_input_links(p_input, PERM.vars[1][0], "IN_LINK_P_EQ_")
else:
    self._append_input_links_xor(p_input, pre_whitening_keys, PERM.vars[1][0], "IN_LINK_P_XOR_")
# 输出侧同理
```

### 2. whitening key 变量的来源（两类）

- **直接来自 key input**（FUTURE：`WK = K0` = 密钥高 64 位）：
  `key_vars` 直接取 `k_input` 的对应切片。零额外提取，最干净。
- **来自 key schedule 演化**（PRESENT：`K_32` 是密钥编排迭代出的最后一个子密钥）：
  需要 `SUBKEYS` 多提取一个"轮外子密钥"。做法是让 `SUBKEYS`/`KEY_SCHEDULE` 比 round function 多一个提取点（pre 用"第 0 轮"、post 用"第 nbr_rounds+1 轮"的 KS 状态），`key_vars` 指向该提取变量。注意：这仍是一次额外提取，但**不占 round function 的轮**，因此不虚增 `nbr_rounds`。

### 3. 各消费点的改动

| 消费点 | 改动 | 风险 |
|---|---|---|
| **codegen**（implementations.py，python/c/verilog 各一处 input + 一处 output，unroll 与 loop 两模式） | IO 生成不能再无条件直接赋值，需遍历 `inputs_constraints`/`outputs_constraints` 按类型分派：`Equal → func = input`；`XOR → func = input ^ key`。 | 中：三语言 × 两模式共 ~12 处，机械但面广 |
| **evaluate** | 走生成代码，codegen 改对即随之正确；若有独立解释路径需同步 | 低 |
| **分析后端**（SAT / MILP / 差分 / 线性 / 不可能差分等） | 各后端遍历约束图建模。IO 位置现在多了 XOR 约束。多数后端已支持 XOR operator，但需确认它们**确实遍历** `inputs_constraints`/`outputs_constraints`（而非像 codegen 那样绕过）。差分语义：`Δ(x⊕k)=Δx`（密钥差分为 0 时透明）；值/密钥恢复需包含该 XOR。 | **高**：OCP 的核心价值在分析，IO 约束类型变化波及所有分析路径，回归面最大 |
| **clean_graph** | XOR 不被 ghost（现逻辑只清 Equal），天然兼容；需确认 whitening key 变量不被误清 | 低 |
| **build_dictionaries** | 已收集 `inputs_constraints`/`outputs_constraints`（primitives.py:345-348）；key_vars 若来自 key input 已在 inputs、若来自 SUBKEYS 已在函数变量中 | 低 |

### 4. 需要先做的调研（落地前）

1. 盘点**每个分析后端**对 `inputs_constraints`/`outputs_constraints` 的处理：是遍历建模，还是像 codegen 一样绕过？绕过的后端在 IO-XOR 下会**静默丢失** whitening，属正确性隐患。
2. 确认 `XOR` operator 在 IO 图位置（跨"外部变量 + 函数变量 + 子密钥变量"）能被各后端的变量绑定正确识别。
3. 确认差分/线性搜索把 whitening key 当作差分为 0 的独立密钥变量（不进入路径权重），值恢复/自动化搜索则纳入。

## 与方向 A 的权衡

| | 方向 A（额外一轮） | 方向 B（IO-XOR，本提案） |
|---|---|---|
| 核心改动 | 无（复用 ARK 层 + identity 层 + `except_rounds`） | Primitive/Block_cipher IO + codegen 三语言 + 各分析后端 |
| 分析后端 | 天然支持（普通层） | 每个都需适配 IO-XOR，风险最大 |
| `nbr_rounds` 语义 | +1（用户无感，readback 已区分） | 论文真实值 |
| slot | 白化轮的非 ARK 层为 identity | 无浪费 |
| 已验证 | 已落地，FUTURE/PRESENT 可用 | 未实施 |

## 推荐

**方向 A 已足够**：功能等价、用户无感、对所有分析后端零改动零风险，`readback` 也已把额外轮标注为 whitening 而非普通轮。

方向 B 语义上最纯净（whitening 本就在轮外），但其代价集中在"让每一条分析路径都理解一种新的 IO 约束类型"，而这正是 OCP 最有价值也最不该引入静默错误的部分。建议仅在出现明确收益（例如某种分析对轮数语义敏感、额外轮会污染结果）时再推进，且必须先完成上文第 4 节的分析后端盘点。

若要落地，推荐顺序：先只做**来源 a（whitening key 直接取自 key input，如 FUTURE）+ 仅 codegen/evaluate 路径**做一个受限原型，用 FUTURE 完整 KAT 验证 IO-XOR 的值语义正确；再逐个分析后端盘点接入。切忌一次性全后端改动。
