"""One general `linear_diffusion` layer (a circulant rotate-and-XOR over a shape) expands to a
bit-level n_xor and reproduces BOTH ASCON's Sigma (axis "within", per-row taps) and SPEEDY's
MixColumn (axis "across", uniform taps) - instead of the LLM hand-writing hundreds of n_xor
index tuples. Verified: each expands to exactly the hand-written layer, and a full 12-round
ASCON built with it matches the reference ASCON permutation.
"""
import io
import random
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_permutation_from_spec


def _run(name, layers, nw, inp, nbr_rounds=1, sbox_tables=None):
    spec = CipherSpec(name=name, cipher_type="permutation", word_bitsize=1, nbr_words=nw,
                      nbr_rounds=nbr_rounds, round_structure=layers, sbox_tables=sbox_tables or {})
    with redirect_stdout(io.StringIO()):
        cipher = build_permutation_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        return imp.evaluate(cipher, [inp], output_len=None)


def test_linear_diffusion_reproduces_speedy_mixcolumn_across():
    lanes, alpha = 32, [1, 5, 9, 15, 21, 26]
    groups = [[i * 6 + j] + [(i + a) % lanes * 6 + j for a in alpha] for i in range(lanes) for j in range(6)]
    ref = LayerSpec("n_xor", {"input_indices": groups, "output_indices": [i * 6 + j for i in range(lanes) for j in range(6)]})
    ld = LayerSpec("linear_diffusion", {"shape": [32, 6], "axis": "across", "taps": alpha, "direction": "r"})
    random.seed(1)
    inp = [random.randint(0, 1) for _ in range(192)]
    assert _run("SpMcRef", [ref], 192, inp) == _run("SpMcLd", [ld], 192, inp)


def test_linear_diffusion_reproduces_ascon_sigma_within_per_row():
    taps = [[45, 36], [3, 25], [63, 58], [54, 47], [57, 23]]
    groups = [[r * 64 + j] + [r * 64 + (j + t) % 64 for t in taps[r]] for r in range(5) for j in range(64)]
    ref = LayerSpec("n_xor", {"input_indices": groups, "output_indices": list(range(320))})
    ld = LayerSpec("linear_diffusion", {"shape": [5, 64], "axis": "within", "taps": taps, "direction": "r"})
    random.seed(2)
    inp = [random.randint(0, 1) for _ in range(320)]
    assert _run("AsSigRef", [ref], 320, inp) == _run("AsSigLd", [ld], 320, inp)


def test_full_ascon_from_linear_diffusion_matches_reference():
    import primitives.ascon as ascon
    with redirect_stdout(io.StringIO()):
        ref = ascon.ASCON_PERMUTATION(r=12)
        imp.generate_implementation(ref, get_files_dir() / f"{ref.name}.py", "python", True)
        want = imp.evaluate(ref, [[0] * 320], output_len=None)

    cons = [0xf0 - r * 0x10 + r * 0x1 for r in range(12)]
    ct = [[(cons[i - 1] >> (7 - b)) & 1 for b in range(8)] for i in range(1, 13)]  # per-round 8-bit RC
    ascon_sbox = [0x4, 0xb, 0x1f, 0x14, 0x1a, 0x15, 0x9, 0x2, 0x1b, 0x5, 0x8, 0x12, 0x1d, 0x3, 0x6, 0x1c,
                  0x1e, 0x13, 0x7, 0xe, 0x0, 0xd, 0x11, 0x18, 0x10, 0xc, 0x1, 0x19, 0x16, 0xa, 0xf, 0x17]
    layers = [
        LayerSpec("add_constant", {"add_type": "xor", "constant_mask": [None] * 184 + [True] * 8, "constant_table": ct}),
        LayerSpec("sbox", {"sbox_name": "S", "index": [[k + j * 64 for j in range(5)] for k in range(64)]}),
        LayerSpec("linear_diffusion", {"shape": [5, 64], "axis": "within",
                                       "taps": [[45, 36], [3, 25], [63, 58], [54, 47], [57, 23]], "direction": "r"}),
    ]
    got = _run("AsconLD", layers, 320, [0] * 320, nbr_rounds=12, sbox_tables={"S": ascon_sbox})
    assert got == want
