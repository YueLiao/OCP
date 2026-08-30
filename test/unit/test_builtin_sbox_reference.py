"""A cipher spec may REFERENCE a built-in OCP S-box by name (no table) - the enabler for the
human-in-the-loop "the S-box is already stored, use it directly" resolution.

Covers the resolver (operators.Sbox.builtin_sbox_class), validate() accepting a built-in
reference, and the builder placing the real built-in operator - plus that a custom table still
wins over a built-in of the same name, and an unknown name is rejected.
"""

from operators.Sbox import builtin_sbox_class, builtin_sbox_names
from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_permutation_from_spec


def _perm(sbox_name, sbox_tables=None, word_bitsize=4):
    return CipherSpec(
        name="Ref", cipher_type="permutation",
        block_size=2 * word_bitsize, word_bitsize=word_bitsize, nbr_words=2, nbr_rounds=1,
        sbox_tables=sbox_tables or {},
        round_structure=[LayerSpec("sbox", {"sbox_name": sbox_name, "index": [[0], [1]]})],
    )


def _sbox_ops(prim):
    return {c.__class__.__name__
            for f in prim.functions.values()
            for rnd in getattr(f, "constraints", [])
            for layer in rnd for c in layer if "Sbox" in c.__class__.__name__}


# --- resolver -------------------------------------------------------------

def test_resolver_finds_builtins_by_name_and_suffix():
    assert builtin_sbox_class("PRESENT_Sbox").__name__ == "PRESENT_Sbox"
    assert builtin_sbox_class("AES").__name__ == "AES_Sbox"            # '_Sbox' suffix added
    assert builtin_sbox_class("Midori128_SSb0").__name__ == "Midori128_SSb0_Sbox"
    assert builtin_sbox_class("NoSuchBox") is None
    assert "PRESENT_Sbox" in builtin_sbox_names() and len(builtin_sbox_names()) > 10


# --- validate + build with a built-in reference (no table) ----------------

def test_validate_accepts_builtin_reference_without_table():
    assert _perm("PRESENT_Sbox").validate() == []


def test_build_places_the_builtin_operator():
    prim = build_permutation_from_spec(_perm("PRESENT_Sbox"))
    assert _sbox_ops(prim) == {"PRESENT_Sbox"}


def test_validate_rejects_unknown_sbox():
    errors = _perm("NoSuchBox").validate()
    assert any("not found in sbox_tables and is not a built-in" in e for e in errors)


# --- precedence: a custom table of the same name wins over the built-in ----

def test_custom_table_takes_precedence_over_builtin():
    # a custom 'PRESENT_Sbox' table (identity here) must be used, not the real built-in
    spec = _perm("PRESENT_Sbox", sbox_tables={"PRESENT_Sbox": list(range(16))})
    assert spec.validate() == []
    prim = build_permutation_from_spec(spec)
    # the custom table builds a CustomSbox-derived class named 'PRESENT_Sbox' whose table is identity;
    # both are named 'PRESENT_Sbox', so assert the value differs via a KAT-free structural check:
    # the custom one carries the identity table.
    tables = [c.table for f in prim.functions.values() for rnd in getattr(f, "constraints", [])
              for layer in rnd for c in layer if c.__class__.__name__ == "PRESENT_Sbox"]
    assert tables and tables[0] == list(range(16))     # identity custom table, not the real S-box
