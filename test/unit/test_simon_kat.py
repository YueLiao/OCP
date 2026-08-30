"""Simon-32/64 built through the agent with CROSS-ROUND subkey extraction: the round subkey
reaches back to a HISTORICAL key-schedule state (vars[i-m+1]), and the key schedule runs fewer
rounds than the cipher (key_nbr_rounds = nbr_rounds - m + 1). This is the category-2 gap - a
subkey that is not just "current key state, fixed words". Verified against the designer KAT
through BOTH the build path and the self-contained exporter.
"""
import io
import importlib
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_blockcipher_from_spec, _spec_needs_unroll
from agent.skills.cipher_primitive_export import generate_primitive_source

_M, _R = 4, 32                                     # Simon-32/64: m = 2k/n = 4, 32 rounds
_KAT = ([0x6565, 0x6877], [0x1918, 0x1110, 0x0908, 0x0100], [0xc69b, 0xe9bb])


def _constant_table():
    z0 = 0b01100111000011010100100010111110110011100001101010010001011111
    rc = (2 ** (32 >> 1) - 1) ^ 3
    return [[rc ^ ((z0 >> ((i - 1) % 62)) & 1)] for i in range(1, _R + 1)]


def _simon_spec():
    # subkey extraction: warmup reads the initial key (vars[1]) in reverse word order, then
    # the steady state reaches back to vars[i-m+1] word 0 (the freshly generated key word).
    extract = [({"from": 1, "words": [(_M - i % _M) % _M]} if i <= _M
                else {"from": i - _M + 1, "words": [0]}) for i in range(1, _R + 1)]
    return CipherSpec(
        name="SIMON3264", cipher_type="blockcipher",
        block_size=32, word_bitsize=16, nbr_words=2, nbr_temp_words=3, nbr_rounds=_R,
        key_size=64, key_word_bitsize=16, key_nbr_words=4, key_nbr_temp_words=2,
        key_nbr_rounds=_R - _M + 1,
        key_extract_indices=extract,
        key_schedule=[
            LayerSpec("rotation", {"rotations": [["r", 3, 0, 4]]}),
            LayerSpec("xor", {"input_indices": [[2, 4]], "output_indices": [4]}),
            LayerSpec("xor", {"input_indices": [[3, 4]], "output_indices": [5]}),
            LayerSpec("rotation", {"rotations": [["r", 1, 4, 4]]}),
            LayerSpec("xor", {"input_indices": [[4, 5]], "output_indices": [4]}),
            LayerSpec("add_constant", {"add_type": "xor",
                                       "constant_mask": [None, None, None, None, True, None],
                                       "constant_table": _constant_table()}),
            LayerSpec("permutation", {"table": [4, 0, 1, 2]}),
        ],
        round_structure=[
            LayerSpec("rotation", {"rotations": [["l", 1, 0, 2], ["l", 8, 0, 3], ["l", 2, 0, 4]]}),
            LayerSpec("and", {"input_indices": [[2, 3]], "output_indices": [2]}),
            LayerSpec("xor", {"input_indices": [[1, 2]], "output_indices": [1]}),
            LayerSpec("xor", {"input_indices": [[1, 4]], "output_indices": [1]}),
            LayerSpec("add_round_key", {"operator": "xor", "mask": [0, 1]}),
            LayerSpec("permutation", {"table": [1, 0]}),
        ],
        test_vectors=[[[_KAT[0], _KAT[1]], _KAT[2]]])


def test_simon_32_64_build_matches_designer_kat():
    spec = _simon_spec()
    assert spec.validate() == []
    P, K, C = _KAT
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python",
                                    _spec_needs_unroll(spec))
        got = imp.evaluate_python(cipher, [P, K], output_len=None)
    assert got == C


def test_simon_32_64_export_round_trips_kat():
    spec = _simon_spec()
    spec.name = "SIMONEXP"                          # distinct name so the export file stands alone
    with redirect_stdout(io.StringIO()):
        _, src, _, _ = generate_primitive_source(spec)
    # the exporter threads the shorter key schedule and the historical-state read
    assert "k_rounds = nbr_rounds -" in src
    assert "KS.vars[e['from']]" in src
    # source module and the generated-impl module must differ (evaluate imports files.<name>)
    with open(get_files_dir() / "SIMONEXPSRC.py", "w") as f:
        f.write(src)
    mod = importlib.import_module("files.SIMONEXPSRC")
    with redirect_stdout(io.StringIO()):
        cipher = mod.SIMONEXP_BLOCKCIPHER()
        cipher.name = "SIMONEXPIMPL"               # so the impl lands in a fresh module
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        assert cipher.test_vectors
        for tv in cipher.test_vectors:
            assert imp.evaluate_python(cipher, tv[0], output_len=len(tv[1])) == tv[1]
