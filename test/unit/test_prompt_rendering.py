"""Guards for the .format()-based prompt templates.

A stray single-brace JSON example (e.g. an unescaped {"code": ...}) makes str.format raise
KeyError and silently breaks a whole prompt path - build_parse_prompt (agent intent parsing)
crashed exactly this way. These tests render every .format-ed prompt so such a regression fails
loudly here instead of only in a live LLM call.
"""
import string

from agent.llm import prompt_templates as pt


def test_build_parse_prompt_renders():
    p = pt.build_parse_prompt("run differential analysis on 3 rounds",
                              [{"name": "x", "description": "y"}], {"ctx": 1})
    assert isinstance(p, str) and len(p) > 100


def test_system_prompt_template_has_no_stray_format_fields():
    legit = {"cipher_catalog", "skills", "diff_goals", "linear_goals",
             "schema", "session_context", "cipher_dsl_schema"}
    fields = {fn for _, fn, _, _ in string.Formatter().parse(pt.SYSTEM_PROMPT_TEMPLATE)
              if fn is not None}
    stray = fields - legit
    assert not stray, f"unescaped single-brace JSON in SYSTEM_PROMPT_TEMPLATE: {stray}"


def test_repair_prompt_still_renders():
    rp = pt.build_repair_prompt({"cipher_type": "permutation", "round_structure": []}, ["problem"])
    assert isinstance(rp, str) and len(rp) > 100


def test_facts_response_schema_declares_all_top_level_representations():
    props = pt.TEXT_CIPHER_FACTS_RESPONSE_SCHEMA["properties"]["cipher_facts"]["properties"]
    for field in ("layout", "cell_layout", "arx", "key_archetype",
                  "pre_whitening", "post_whitening", "source_spans"):
        assert field in props, f"schema missing top-level field {field!r}"
