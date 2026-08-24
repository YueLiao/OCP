"""Layer PARAM synonyms an LLM commonly emits are normalized so a correct-but-differently-worded
spec still builds. The important case is rotation/shift `direction`: OCP's RotationLayer accepts
only 'l'/'r', but 'left'/'right' is the natural phrasing - and validate accepts them, so without
normalization the spec would pass validate and then CRASH at build. `inputs`/`outputs` are
normalized to `input_indices`/`output_indices`. Deliberately NOT normalized: `row` -> `word_index`
(a whole-row rotation across cells is a bit permutation, not a word rotation - mapping it would
hide a granularity error), so a bare `row` still surfaces a clear "missing word_index".
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_permutation_from_spec
from agent.skills.cipher_text_input import _operation_params


def _rot_out(direction):
    spec = CipherSpec(name=f"Rot{direction}", cipher_type="permutation",
                      block_size=16, word_bitsize=8, nbr_words=2, nbr_rounds=1,
                      round_structure=[LayerSpec("rotation", {"direction": direction,
                                                              "amount": 3, "word_index": 0})])
    assert spec.validate() == []
    with redirect_stdout(io.StringIO()):
        cipher = build_permutation_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        return imp.evaluate(cipher, [[0x81, 0]], output_len=None)


def test_direction_left_right_synonyms_build_and_match_l_r():
    assert _rot_out("left") == _rot_out("l")
    assert _rot_out("right") == _rot_out("r")


def test_inputs_outputs_param_synonyms_normalized():
    assert _operation_params({"params": {"inputs": [[0, 1]], "outputs": [1]}}) == \
        {"input_indices": [[0, 1]], "output_indices": [1]}


def test_row_is_not_silently_mapped_to_word_index():
    # a whole-row rotation is a bit permutation, not a word rotation - do NOT auto-map `row`;
    # surface the missing word_index so the modeling choice is made deliberately.
    errs = CipherSpec(name="Row", cipher_type="permutation", word_bitsize=8, nbr_words=2,
                      nbr_rounds=1, round_structure=[LayerSpec("rotation",
                      {"direction": "left", "amount": 3, "row": 0})]).validate()
    assert any("word_index" in e for e in errs)
