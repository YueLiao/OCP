# OCP Agent - Automated Cryptanalysis Assistant

OCP Agent is a conversational cryptanalysis assistant that automates cipher analysis, code generation, and visualization through natural language or a Python API.

## Quick Start

### 1. Install Dependencies

```bash
# Required
pip install numpy matplotlib kiwisolver

# Choose an LLM provider (pick one)
pip install openai       # OpenAI GPT
pip install anthropic    # Anthropic Claude
pip install google-genai # Google Gemini
pip install ollama       # Ollama (local models, no API key needed)

# Optional (for MILP/SAT solvers)
pip install gurobipy     # Gurobi MILP solver
pip install python-sat   # SAT solver
pip install ortools      # Google OR-Tools
```

### 2. Launch the CLI

```bash
cd /path/to/OCP

# OpenAI
export OPENAI_API_KEY="sk-xxx"
python3 run_agent.py

# Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-xxx"
python3 run_agent.py --provider anthropic

# Google Gemini
export GOOGLE_API_KEY="AIza..."
python3 run_agent.py --provider gemini

# Ollama (local models, no API key needed)
python3 run_agent.py --provider ollama
python3 run_agent.py --provider ollama --model qwen2.5

# Specify a model
python3 run_agent.py --model gpt-4o-mini
python3 run_agent.py --provider anthropic --model claude-sonnet-4-20250514
python3 run_agent.py --provider gemini --model gemini-2.5-flash
python3 run_agent.py --provider ollama --model llama3

# Use a local/custom OpenAI-compatible endpoint
python3 run_agent.py --base-url http://localhost:8000/v1
```

Once launched, you enter an interactive session:

```
============================================================
  OCP Agent - Automated Cryptanalysis Assistant
============================================================
Commands: 'quit'/'exit' to leave, 'reset' to clear session

You>
```

---

## Dialogue Examples

### Example 1: Analyze an Existing Cipher

```
You> Analyze SPECK32/64 with differential cryptanalysis using MILP

Assistant> Created SPECK32_64 (22-round block cipher). Running differential analysis...
           Differential analysis complete: found 1 optimal trail.

You> Now run linear analysis with SAT

Assistant> Linear analysis (SAT) complete: found 1 optimal linear trail.

You> Generate Python code

Assistant> Generated files/SPECK32_64.py. Tests passed (1/1).
```

### Example 2: Define and Analyze a New Custom Cipher

```
You> I designed a new ARX cipher called TinyARX. Block size 32 bits,
     split into 2 words of 16 bits each, 10 rounds.
     Each round: rotate word 0 right by 7, modular add words 0 and 1 into word 0,
     rotate word 1 left by 2, XOR words 0 and 1 into word 1.
     Run differential analysis on it.

Assistant> Parsed your cipher TinyARX:
           - permutation, 32-bit, 2x16-bit words, 10 rounds
           - ROT_R(w0,7) -> MODADD(w0,w1->w0) -> ROT_L(w1,2) -> XOR(w0,w1->w1)
           Built successfully. Running analysis...
           Differential analysis complete: found optimal differential trail.
```

### Example 3: Step-by-Step Guided Cipher Definition

If the description is incomplete, the agent guides you through each step:

```
You> I have a new SPN cipher I'd like to analyze

Assistant> I need the following basic information:
           1. Cipher name
           2. Type: 'permutation' or 'blockcipher'
           3. Block size (bits)
           4. Word size (bits)
           5. Number of words
           6. Number of rounds

You> It's called MySPN, permutation, 64-bit, bit-level so word size is 1 bit,
     64 words, 8 rounds

Assistant> Does your cipher use S-boxes? If so, please provide the name and lookup table.

You> Yes, use the PRESENT S-box: [0xC,0x5,0x6,0xB,0x9,0x0,0xA,0xD,0x3,0xE,0xF,0x8,0x4,0x7,0x1,0x2]

Assistant> Now describe the round function operations.

You> First apply the S-box in 4-bit groups, then a bit permutation [0,4,8,12,1,5,9,13,...]

Assistant> Here is the cipher specification:
           - S-box layer (PRESENT S-box, 4-bit groups)
           - Permutation layer
           Confirm?

You> Confirm

Assistant> MySPN_PERM built successfully! What analysis would you like to run?

You> Both differential and linear

Assistant> Differential analysis complete... Linear analysis complete...
```

### Example 4: Extract Cipher from a PDF Paper

```
You> Analyze the cipher described in /path/to/paper.pdf

Assistant> Loaded PDF file: paper.pdf. Extracting cipher specification...
           Extracted cipher "NewCipher": permutation, 128-bit, 4x32-bit words, 20 rounds.
           Building cipher... Built successfully.
           What analysis would you like to run?

You> Differential analysis with MILP

Assistant> Differential analysis complete: found 1 optimal trail.
```

You can also specify a section or page range:
```
You> Extract the cipher from pages 3-5 of /path/to/paper.pdf, focus on the KATAN cipher
```

Supported file formats: PDF (.pdf), images (.png, .jpg), plain text (.txt).

---

## Python API

No LLM required -- call the API directly from your code:

### Analyze an Existing Cipher

```python
from agent import OCPAgent

agent = OCPAgent()

# Instantiate a cipher
agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])

# Generate code
agent.generate_code(language="python", unroll=True, test=True)

# Generate visualization
agent.generate_visualization()

# Differential analysis
result = agent.differential_analysis(goal="DIFFERENTIALPATH_PROB", model_type="milp")

# Linear analysis
result = agent.linear_analysis(goal="LINEARPATH_CORR", model_type="sat")
```

### Define and Analyze a Custom Cipher

```python
from agent import OCPAgent, CipherSpec, LayerSpec

agent = OCPAgent()

# Define the cipher structure
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

# Build and analyze
agent.define_custom_cipher(spec)
agent.differential_analysis(model_type="milp")
agent.linear_analysis(model_type="sat")
agent.generate_code(language="python")
```

### SPN Cipher with S-box

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

### Extract Cipher from a PDF Paper

```python
from agent import OCPAgent
from agent.llm.openai_provider import OpenAIProvider

agent = OCPAgent(llm_provider=OpenAIProvider(api_key="sk-xxx"))

# Extract cipher from a PDF and auto-build
agent.extract_cipher_from_file(
    "path/to/crypto_paper.pdf",
    focus="the new lightweight cipher in Section 3",
    pages="3-6",
    auto_build=True,
)

# Now analyze
agent.differential_analysis(model_type="milp")
agent.generate_code(language="python")
```

Supported file formats: PDF (requires `pip install PyMuPDF`), images (PNG/JPG), plain text.

---

## Reference

### Supported Built-in Ciphers (17)
speck, aes, gift, simon, present, skinny, ascon, chacha, salsa, forro, led, siphash, shacal2, rocca, speedy, trivium

### Custom Cipher Layer Types
| Layer Type | Description | Parameters |
|------------|-------------|------------|
| `rotation` | Cyclic rotation | direction, amount, word_index |
| `xor` | Bitwise XOR | input_indices, output_indices |
| `modadd` | Modular addition | input_indices, output_indices |
| `sbox` | S-box substitution | sbox_name, index |
| `permutation` | Bit/word permutation | table |
| `matrix` | Matrix multiplication | matrix, indices, polynomial |
| `add_round_key` | Round key addition | operator, mask |
| `add_constant` | Constant addition | add_type, constant_mask, constant_table |

### Analysis Capabilities
| Feature | Method | Solvers |
|---------|--------|---------|
| Differential analysis | `differential_analysis()` | MILP, SAT |
| Linear analysis | `linear_analysis()` | MILP, SAT |
| Code generation | `generate_code()` | Python, C, Verilog |
| Visualization | `generate_visualization()` | PDF |

### Analysis Goals
- **Differential:** `DIFFERENTIALPATH_PROB`, `DIFFERENTIAL_SBOXCOUNT`, `DIFFERENTIAL_PROB`, `TRUNCATEDDIFF_SBOXCOUNT`
- **Linear:** `LINEARPATH_CORR`, `LINEAR_SBOXCOUNT`, `LINEARHULL_CORR`, `TRUNCATEDLINEAR_SBOXCOUNT`
