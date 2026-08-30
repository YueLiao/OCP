"""Restricted-execution path: besides hand-written deterministic expanders, the LLM may supply
a small PROGRAM that computes constants (from the paper's rule) which safe_eval_program runs in
a sandbox; the KAT is the safety net. Verifies the sandbox rejects everything unsafe, runs real
integer computation, and drives a correct Midori64 whose round constants come only from code.
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import (
    safe_eval_program, pi_round_constant_cells, _round_constant_values, CipherSpec, LayerSpec,
)
from agent.skills.cipher_definition import build_blockcipher_from_spec


def test_sandbox_runs_integer_computation():
    assert safe_eval_program("result = [(i * i + 1) & 0xff for i in range(count)]", {"count": 5}) \
        == [1, 2, 5, 10, 17]
    # a program that builds a list with append (loops + subscript assignment)
    prog = "result = []\nfor i in range(count):\n    result.append((i << 2) | 1)"
    assert safe_eval_program(prog, {"count": 4}) == [1, 5, 9, 13]


def test_sandbox_rejects_unsafe_code():
    for bad in [
        "import os\nresult = 1",
        "result = open('/etc/passwd')",
        "result = [].__class__",
        "while True:\n    result = 1",
        "result = __import__('os')",
        "def f():\n    return 1\nresult = f()",
        "result = eval('1')",
        "result = (1).__class__.__mro__",
    ]:
        assert safe_eval_program(bad) is None, bad


def test_sandbox_bounds_runaway():
    # step budget stops an unbounded-looking loop instead of hanging
    assert safe_eval_program("result = [0 for i in range(10**9)]", {}, max_steps=10000) is None


def test_round_constant_values_code_source():
    assert _round_constant_values({"code": "result = [i for i in range(count)]"}, 6) == [0, 1, 2, 3, 4, 5]
    # a bad program falls back to zeros (never crashes the build)
    assert _round_constant_values({"code": "result = brokenname"}, 3) == [0, 0, 0]


_MIDORI_BETA = ("[[2,4,3,15],[6,10,8,8],[8,5,10,3],[0,8,13,3],[1,3,1,9],[8,10,2,14],[0,3,7,0],[7,3,4,4],"
                "[10,4,0,9],[3,8,2,2],[2,9,9,15],[3,1,13,0],[0,8,2,14],[15,10,9,8],[14,12,4,14]]")
_MIDORI_CODE = f"""
beta = {_MIDORI_BETA}
result = []
for i in range(count):
    row = beta[i]
    cells = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    for r in range(4):
        v = row[r]
        for c in range(4):
            cells[4*c+r] = (v >> (3-c)) & 1
    result.append(cells)
"""


def test_code_derived_constants_match_reference_and_kat():
    # the LLM could supply _MIDORI_CODE to derive Midori's alpha from the beta hex integers;
    # it reproduces pi_round_constant_cells and, end to end, the designer Midori64 KAT.
    assert safe_eval_program(_MIDORI_CODE, {"count": 15}) == pi_round_constant_cells(15)
    spec = CipherSpec(
        name="MidoriCode", cipher_type="blockcipher",
        block_size=64, word_bitsize=4, nbr_words=16, nbr_rounds=16,
        key_size=128, key_word_bitsize=4, key_nbr_words=32,
        sbox_tables={"Sb0": [12, 10, 13, 3, 14, 11, 15, 7, 8, 9, 1, 5, 0, 2, 4, 6]},
        round_structure=[
            LayerSpec("sbox", {"sbox_name": "Sb0", "index": [[j] for j in range(16)]}),
            LayerSpec("permutation", {"table": [0, 10, 5, 15, 14, 4, 11, 1, 9, 3, 12, 6, 7, 13, 2, 8]}),
            LayerSpec("matrix", {"matrix": [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]],
                                 "indices": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]],
                                 "polynomial": "0x0"}),
        ],
        key_archetype={"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
                       "round_constants": {"source": "code", "count": 15, "code": _MIDORI_CODE}})
    assert spec.validate() == []
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        out = imp.evaluate_python(cipher, [[0] * 16, [0] * 32], output_len=64)
    val = 0
    for v in out[:16]:
        val = (val << 4) | (v & 0xF)
    assert val == 0x3c9cceda2bbd449a


def test_code_source_works_in_layout_add_round_constant():
    # The `code` source now also drives a bit-sliced (KNOT/GIFT-style) layout round constant:
    # an LLM program computing the Fibonacci LFSR sequence produces the SAME cipher as the
    # built-in {"lfsr": ...} generator.
    lfsr = {"width": 6, "taps": [5, 4], "init": 1}
    code = ("result = []\ns = 1\nfor i in range(count):\n    result.append(s)\n"
            "    fb = ((s >> 5) ^ (s >> 4)) & 1\n    s = ((s << 1) | fb) & 63")
    assert _round_constant_values({"code": code}, 20) == _round_constant_values({"lfsr": lfsr}, 20)

    sbox = [i ^ 1 for i in range(64)]

    def _out(rc_source, name):
        spec = CipherSpec(
            name=name, cipher_type="permutation", nbr_rounds=10,
            layout={"rows": 6, "cols": 4}, sbox_tables={"S": sbox},
            round_structure=[
                LayerSpec("subcolumn_sbox", {"sbox_name": "S"}),
                LayerSpec("shift_rows", {"offsets": [0, 1, 2, 3, 1, 2], "direction": "l"}),
                LayerSpec("add_round_constant", {"d": 6, **rc_source}),
            ]).expand_bitsliced()
        with redirect_stdout(io.StringIO()):
            cipher = build_permutation_from_spec(spec)
            imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
            return imp.evaluate_python(cipher, [[1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0]],
                                output_len=None)

    from agent.skills.cipher_definition import build_permutation_from_spec  # noqa: local import for clarity
    out_lfsr = _out({"lfsr": lfsr}, "LayLfsr")
    out_code = _out({"code": code}, "LayCode")
    assert out_code is not None and out_code == out_lfsr
