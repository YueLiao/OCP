"""The declared operator capability surface stays in sync with the code."""

import inspect

import pytest

import variables.variables as var
from operators.boolean_operators import XOR
from operators.operators import Operator
from operators.Sbox import PRESENT_Sbox
from tools.operator_capabilities import describe_operators, consistency_report


def test_declarations_do_not_drift_from_code():
    # Every model_version a generate_model handles must be declared, and every
    # declared version must be recognised by the code (documented AST over-reports aside).
    report = consistency_report()
    assert report == {}, f"operator capability declarations drifted from code: {report}"


def test_core_operators_are_described_accurately():
    caps = describe_operators()

    # model_versions is now a {model_type: [versions]} map. INTEGRAL is MILP-only.
    assert "INTEGRAL_TWOSUBSET" in caps["XOR"]["model_versions"]["milp"]
    assert "INTEGRAL_TWOSUBSET" not in caps["XOR"]["model_versions"]["sat"]
    assert "XORDIFF_1" in caps["XOR"]["model_versions"]["sat"]

    # OR shares AND's helper but is guarded OUT of the integral model (no integral in either type).
    assert caps["OR"]["model_versions"]["sat"] == ["XORDIFF", "LINEAR"]
    assert caps["OR"]["model_versions"]["milp"] == ["XORDIFF", "LINEAR"]

    # Integral is MILP-only for the operators that support it; Shift has no integral at all.
    assert "INTEGRAL_TWOSUBSET" in caps["Equal"]["model_versions"]["milp"]
    assert "INTEGRAL_TWOSUBSET" in caps["Rot"]["model_versions"]["milp"]
    assert "INTEGRAL_TWOSUBSET" not in caps["Shift"]["model_versions"]["milp"]

    # ModAdd's indicator-constraint variants are MILP-only, not available under sat.
    assert "XORDIFF_1" in caps["ModAdd"]["model_versions"]["milp"]
    assert "XORDIFF_1" not in caps["ModAdd"]["model_versions"]["sat"]

    # Implementation coverage: Sbox now emits verilog (function + case), like XOR.
    assert "verilog" in caps["Sbox"]["implementations"]
    assert "verilog" in caps["XOR"]["implementations"]


def test_declared_surface_is_enforced_at_runtime():
    # The base-class guard rejects an undeclared model_version / implementation language,
    # so the declaration is the enforced single source of truth (not just documentation).
    i1, i2, out = var.Variable(4, ID="a"), var.Variable(4, ID="b"), var.Variable(4, ID="c")
    xor = XOR([i1, i2], [out])

    xor.model_version = "XOR_FAKEVERSION"
    with pytest.raises(ValueError, match="version XOR_FAKEVERSION not existing"):
        xor.generate_model("sat")

    xor.model_version = "XOR_XORDIFF"  # a declared version still works
    assert xor.generate_model("sat")

    # The guard is model-type aware: INTEGRAL_TWOSUBSET is declared for milp only.
    xor.model_version = "XOR_INTEGRAL_TWOSUBSET"
    with pytest.raises(ValueError, match="not existing for sat"):
        xor.generate_model("sat")
    assert xor.generate_model("milp")  # same version works under milp

    sbox = PRESENT_Sbox([var.Variable(4, ID="x")], [var.Variable(4, ID="y")], ID="S")
    with pytest.raises(ValueError, match="unknown implementation type 'vhdl'"):
        sbox.generate_implementation("vhdl")  # Sbox declares python/c/verilog only
    assert sbox.generate_implementation("verilog")  # a declared language now works


def _all_subclasses(cls):
    seen = {}
    stack = list(cls.__subclasses__())
    while stack:
        sub = stack.pop()
        if sub.__name__ not in seen:
            seen[sub.__name__] = sub
            stack.extend(sub.__subclasses__())
    return seen


def test_every_declared_operator_wires_the_capability_guards():
    # With the explicit approach, enforcement relies on each operator calling the guard.
    # This guarantees none is forgotten: every declared operator's own generators must call
    # the base-class guards at their top (so a new operator that skips them fails CI).
    classes = _all_subclasses(Operator)
    missing = []
    for name in describe_operators():
        cls = classes[name]
        gm = cls.__dict__.get("generate_model")
        gi = cls.__dict__.get("generate_implementation")
        if gm and "check_supported_model_version" not in inspect.getsource(gm):
            missing.append(f"{name}.generate_model")
        if gi and "check_supported_implementation" not in inspect.getsource(gi):
            missing.append(f"{name}.generate_implementation")
    assert not missing, f"operators missing the capability guard call: {missing}"
