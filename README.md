# OCP (Open Cryptanalysis Platform)

Language: **English** | [中文](README.zh-CN.md)

OCP is a Python research platform for modeling symmetric cryptographic
primitives, generating implementations, visualizing structures, and searching
for differential or linear trails with MILP/SAT backends.

This fork also includes **OCP Agent**, a conversational and programmatic layer
that can instantiate built-in ciphers, define custom ciphers from structured
specifications, parse text-first cipher descriptions, and run analysis
workflows.

Official upstream: https://github.com/Open-CP/OCP

## Repository Layout

| Path | Purpose |
|---|---|
| `variables/` | Variable nodes used in cipher graphs. |
| `operators/` | Boolean, modular, S-box, matrix, AES-round, and helper operators. |
| `primitives/` | Built-in cipher and permutation models. |
| `attacks/` | Differential and linear attack orchestration and trail formats. |
| `solving/` | MILP/SAT solver wrappers. |
| `implementations/` | Python/C/SystemVerilog code generation and implementation tests. |
| `visualisations/` | Structure and trail visualization helpers. |
| `tools/` | Constraint generation, objectives, resource monitoring, and utilities. |
| `agent/` | Conversational/API wrapper around OCP workflows. |
| `web/` | Flask web chat interface for OCP Agent. |
| `test/` | Unit, operator, implementation, and cryptanalysis tests. |
| `docs/wiki/` | Wiki-style documentation with language switch links. |

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For Agent and web UI features:

```bash
pip install -e ".[agent]"
```

Optional solver and modeling backends:

```bash
pip install -r requirements-solvers.txt
```

Classic requirements files are also available:

```bash
pip install -r requirements.txt
pip install -r requirements-agent.txt
```

Notes:

- `gurobipy` requires a valid Gurobi installation/license for MILP solving.
- `python-sat` is needed for SAT solving.
- `PyMuPDF` or `pdfplumber` is needed for PDF extraction.
- `pyeda`, `pycddlib`, and Espresso-related tooling are used by some constraint generation modes.

## Quick Start: Python API

```python
from agent import OCPAgent

agent = OCPAgent()
agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])

agent.generate_code(language="python", unroll=True, test=True)
agent.differential_analysis(model_type="milp")
agent.linear_analysis(model_type="sat")
```

The direct API does not require an LLM provider.

## Quick Start: CLI Agent

```bash
export OPENAI_API_KEY="sk-..."
python3 run_agent.py --provider openai

export DEEPSEEK_API_KEY="sk-..."
python3 run_agent.py --provider deepseek

export OPENAI_COMPATIBLE_API_KEY="key"
python3 run_agent.py --provider openai-compatible --base-url http://localhost:8000/v1

python3 run_agent.py --provider anthropic
python3 run_agent.py --provider gemini
python3 run_agent.py --provider ollama --model llama3
```

Example text-first prompt:

```text
Describe the following ARX cipher from this Markdown/LaTeX text:
x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1
x_1 \leftarrow (x_1 \lll 2) \oplus x_0
Then run differential cryptanalysis using MILP.
```

Text input is the preferred path for precise cipher extraction. PDF/image
extraction remains experimental because visual recognition can miss formulas,
tables, state layouts, and bit-index conventions.

## Quick Start: Web UI

```bash
pip install -r requirements-agent.txt
python3 web/app.py --port 5001
```

Open `http://localhost:5001`.

## Built-in Ciphers

The Agent catalog currently includes:

`speck`, `simon`, `aes`, `gift`, `present`, `skinny`, `ascon`, `chacha`,
`salsa`, `forro`, `led`, `siphash`, `shacal2`, `rocca`, `speedy`, `trivium`.

Supported primitive types vary by cipher: `permutation`, `blockcipher`, and
`keypermutation`.

## Custom Cipher Definition

```python
from agent import OCPAgent, CipherSpec, LayerSpec

spec = CipherSpec(
    name="TinyARX",
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

agent = OCPAgent()
agent.define_custom_cipher(spec)
agent.differential_analysis(model_type="milp")
```

## Generated Files

Runtime outputs are written under `files/` by default. This includes generated
implementations, MILP/SAT model files, trail JSON/TXT files, and visualization
PDFs.

Some modeling templates under `files/*_modeling/` are tracked because they
exist in upstream history. Do not remove them in drive-by cleanup; use a
dedicated migration if the project later decides to regenerate them on demand.

To redirect runtime artifacts:

```bash
export OCP_FILES_DIR=/tmp/ocp-files
```

## Validation

```bash
python -m compileall agent primitives attacks solving tools operators
python -m pytest

# Optional heavier suites:
python -m pytest --run-implementations
python -m pytest --run-solver

# Manual legacy operator experiments:
python test/operators/test_xor.py
```

Default pytest runs lightweight standardized tests. Script-style operator
experiments are always skipped under pytest because they are manual experiment
scripts. Generated implementation tests and solver-dependent cryptanalysis
tests are opt-in.

## Documentation

- [Wiki home](docs/wiki/README.md)
- [English wiki](docs/wiki/en/README.md)
- [中文 Wiki](docs/wiki/zh-CN/README.md)
- [Agent guide](agent/README.md)
