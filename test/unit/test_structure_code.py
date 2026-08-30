"""The LLM-code escape hatch now covers STRUCTURE, not just constants: key_extract_indices and
any layer index table may be a {"code": "..."} program that returns the concrete list, run in
the safe_eval_program sandbox and verified by the KAT. This lets a cipher whose structure
follows a RULE (Simon's per-round key reach-back) be expressed in a few lines instead of a new
hand-written declarative field or dozens of literal entries. The sandbox gained dict-literal and
string-constant support (needed for {"from": r, "words": [..]} entries) without losing safety.
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec, safe_eval_program
from agent.skills.cipher_definition import build_permutation_from_spec


def test_sandbox_supports_dict_and_string_but_stays_safe():
    out = safe_eval_program('result = [{"from": i, "words": [i, i + 1]} for i in range(3)]', {})
    assert out == [{"from": 0, "words": [0, 1]}, {"from": 1, "words": [1, 2]},
                   {"from": 2, "words": [2, 3]}]
    # strings did not open an attribute / import / unbounded-growth hole
    assert safe_eval_program('result = "".__class__', {}) is None
    assert safe_eval_program('result = __import__("os")', {}) is None
    assert safe_eval_program('result = "a" * (10**9)', {}, max_len=1000) is None


def test_key_extract_code_matches_the_explicit_plan():
    # Simon's rule (warmup reads vars[1] reversed, steady reads vars[i-m+1] word 0), as code.
    m = 4
    code = (
        "m = 4\nresult = []\n"
        "for i in range(1, count + 1):\n"
        "    if i <= m:\n"
        "        result.append({\"from\": 1, \"words\": [(m - i % m) % m]})\n"
        "    else:\n"
        "        result.append({\"from\": i - m + 1, \"words\": [0]})\n"
    )
    spec = CipherSpec(name="X", cipher_type="blockcipher",
                      block_size=32, word_bitsize=16, nbr_words=2, nbr_rounds=32,
                      key_size=64, key_word_bitsize=16, key_nbr_words=4, key_nbr_rounds=29,
                      key_extract_indices={"code": code, "count": 32},
                      round_structure=[LayerSpec("add_round_key", {"operator": "xor", "mask": [1, 0]})])
    resolved = spec.resolve_code_params().key_extract_indices
    expected = [({"from": 1, "words": [(m - i % m) % m]} if i <= m
                 else {"from": i - m + 1, "words": [0]}) for i in range(1, 33)]
    assert resolved == expected


def test_layer_index_table_from_code_builds_correctly():
    sbox = [3, 14, 1, 10, 4, 9, 5, 6, 8, 11, 15, 2, 13, 12, 0, 7]
    spec = CipherSpec(name="IdxCode", cipher_type="permutation",
                      block_size=16, word_bitsize=4, nbr_words=4, nbr_rounds=1,
                      sbox_tables={"S": sbox},
                      round_structure=[LayerSpec("sbox", {"sbox_name": "S",
                                       "index": {"code": "result = [[i] for i in range(nbr_words)]"}})])
    assert spec.validate() == []
    with redirect_stdout(io.StringIO()):
        cipher = build_permutation_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        out = imp.evaluate_python(cipher, [[1, 2, 3, 4]], output_len=None)
    assert out == [sbox[w] for w in [1, 2, 3, 4]]


def test_code_that_returns_nonlist_is_a_clear_error():
    spec = CipherSpec(name="Bad", cipher_type="permutation",
                      block_size=8, word_bitsize=4, nbr_words=2, nbr_rounds=1,
                      round_structure=[LayerSpec("permutation", {"table": {"code": "result = 5"}})])
    errs = spec.validate()
    assert any("must return a list" in e for e in errs)
