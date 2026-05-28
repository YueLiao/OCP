# OCP Wiki

Language: **English** | [中文](../zh-CN/README.md)

OCP models ciphers as graphs of variables and operators. Built-in primitives
construct these graphs round by round. Attack modules translate operators into
MILP/SAT constraints, solver modules search for solutions, and trail classes
format the resulting differential or linear characteristics.

OCP Agent adds a workflow layer around the core platform. It can parse user
requests through an LLM provider, execute structured skills, keep session state,
and expose the same capabilities through a direct Python API.

## Pages

- [Agent Guide](agent-guide.md)
- [Development and Standardization](development-and-standardization.md)
- [Standardization Report](standardization-report.md)
- [Agentic System Roadmap](agentic-system-roadmap.md)
- [Testing and CI](testing-and-ci.md)

## Typical Workflows

1. Instantiate a built-in cipher and run differential analysis.
2. Generate Python/C/SystemVerilog implementations and run test vectors.
3. Define a custom cipher with `CipherSpec`.
4. Parse a text-first cipher description into a draft specification.
5. Visualize a primitive or a trail.

## Installation Summary

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[agent,test]"
pip install -r requirements-solvers.txt    # optional solver/modeling backends
```

Solver packages are optional because different users may prefer Gurobi, SCIP,
PySAT, or only code generation without solving.
