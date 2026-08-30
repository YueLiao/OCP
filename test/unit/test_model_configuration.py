"""Unit tests for tools/model_configuration.py - scope filling, per-operator model-version
assignment (goal rules + overrides), round constraint/objective generation, and the
attack-search config defaults. Fake operators drive the class-name-based version matching.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import model_configuration as mc


class _Op:
    """Fake operator/constraint; its class name drives version matching."""

    def __init__(self, model_out=None, weight=None):
        self._model_out = list(model_out or [])
        if weight is not None:
            self.weight = weight

    def generate_model(self, model_type, **params):
        self._last_params = params
        return list(self._model_out)


class XOR(_Op):
    pass


class PRESENT_Sbox(_Op):  # class name ends with "Sbox" -> matched by the "Sbox" rule
    pass


class AESround(_Op):  # matched by the exact-class-name "AESround" rule
    pass


def _cipher_one_layer():
    """A 1-function / 1-round / 1-layer cipher with [XOR, PRESENT_Sbox] plus I/O XORs."""
    xor, sbox = XOR(), PRESENT_Sbox()
    fn = SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: [xor, sbox]}})
    cipher = SimpleNamespace(
        name="toy", nbr_rounds=1, functions={"P": fn},
        inputs_constraints=[XOR()], outputs_constraints=[XOR()],
    )
    return cipher, xor, sbox


_FULL_SCOPE = {"functions": ["P"], "rounds": {"P": [1]}, "layers": {"P": {1: [0]}}, "positions": {"P": {1: {0: [0, 1]}}}}


# ------------------------------ normalize_model_type ------------------------------
@pytest.mark.parametrize("raw,expected", [("milp", "milp"), ("MILP", "milp"), ("SaT", "sat"), ("sat", "sat")])
def test_normalize_model_type_lowercases_valid(raw, expected):
    assert mc.normalize_model_type(raw) == expected


def test_normalize_model_type_rejects_unknown():
    with pytest.raises(ValueError, match="Invalid model_type"):
        mc.normalize_model_type("cnf")


# ------------------------------ normalize_solution_number ------------------------------
def test_normalize_solution_number_accepts_positive_int():
    assert mc.normalize_solution_number(5) == 5


@pytest.mark.parametrize("bad", [0, -1, "5", 2.0])
def test_normalize_solution_number_rejects_non_positive_int(bad):
    with pytest.raises(ValueError, match="Invalid solution_number"):
        mc.normalize_solution_number(bad)


# ------------------------------ default_model_filename ------------------------------
def test_default_model_filename_encodes_scope_and_backend_suffix(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    cipher = SimpleNamespace(nbr_rounds=3, name="toy")

    milp = mc.default_model_filename(cipher, "DIFFERENTIAL_SBOXCOUNT", "EXISTENCE", "milp")
    sat = mc.default_model_filename(cipher, "DIFFERENTIAL_SBOXCOUNT", "EXISTENCE", "sat")

    assert Path(milp).parent == tmp_path
    assert "3round_toy_DIFFERENTIAL_SBOXCOUNT_EXISTENCE" in milp and milp.endswith("milp_model.lp")
    assert sat.endswith("sat_model.cnf")


# ------------------------------ fill_functions_rounds_layers_positions ------------------------------
def test_fill_scope_expands_to_full_coverage_when_none():
    fn = SimpleNamespace(nbr_rounds=2, nbr_layers=1, constraints={1: {0: [0], 1: [0, 0]}, 2: {0: [0], 1: [0, 0]}})
    cipher = SimpleNamespace(functions={"P": fn})

    functions, rounds, layers, positions = mc.fill_functions_rounds_layers_positions(cipher)

    assert functions == ["P"]
    assert rounds == {"P": [1, 2]}
    assert layers == {"P": {1: [0, 1], 2: [0, 1]}}
    assert positions == {"P": {1: {0: [0], 1: [0, 1]}, 2: {0: [0], 1: [0, 1]}}}


def test_fill_scope_keeps_user_supplied_values_and_fills_downstream():
    fn = SimpleNamespace(nbr_rounds=2, nbr_layers=0, constraints={1: {0: [0, 0]}, 2: {0: [0, 0]}})
    cipher = SimpleNamespace(functions={"P": fn})

    _, rounds, layers, positions = mc.fill_functions_rounds_layers_positions(cipher, functions=["P"], rounds={"P": [1]})

    assert rounds == {"P": [1]}                        # user value kept
    assert layers == {"P": {1: [0]}}                   # only round 1 filled downstream
    assert positions == {"P": {1: {0: [0, 1]}}}        # len(constraints[1][0]) == 2


# ------------------------------ set_model_versions ------------------------------
def test_set_model_versions_assigns_all_when_operator_name_none():
    cipher, xor, sbox = _cipher_one_layer()

    mc.set_model_versions(cipher, "XORDIFF", ["P"], {"P": [1]}, {"P": {1: [0]}}, None)

    assert xor.model_version == "XOR_XORDIFF"
    assert sbox.model_version == "PRESENT_Sbox_XORDIFF"
    assert cipher.inputs_constraints[0].model_version == "XOR_XORDIFF"
    assert cipher.outputs_constraints[0].model_version == "XOR_XORDIFF"


def test_set_model_versions_targets_only_sbox_operators():
    cipher, xor, sbox = _cipher_one_layer()

    mc.set_model_versions(cipher, "XORDIFF_A", ["P"], {"P": [1]}, {"P": {1: [0]}}, None, operator_name="Sbox")

    assert sbox.model_version == "PRESENT_Sbox_XORDIFF_A"
    assert not hasattr(xor, "model_version")  # non-Sbox operator untouched


# ------------------------------ configure_model_version ------------------------------
def test_configure_model_version_rejects_missing_scope():
    cipher, _, _ = _cipher_one_layer()
    with pytest.raises(ValueError, match="missing required scope keys"):
        mc.configure_model_version(cipher, "DIFFERENTIAL_SBOXCOUNT", {"functions": ["P"]})


def test_configure_model_version_rejects_invalid_goal():
    cipher, _, _ = _cipher_one_layer()
    with pytest.raises(ValueError, match="Invalid goal"):
        mc.configure_model_version(cipher, "NOPE", dict(_FULL_SCOPE))


def test_configure_model_version_applies_goal_rules():
    cipher, xor, sbox = _cipher_one_layer()

    mc.configure_model_version(cipher, "DIFFERENTIAL_SBOXCOUNT", dict(_FULL_SCOPE))

    assert xor.model_version == "XOR_XORDIFF"              # (XORDIFF, None)
    assert sbox.model_version == "PRESENT_Sbox_XORDIFF_A"  # (XORDIFF_A, "Sbox") wins for the S-box


def test_configure_model_version_named_override_beats_wildcard():
    cipher, xor, sbox = _cipher_one_layer()
    scope = dict(_FULL_SCOPE, model_version={None: "AAA", "Sbox": "BBB"})

    mc.configure_model_version(cipher, "DIFFERENTIAL_SBOXCOUNT", scope)

    # wildcard None applied first (both AAA), then the Sbox override lands only on the S-box
    assert xor.model_version == "XOR_AAA"
    assert sbox.model_version == "PRESENT_Sbox_BBB"


def test_configure_model_version_applies_aesround_exact_name_rule():
    # DIFFERENTIAL_SBOXCOUNT's third rule ("XORDIFF_A", "AESround") matches by exact class name,
    # carrying the S-box-level version onto the composite AES round.
    xor, sbox, aes = XOR(), PRESENT_Sbox(), AESround()
    fn = SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: [xor, sbox, aes]}})
    cipher = SimpleNamespace(name="toy", nbr_rounds=1, functions={"P": fn}, inputs_constraints=[], outputs_constraints=[])
    scope = {"functions": ["P"], "rounds": {"P": [1]}, "layers": {"P": {1: [0]}}, "positions": {"P": {1: {0: [0, 1, 2]}}}}

    mc.configure_model_version(cipher, "DIFFERENTIAL_SBOXCOUNT", scope)

    assert xor.model_version == "XOR_XORDIFF"             # (XORDIFF, None)
    assert sbox.model_version == "PRESENT_Sbox_XORDIFF_A"  # (XORDIFF_A, "Sbox") suffix match
    assert aes.model_version == "AESround_XORDIFF_A"       # (XORDIFF_A, "AESround") exact-name match


# ------------------------------ gen_round_model_constraint_obj_fun ------------------------------
def test_gen_round_model_constraint_obj_fun_aggregates_and_places_weights():
    xor = XOR(model_out=["xc"])
    sbox = PRESENT_Sbox(model_out=["sc"], weight=["w0"])
    fn = SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: [xor, sbox]}})
    cipher = SimpleNamespace(
        name="toy", nbr_rounds=1, functions={"P": fn},
        inputs_constraints=[XOR(model_out=["in"])], outputs_constraints=[XOR(model_out=["out"])],
    )
    config = dict(_FULL_SCOPE, model_type="milp")

    constraint, obj_fun = mc.gen_round_model_constraint_obj_fun(cipher, "DIFFERENTIAL_SBOXCOUNT", config)

    assert {"in", "out", "xc", "sc"} <= set(constraint)  # I/O + per-operator models all aggregated
    assert obj_fun == [["w0"]]                            # the S-box weight lands in round 1's objective


def test_gen_round_model_constraint_obj_fun_skips_io_models_when_disabled():
    xor = XOR(model_out=["xc"])
    fn = SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: [xor]}})
    cipher = SimpleNamespace(
        name="toy", nbr_rounds=1, functions={"P": fn},
        inputs_constraints=[XOR(model_out=["in"])], outputs_constraints=[XOR(model_out=["out"])],
    )
    config = {
        "model_type": "milp", "functions": ["P"], "rounds": {"P": [1]}, "layers": {"P": {1: [0]}},
        "positions": {"P": {1: {0: [0]}}}, "gen_input_model": False, "gen_output_model": False,
    }

    constraint, _ = mc.gen_round_model_constraint_obj_fun(cipher, "DIFFERENTIAL_SBOXCOUNT", config)

    assert "in" not in constraint and "out" not in constraint  # I/O model generation skipped
    assert "xc" in constraint                                  # per-operator model still generated


def test_gen_round_passes_model_params_to_matching_operator():
    sbox = PRESENT_Sbox(model_out=["sc"])
    fn = SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: [sbox]}})
    cipher = SimpleNamespace(name="toy", nbr_rounds=1, functions={"P": fn}, inputs_constraints=[], outputs_constraints=[])
    config = {
        "model_type": "milp", "functions": ["P"], "rounds": {"P": [1]}, "layers": {"P": {1: [0]}},
        "positions": {"P": {1: {0: [0]}}}, "model_params": {"PRESENT_Sbox": {"tool_type": "polyhedron"}},
    }

    mc.gen_round_model_constraint_obj_fun(cipher, "DIFFERENTIAL_SBOXCOUNT", config)

    assert sbox._last_params == {"tool_type": "polyhedron"}  # per-operator params threaded to generate_model


# ------------------------------ parse_and_set_configs ------------------------------
def _scope_cipher():
    fn = SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: [0]}})
    return SimpleNamespace(name="toy", nbr_rounds=1, functions={"P": fn})


def test_parse_and_set_configs_fills_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))

    cm, cs = mc.parse_and_set_configs(_scope_cipher(), "DIFFERENTIAL_SBOXCOUNT", "EXISTENCE", {}, {})

    assert cm["model_type"] == "milp"
    assert {"functions", "rounds", "layers", "positions", "filename"} <= set(cm)
    assert cs["solver"] == "DEFAULT"
    assert cm["filename"].endswith("milp_model.lp")
    assert "solution_number" not in cs  # the many-solution default is a frontend concern, not here


def test_parse_and_set_configs_preserves_explicit_filename(tmp_path):
    filename = str(tmp_path / "custom.cnf")

    cm, _ = mc.parse_and_set_configs(
        _scope_cipher(), "DIFFERENTIAL_SBOXCOUNT", "EXISTENCE", {"model_type": "SAT", "filename": filename}, {}
    )

    assert cm["model_type"] == "sat"      # SAT normalized to sat
    assert cm["filename"] == filename     # explicit path preserved verbatim, not replaced by the default


def test_parse_and_set_configs_normalizes_and_validates_solution_number():
    cipher = _scope_cipher()

    _, cs = mc.parse_and_set_configs(cipher, "DIFFERENTIAL_SBOXCOUNT", "EXISTENCE", {}, {"solution_number": 7})
    assert cs["solution_number"] == 7

    with pytest.raises(ValueError, match="Invalid solution_number"):
        mc.parse_and_set_configs(cipher, "DIFFERENTIAL_SBOXCOUNT", "EXISTENCE", {}, {"solution_number": 0})


def test_parse_and_set_configs_rejects_bad_model_type():
    with pytest.raises(ValueError, match="Invalid model_type"):
        mc.parse_and_set_configs(_scope_cipher(), "DIFFERENTIAL_SBOXCOUNT", "EXISTENCE", {"model_type": "cnf"}, {})
