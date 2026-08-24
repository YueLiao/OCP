"""Preflight (`_kat_problems`) must not SWALLOW a build/codegen failure - a spec that passes
static validation but crashes the builder used to return [] ("no problems"), so auto-repair
ignored it and confirm failed later. Now it returns a repairable problem. And the define result
reports the four distinct outcomes (built / verified / exported / registered) instead of one
conflated "success", with the catalog updated in-process so a freshly defined cipher is usable
by name without a restart.
"""
import inspect
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import agent.interfaces.api as apimod
import agent.skills.cipher_instantiation as ci
from agent.types import SkillRequest
from agent.session import Session
from agent.skills.cipher_definition import CipherDefinitionSkill
from agent.skills.cipher_spec import CipherSpec, LayerSpec

_API_CLS = next(o for n in dir(apimod)
                if inspect.isclass(o := getattr(apimod, n)) and hasattr(o, "_kat_problems"))


def test_kat_problems_reports_build_failure_not_empty():
    inst = _API_CLS.__new__(_API_CLS)
    # constant_table shorter than nbr_rounds: passes static validation, fails at codegen/run
    spec = {"name": "PreBF", "cipher_type": "permutation", "block_size": 8, "word_bitsize": 4,
            "nbr_words": 2, "nbr_rounds": 5,
            "round_structure": [{"layer_type": "add_constant",
                                 "params": {"add_type": "xor", "constant_mask": [1, 1],
                                            "constant_table": [[1, 1]]}}],
            "test_vectors": [[[[1, 2]], [3, 4]]]}
    assert CipherSpec.from_dict(spec).validate() == []      # static validation is clean
    assert inst._kat_problems(spec)                          # but preflight surfaces the failure


def test_define_result_has_status_flags_and_updates_catalog_in_process():
    skill = CipherDefinitionSkill()
    spec = CipherSpec(name="PreStatus", cipher_type="permutation", block_size=32, word_bitsize=16,
                      nbr_words=2, nbr_rounds=1,
                      round_structure=[LayerSpec("xor", {"input_indices": [[0, 1]],
                                                         "output_indices": [1]})],
                      test_vectors=[[[[1, 2]], [1, 3]]])
    try:
        with redirect_stdout(io.StringIO()):
            res = skill.execute(SkillRequest(skill=skill.name, params={"spec": spec.to_dict()}), Session())
        st = res.data["status"]
        assert st["built"] is True and st["verified"] is True
        assert st["exported"] is True and st["registered"] is True
        assert "prestatus" in ci.CIPHER_CATALOG        # usable by name in THIS process
    finally:
        p = Path("files/custom_ciphers.json")
        if p.exists():
            d = json.loads(p.read_text()); d.pop("prestatus", None); p.write_text(json.dumps(d, indent=1))
        Path("primitives/prestatus.py").unlink(missing_ok=True)


def test_cipher_without_test_vectors_is_not_persisted_or_registered():
    """The persist gate registers ONLY a VERIFIED cipher. A structurally-valid definition with
    NO runnable test vectors must NOT reach primitives/ or the catalog (this is how a broken,
    unverified 'midori' with no test vectors got registered). It still builds in-memory."""
    skill = CipherDefinitionSkill()
    spec = CipherSpec(name="NoVecCipher", cipher_type="permutation", block_size=32,
                      word_bitsize=16, nbr_words=2, nbr_rounds=1,
                      round_structure=[LayerSpec("xor", {"input_indices": [[0, 1]],
                                                         "output_indices": [1]})])
    # no test_vectors on purpose
    with redirect_stdout(io.StringIO()):
        res = skill.execute(SkillRequest(skill=skill.name, params={"spec": spec.to_dict()}), Session())
    st = res.data["status"]
    assert st["built"] is True
    assert st["verified"] is False
    assert st["exported"] is False and st["registered"] is False
    assert "noveccipher" not in ci.CIPHER_CATALOG
    assert "NOT saved" in res.summary
    # and nothing was written to the custom catalog file
    p = Path("files/custom_ciphers.json")
    if p.exists():
        assert "noveccipher" not in json.loads(p.read_text())


def test_kat_problems_includes_a_traceback_pointing_at_the_failing_operator():
    """Tier-1a root-cause signal: when a spec builds but its KAT crashes, the repair problem now
    carries a concise OCP-frame traceback naming the failing operation, not just 'list index out
    of range' - so repair can localize the layer instead of blind-retrying."""
    inst = _API_CLS.__new__(_API_CLS)
    # add_constant with a 1-row constant_table but nbr_rounds=5 -> RC[i] overruns at eval time
    spec = {"name": "TbT", "cipher_type": "permutation", "block_size": 8, "word_bitsize": 4,
            "nbr_words": 2, "nbr_rounds": 5,
            "round_structure": [{"layer_type": "add_constant",
                                 "params": {"add_type": "xor", "constant_mask": [1, 1],
                                            "constant_table": [[1, 1]]}}],
            "test_vectors": [[[[1, 2]], [3, 4]]]}
    probs = inst._kat_problems(spec)
    assert probs
    blob = "\n".join(probs)
    assert "traceback" in blob.lower()
    assert "IndexError" in blob and "RC[i]" in blob   # the actual failing line is surfaced
