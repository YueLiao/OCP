"""The generic primitive exporter turns any (non-layout) CipherSpec - word-level or bit,
permutation or block cipher - into a SELF-CONTAINED OCP primitive file (no agent deps, like
the hand-written built-ins), building itself layer by layer. Verified end to end: generate ->
append S-boxes to operators/Sbox.py -> write to primitives/ -> import -> factory() -> the
built cipher passes the spec's test vectors. All side effects are restored afterward."""
import io
import importlib
import pathlib
import sys
from contextlib import redirect_stdout

import operators.Sbox as sbox_mod
import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec
from agent.skills.cipher_examples import EXAMPLE_SPECS
from agent.skills.cipher_primitive_export import generate_primitive_source
from agent.skills.cipher_definition import _normalize_test_vectors


def _export_import_build(spec):
    """Generate an independent primitive, materialize it (S-box + module), build via factory,
    and restore operators/Sbox.py and primitives/ afterward. Returns (filename, cipher)."""
    fn, src, appends, cat = generate_primitive_source(spec)
    factory_name = next(iter(next(iter(cat.values()))["factories"].values()))
    sbox_path = pathlib.Path(sbox_mod.__file__)
    sbox_backup = sbox_path.read_text()
    ppath = pathlib.Path("primitives") / fn
    module = f"primitives.{fn[:-3]}"
    try:
        if appends:
            sbox_path.write_text(sbox_backup + "".join(s for _, s in appends))
            importlib.reload(sbox_mod)
        # the generated file has NO agent imports - only primitives/operators
        assert "from agent" not in src
        ppath.write_text(src)
        mod = importlib.import_module(module)
        with redirect_stdout(io.StringIO()):
            cipher = getattr(mod, factory_name)()
        return fn, cipher
    finally:
        ppath.unlink(missing_ok=True)
        sys.modules.pop(module, None)
        sbox_path.write_text(sbox_backup)
        importlib.reload(sbox_mod)


def _passes_kat(cipher, spec):
    spec.test_vectors = _normalize_test_vectors(spec.test_vectors, spec.cipher_type)
    with redirect_stdout(io.StringIO()):
        from agent.skills.cipher_definition import verify_cipher_test_vectors
        res = verify_cipher_test_vectors(cipher, spec)
    return res


def test_generic_export_block_cipher_is_self_contained_and_verifies():
    spec = CipherSpec.from_dict(EXAMPLE_SPECS["mini_block"])
    fn, cipher = _export_import_build(spec)
    assert fn == "miniblock.py"
    res = _passes_kat(cipher, spec)
    assert res["tested"] and res["all_passed"], res


def test_generic_export_permutation_is_self_contained_and_verifies():
    spec = CipherSpec.from_dict(EXAMPLE_SPECS["mini_spn"])
    fn, cipher = _export_import_build(spec)
    assert fn == "minispn.py"
    res = _passes_kat(cipher, spec)
    assert res["tested"] and res["all_passed"], res


def test_generic_export_handles_key_archetype_and_xor_whitening():
    # A Midori64 declared with a key_archetype (static_alternating + xor whitening + pi
    # constants) must export to a self-contained file whose SUBKEYS builds WK = K0 (+) K1
    # and whose exported cipher still passes the designer KAT.
    spec = CipherSpec.from_dict({
        "name": "MidoriArchExp", "cipher_type": "blockcipher",
        "block_size": 64, "word_bitsize": 4, "nbr_words": 16, "nbr_rounds": 16,
        "key_size": 128, "key_word_bitsize": 4, "key_nbr_words": 32,
        "sbox_tables": {"Sb0": [12, 10, 13, 3, 14, 11, 15, 7, 8, 9, 1, 5, 0, 2, 4, 6]},
        "round_structure": [
            {"layer_type": "sbox", "params": {"sbox_name": "Sb0", "index": [[j] for j in range(16)]}},
            {"layer_type": "permutation", "params": {"table": [0, 10, 5, 15, 14, 4, 11, 1, 9, 3, 12, 6, 7, 13, 2, 8]}},
            {"layer_type": "matrix", "params": {"matrix": [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]],
                                                "indices": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]],
                                                "polynomial": "0x0"}},
        ],
        "key_archetype": {"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
                          "round_constants": {"source": "pi_hex", "count": 15}},
        "test_vectors": [{"plaintext": [0] * 16, "key": [0] * 32,
                          "output": [3, 12, 9, 12, 12, 14, 13, 10, 2, 11, 11, 13, 4, 4, 9, 10]}],
    })
    fn, cipher = _export_import_build(spec)
    assert fn == "midoriarchexp.py"
    assert _passes_kat(cipher, spec)


def test_generic_export_versioned_block_cipher_is_one_file_with_version_param():
    # A versioned block cipher exports to ONE file with a `version` parameter (like
    # present.py/led.py), keyed by [block, key], and each version reproduces the builder.
    from agent.skills.cipher_definition import build_blockcipher_from_spec, _spec_needs_unroll
    base = {
        "name": "Duo", "cipher_type": "blockcipher",
        "block_size": 0, "word_bitsize": 0, "nbr_words": 0, "nbr_rounds": 0,
        "key_size": 0, "key_word_bitsize": 4, "key_nbr_words": 0, "key_extract_indices": [0, 1, 2, 3],
        "sbox_tables": {"S": list(range(16))},
        "round_structure": [
            {"layer_type": "add_round_key", "params": {"operator": "xor", "mask": [1, 1, 1, 1]}},
            {"layer_type": "sbox", "params": {"sbox_name": "S", "index": [[0], [1], [2], [3]]}},
        ],
        "versions": {
            "A": {"block_size": 16, "word_bitsize": 4, "nbr_words": 4, "nbr_rounds": 2, "key_size": 64, "key_nbr_words": 16},
            "B": {"block_size": 16, "word_bitsize": 4, "nbr_words": 4, "nbr_rounds": 3, "key_size": 128, "key_nbr_words": 32},
        },
        "default_version": "A",
    }
    spec = CipherSpec.from_dict(base)
    fn, src, appends, cat = generate_primitive_source(spec)
    assert fn == "duo.py"
    assert "def DUO_BLOCKCIPHER(r=None, version=None" in src and "DUO_VERSIONS" in src
    assert set(cat["duo"]["valid_versions"]["blockcipher"]) == {(16, 64), (16, 128)}
    assert "from agent" not in src

    def _build_eval(inst, P, K):
        with redirect_stdout(io.StringIO()):
            c = build_blockcipher_from_spec(inst)
            imp.generate_implementation(c, get_files_dir() / f"{c.name}.py", "python", _spec_needs_unroll(inst))
            return imp.evaluate_python(c, [P, K], output_len=16)

    exp_a = _build_eval(spec.instantiate("A"), [1, 2, 3, 4], list(range(16)))
    exp_b = _build_eval(spec.instantiate("B"), [1, 2, 3, 4], list(range(32)))

    sbox_path = pathlib.Path(sbox_mod.__file__)
    backup = sbox_path.read_text()
    ppath = pathlib.Path("primitives") / fn
    try:
        if appends:
            sbox_path.write_text(backup + "".join(s for _, s in appends))
            importlib.reload(sbox_mod)
        ppath.write_text(src)
        mod = importlib.import_module("primitives.duo")
        with redirect_stdout(io.StringIO()):
            ca = mod.DUO_BLOCKCIPHER(version=[16, 64])
            imp.generate_implementation(ca, get_files_dir() / f"{ca.name}.py", "python", True)
            got_a = imp.evaluate_python(ca, [[1, 2, 3, 4], list(range(16))], output_len=16)
            cb = mod.DUO_BLOCKCIPHER(version=[16, 128])
            imp.generate_implementation(cb, get_files_dir() / f"{cb.name}.py", "python", True)
            got_b = imp.evaluate_python(cb, [[1, 2, 3, 4], list(range(32))], output_len=16)
        assert got_a == exp_a and got_b == exp_b       # each version reproduces the builder
    finally:
        ppath.unlink(missing_ok=True)
        sys.modules.pop("primitives.duo", None)
        sbox_path.write_text(backup)
        importlib.reload(sbox_mod)
