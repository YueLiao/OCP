"""One general ARX-permutation expander (CipherSpec.expand_arx) lowers a declared (sub)round
into concrete modadd/xor/rotation layers and reproduces the whole ChaCha / Salsa / Forro
family from KATs - instead of the LLM hand-wiring 12*nbr_rounds index layers.

Exercises: periodic selection phases via LayerSpec.phase_params (ChaCha/Salsa columns vs
diagonals = period 2; Forro = period 8), multi-word rotation layers (4 lanes at once),
per-lane scratch temps ({"temp": 0} for Salsa's a+d), and the feed-forward keystream variant
(save the input state with an `equal` copy, add it back in the last round).
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec
from agent.skills.cipher_definition import build_permutation_from_spec, _spec_needs_unroll

_CHACHA_OPS = [
    {"op": "modadd", "in": [0, 1], "out": 0}, {"op": "xor", "in": [0, 3], "out": 3},
    {"op": "rotl", "in": [3], "out": 3, "amount": 16},
    {"op": "modadd", "in": [2, 3], "out": 2}, {"op": "xor", "in": [1, 2], "out": 1},
    {"op": "rotl", "in": [1], "out": 1, "amount": 12},
    {"op": "modadd", "in": [0, 1], "out": 0}, {"op": "xor", "in": [0, 3], "out": 3},
    {"op": "rotl", "in": [3], "out": 3, "amount": 8},
    {"op": "modadd", "in": [2, 3], "out": 2}, {"op": "xor", "in": [1, 2], "out": 1},
    {"op": "rotl", "in": [1], "out": 1, "amount": 7},
]
_CHACHA_SEL = [[[0, 4, 8, 12], [1, 5, 9, 13], [2, 6, 10, 14], [3, 7, 11, 15]],
               [[0, 5, 10, 15], [1, 6, 11, 12], [2, 7, 8, 13], [3, 4, 9, 14]]]

_T = {"temp": 0}
_SALSA_OPS = [
    {"op": "modadd", "in": [0, 3], "out": _T}, {"op": "rotl", "in": [_T], "out": _T, "amount": 7},
    {"op": "xor", "in": [_T, 1], "out": 1},
    {"op": "modadd", "in": [0, 1], "out": _T}, {"op": "rotl", "in": [_T], "out": _T, "amount": 9},
    {"op": "xor", "in": [_T, 2], "out": 2},
    {"op": "modadd", "in": [1, 2], "out": _T}, {"op": "rotl", "in": [_T], "out": _T, "amount": 13},
    {"op": "xor", "in": [_T, 3], "out": 3},
    {"op": "modadd", "in": [2, 3], "out": _T}, {"op": "rotl", "in": [_T], "out": _T, "amount": 18},
    {"op": "xor", "in": [_T, 0], "out": 0},
]
_SALSA_SEL = [[[0, 4, 8, 12], [5, 9, 13, 1], [10, 14, 2, 6], [15, 3, 7, 11]],
              [[0, 1, 2, 3], [5, 6, 7, 4], [10, 11, 8, 9], [15, 12, 13, 14]]]

_FORRO_OPS = [
    {"op": "modadd", "in": [3, 4], "out": 3}, {"op": "xor", "in": [2, 3], "out": 2},
    {"op": "modadd", "in": [1, 2], "out": 1}, {"op": "rotl", "in": [1], "out": 1, "amount": 10},
    {"op": "modadd", "in": [1, 0], "out": 0}, {"op": "xor", "in": [0, 4], "out": 4},
    {"op": "modadd", "in": [4, 3], "out": 3}, {"op": "rotl", "in": [3], "out": 3, "amount": 27},
    {"op": "modadd", "in": [3, 2], "out": 2}, {"op": "xor", "in": [2, 1], "out": 1},
    {"op": "modadd", "in": [1, 0], "out": 0}, {"op": "rotl", "in": [0], "out": 0, "amount": 8},
]
_FORRO_SEL = [[t] for t in ([0, 4, 8, 12, 3], [1, 5, 9, 13, 0], [2, 6, 10, 14, 1], [3, 7, 11, 15, 2],
                            [0, 5, 10, 15, 3], [1, 6, 11, 12, 0], [2, 7, 8, 13, 1], [3, 4, 9, 14, 2])]


def _run(spec, IN, OUT):
    with redirect_stdout(io.StringIO()):
        cipher = build_permutation_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        got = imp.evaluate(cipher, [IN], output_len=None)
    return got == OUT


def test_chacha_permutation_from_arx():
    spec = CipherSpec(name="ChaChaARX", cipher_type="permutation", nbr_rounds=20,
                      arx={"word_bitsize": 32, "nbr_words": 16, "selections": _CHACHA_SEL, "ops": _CHACHA_OPS})
    assert _spec_needs_unroll(spec) and spec.validate() == []
    IN = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574, 0x03020100, 0x07060504, 0x0b0a0908, 0x0f0e0d0c,
          0x13121110, 0x17161514, 0x1b1a1918, 0x1f1e1d1c, 0x00000001, 0x09000000, 0x4a000000, 0x00000000]
    OUT = [0x837778ab, 0xe238d763, 0xa67ae21e, 0x5950bb2f, 0xc4f2d0c7, 0xfc62bb2f, 0x8fa018fc, 0x3f5ec7b7,
           0x335271c2, 0xf29489f3, 0xeabda8fc, 0x82e46ebd, 0xd19c12b4, 0xb04e16de, 0x9e83d0cb, 0x4e3c50a2]
    assert _run(spec, IN, OUT)


def test_salsa_permutation_from_arx_with_scratch_temp():
    spec = CipherSpec(name="SalsaARX", cipher_type="permutation", nbr_rounds=20,
                      arx={"word_bitsize": 32, "nbr_words": 16, "temp_per_lane": 1,
                           "selections": _SALSA_SEL, "ops": _SALSA_OPS})
    assert spec.validate() == []
    IN = [0x61707865, 0x04030201, 0x08070605, 0x0c0b0a09, 0x100f0e0d, 0x3320646e, 0x01040103, 0x06020905,
          0x00000007, 0x00000000, 0x79622d32, 0x14131211, 0x18171615, 0x1c1b1a19, 0x201f1e1d, 0x6b206574]
    OUT = [0x58318d3e, 0x0292df4f, 0xa28d8215, 0xa1aca723, 0x697a34c7, 0xf2f00ba8, 0x63e9b0a1, 0x27250e3a,
           0xb1c7f1f3, 0x62066edc, 0x66d3ccf1, 0xb0365cf3, 0x091ad09e, 0x64f0c40f, 0xd60d95ea, 0x00be78c9]
    assert _run(spec, IN, OUT)


def test_forro_permutation_from_arx_period_8():
    spec = CipherSpec(name="ForroARX", cipher_type="permutation", nbr_rounds=14 * 4,
                      arx={"word_bitsize": 32, "nbr_words": 16, "selections": _FORRO_SEL, "ops": _FORRO_OPS})
    assert spec.validate() == []
    IN = [0x686e696d, 0x69762061, 0x65206164, 0x646e6120, 0x00000000, 0x00000000, 0x746c6f76, 0x61616461,
          0x70207261, 0x6520726f, 0x20657473, 0x73696170, 0x74736f6d, 0x61206f72, 0x72626173, 0x61636e61]
    OUT = [0xf9fe4058, 0x45dc7391, 0x5075018e, 0xf7eb3f6d, 0x25821062, 0x11334ef1, 0x06d33da0, 0x9c9f3bed,
           0x1e167e5f, 0x4d289ed3, 0x77dd96f8, 0x47d21a6b, 0x6382742c, 0xc7cfac37, 0xd42a0926, 0x901b01f0]
    assert _run(spec, IN, OUT)


def test_chacha_keystream_feedforward_from_arx():
    # 20 quarter-round rounds + 1 feed-forward add round = 21
    spec = CipherSpec(name="ChaChaKeyARX", cipher_type="permutation", nbr_rounds=21,
                      arx={"word_bitsize": 32, "nbr_words": 16, "selections": _CHACHA_SEL,
                           "ops": _CHACHA_OPS, "feedforward": True})
    assert spec.validate() == []
    IN = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574, 0x03020100, 0x07060504, 0x0b0a0908, 0x0f0e0d0c,
          0x13121110, 0x17161514, 0x1b1a1918, 0x1f1e1d1c, 0x00000001, 0x09000000, 0x4a000000, 0x00000000]
    OUT = [0xe4e7f110, 0x15593bd1, 0x1fdd0f50, 0xc47120a3, 0xc7f4d1c7, 0x0368c033, 0x9aaa2204, 0x4e6cd4c3,
           0x466482d2, 0x09aa9f07, 0x05d7c214, 0xa2028bd9, 0xd19c12b5, 0xb94e16de, 0xe883d0cb, 0x4e3c50a2]
    assert _run(spec, IN, OUT)


def test_arx_carries_through_facts_layer():
    # The text-first FACTS layer must carry `arx` (with operations empty) through to a spec,
    # so an LLM that declares an ARX round gets a correct ChaCha without hand-writing layers.
    from agent.skills.cipher_text_input import CipherFacts, cipher_spec_payload_from_facts
    facts = CipherFacts.from_dict({
        "name": "ChaChaFacts", "primitive_type": "permutation", "rounds": {"nbr_rounds": 20},
        "operations": [], "tables": {},
        "arx": {"word_bitsize": 32, "nbr_words": 16, "selections": _CHACHA_SEL, "ops": _CHACHA_OPS},
    })
    assert facts.validate()[0] == []                       # no "operations required" / state errors
    spec = CipherSpec.from_dict(cipher_spec_payload_from_facts(facts))
    assert spec.validate() == [] and spec.arx
    IN = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574, 0x03020100, 0x07060504, 0x0b0a0908, 0x0f0e0d0c,
          0x13121110, 0x17161514, 0x1b1a1918, 0x1f1e1d1c, 0x00000001, 0x09000000, 0x4a000000, 0x00000000]
    OUT = [0x837778ab, 0xe238d763, 0xa67ae21e, 0x5950bb2f, 0xc4f2d0c7, 0xfc62bb2f, 0x8fa018fc, 0x3f5ec7b7,
           0x335271c2, 0xf29489f3, 0xeabda8fc, 0x82e46ebd, 0xd19c12b4, 0xb04e16de, 0x9e83d0cb, 0x4e3c50a2]
    assert _run(spec, IN, OUT)


def test_arx_exports_to_self_contained_file():
    # An ARX spec exports to a self-contained primitive (no agent deps): the phase params are
    # small, so they inline (like Midori) - the exported file rebuilds ChaCha and matches KAT.
    import importlib
    import pathlib
    import sys
    from agent.skills.cipher_primitive_export import generate_primitive_source
    spec = CipherSpec(name="ChaChaExp", cipher_type="permutation", nbr_rounds=20,
                      arx={"word_bitsize": 32, "nbr_words": 16, "selections": _CHACHA_SEL, "ops": _CHACHA_OPS})
    fn, src, appends, cat = generate_primitive_source(spec)
    assert fn == "chachaexp.py" and "from agent" not in src
    IN = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574, 0x03020100, 0x07060504, 0x0b0a0908, 0x0f0e0d0c,
          0x13121110, 0x17161514, 0x1b1a1918, 0x1f1e1d1c, 0x00000001, 0x09000000, 0x4a000000, 0x00000000]
    OUT = [0x837778ab, 0xe238d763, 0xa67ae21e, 0x5950bb2f, 0xc4f2d0c7, 0xfc62bb2f, 0x8fa018fc, 0x3f5ec7b7,
           0x335271c2, 0xf29489f3, 0xeabda8fc, 0x82e46ebd, 0xd19c12b4, 0xb04e16de, 0x9e83d0cb, 0x4e3c50a2]
    p = pathlib.Path("primitives") / fn
    try:
        p.write_text(src)
        sys.modules.pop("primitives.chachaexp", None)
        mod = importlib.import_module("primitives.chachaexp")
        with redirect_stdout(io.StringIO()):
            cipher = mod.CHACHAEXP_PERMUTATION()
            imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
            got = imp.evaluate(cipher, [IN], output_len=None)
        assert got == OUT
    finally:
        p.unlink(missing_ok=True)
        sys.modules.pop("primitives.chachaexp", None)
