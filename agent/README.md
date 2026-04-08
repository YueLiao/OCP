# OCP Agent - Automated Cryptanalysis Assistant

OCP Agent 是一个对话式密码分析助手，支持通过自然语言或 Python API 自动化完成密码算法的分析。

## Quick Start

### 1. 安装依赖

```bash
# 必需
pip install numpy

# 选择一个 LLM provider（二选一）
pip install openai       # 使用 OpenAI GPT
pip install anthropic    # 使用 Anthropic Claude

# 可选（用于 MILP/SAT 求解）
pip install gurobipy     # Gurobi MILP solver
pip install python-sat   # SAT solver
```

### 2. 启动对话

```bash
cd /path/to/OCP

# 使用 OpenAI
export OPENAI_API_KEY="sk-xxx"
python3 run_agent.py

# 使用 Claude
export ANTHROPIC_API_KEY="sk-ant-xxx"
python3 run_agent.py --provider anthropic

# 指定模型
python3 run_agent.py --model gpt-4o-mini
python3 run_agent.py --provider anthropic --model claude-sonnet-4-20250514

# 使用本地/自定义 OpenAI 兼容 API
python3 run_agent.py --base-url http://localhost:8000/v1
```

启动后进入交互式对话：

```
============================================================
  OCP Agent - Automated Cryptanalysis Assistant
============================================================
Commands: 'quit'/'exit' to leave, 'reset' to clear session

You>
```

---

## 对话示例

### 示例 1：分析已有算法

```
You> 分析 SPECK32/64 的差分特性，用 MILP

Assistant> 已创建 SPECK32_64（22轮分组密码），正在运行差分分析...
           差分分析完成：找到 1 条最优路径。

You> 再用 SAT 做线性分析

Assistant> 线性分析 (SAT) 完成：找到 1 条最优线性路径。

You> 生成 Python 代码

Assistant> 已生成 files/SPECK32_64.py，测试通过 (1/1)。
```

### 示例 2：定义并分析全新的密码算法

```
You> 我设计了一个新的 ARX 密码叫 TinyARX，块大小 32 bit，
     分成 2 个 16-bit 的字，共 10 轮。
     每轮操作：字0右旋7位，字0和字1模加存字0，字1左旋2位，字0和字1异或存字1。
     帮我做差分分析。

Assistant> 已解析你的密码 TinyARX:
           - permutation, 32-bit, 2×16-bit words, 10 rounds
           - ROT_R(w0,7) → MODADD(w0,w1→w0) → ROT_L(w1,2) → XOR(w0,w1→w1)
           构建成功，正在分析...
           差分分析完成：找到最优差分路径。
```

### 示例 3：分步引导定义复杂密码

如果描述不够完整，agent 会分步引导你：

```
You> 我有一个新的 SPN 密码想分析

Assistant> 我需要以下基本信息：
           1. 密码名称
           2. 类型: permutation 还是 blockcipher
           3. 块大小 (bits)
           4. 字大小 (bits)
           5. 字的数量
           6. 轮数

You> 叫 MySPN，permutation，64 bit，bit 级别所以字大小 1 bit，64 个字，8 轮

Assistant> 你的密码用 S-box 吗？请提供 S-box 名称和查找表。

You> 用 PRESENT 的 S-box: [0xC,0x5,0x6,0xB,0x9,0x0,0xA,0xD,0x3,0xE,0xF,0x8,0x4,0x7,0x1,0x2]

Assistant> 请描述轮函数的操作。

You> 先做 S-box，每 4 bit 一组，然后做 bit 置换 [0,4,8,12,1,5,9,13,...]

Assistant> 已构建 MySPN:
           - S-box layer (PRESENT S-box, 4-bit groups)
           - Permutation layer
           确认？

You> 确认

Assistant> MySPN_PERM 构建成功！需要做什么分析？

You> 差分和线性都做一下

Assistant> 差分分析完成... 线性分析完成...
```

---

## Python API 使用

不需要 LLM，直接在代码中调用：

### 分析已有算法

```python
from agent import OCPAgent

agent = OCPAgent()

# 创建密码实例
agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])

# 生成代码
agent.generate_code(language="python", unroll=True, test=True)

# 生成可视化
agent.generate_visualization()

# 差分分析
result = agent.differential_analysis(goal="DIFFERENTIALPATH_PROB", model_type="milp")

# 线性分析
result = agent.linear_analysis(goal="LINEARPATH_CORR", model_type="sat")
```

### 定义并分析自定义密码

```python
from agent import OCPAgent, CipherSpec, LayerSpec

agent = OCPAgent()

# 定义密码结构
spec = CipherSpec(
    name="MyARX",
    cipher_type="permutation",
    block_size=32,
    word_bitsize=16,
    nbr_words=2,
    nbr_rounds=10,
    round_structure=[
        LayerSpec("rotation", {"direction": "r", "amount": 7, "word_index": 0}),
        LayerSpec("modadd", {"input_indices": [[0, 1]], "output_indices": [0]}),
        LayerSpec("rotation", {"direction": "l", "amount": 2, "word_index": 1}),
        LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]}),
    ],
)

# 构建并分析
agent.define_custom_cipher(spec)
agent.differential_analysis(model_type="milp")
agent.linear_analysis(model_type="sat")
agent.generate_code(language="python")
```

### 带 S-box 的 SPN 密码

```python
from agent import OCPAgent, CipherSpec, LayerSpec

PRESENT_SBOX = [0xC,0x5,0x6,0xB,0x9,0x0,0xA,0xD,0x3,0xE,0xF,0x8,0x4,0x7,0x1,0x2]
PRESENT_PERM = [0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15] * 4  # 64-bit

spec = CipherSpec(
    name="MySPN",
    cipher_type="permutation",
    block_size=64,
    word_bitsize=1,       # bit-level
    nbr_words=64,
    nbr_rounds=8,
    sbox_tables={"my_sbox": PRESENT_SBOX},
    round_structure=[
        LayerSpec("sbox", {
            "sbox_name": "my_sbox",
            "index": [list(range(i, i+4)) for i in range(0, 64, 4)],
        }),
        LayerSpec("permutation", {"table": PRESENT_PERM}),
    ],
)

agent = OCPAgent()
agent.define_custom_cipher(spec)
agent.differential_analysis(model_type="milp")
```

---

## 支持的操作

### 已有算法 (17种)
speck, aes, gift, simon, present, skinny, ascon, chacha, salsa, forro, led, siphash, shacal2, rocca, speedy, trivium

### 自定义密码支持的层类型
| 层类型 | 说明 | 参数 |
|--------|------|------|
| `rotation` | 循环移位 | direction, amount, word_index |
| `xor` | 异或 | input_indices, output_indices |
| `modadd` | 模加 | input_indices, output_indices |
| `sbox` | S-box 替换 | sbox_name, index |
| `permutation` | 置换 | table |
| `matrix` | 矩阵乘法 | matrix, indices, polynomial |
| `add_round_key` | 轮密钥加 | operator, mask |
| `add_constant` | 常量加 | add_type, constant_mask, constant_table |

### 分析功能
| 功能 | 方法 | 求解器 |
|------|------|--------|
| 差分分析 | `differential_analysis()` | MILP, SAT |
| 线性分析 | `linear_analysis()` | MILP, SAT |
| 代码生成 | `generate_code()` | Python, C, Verilog |
| 可视化 | `generate_visualization()` | PDF |

### 分析目标
- 差分: `DIFFERENTIALPATH_PROB`, `DIFFERENTIAL_SBOXCOUNT`, `DIFFERENTIAL_PROB`, `TRUNCATEDDIFF_SBOXCOUNT`
- 线性: `LINEARPATH_CORR`, `LINEAR_SBOXCOUNT`, `LINEARHULL_CORR`, `TRUNCATEDLINEAR_SBOXCOUNT`
