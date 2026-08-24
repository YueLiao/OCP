"""Verified example CipherSpecs used as few-shot anchors for LLM extraction.

Each spec here builds and passes its test vectors (see test/unit/test_cipher_examples.py),
so it doubles as a regression fixture and the single source of truth for the
on-prompt format. SPECK-32 and SIMON-32 reproduce the real ciphers (their test
vectors are the official known-answers); MiniSPN is a compact synthetic SPN whose
test vector was computed from the built cipher.
"""

import json

# --- SPECK-32 (ARX permutation): rotation + modular add + XOR ---
SPECK32 = {
    "name": "SPECK32",
    "cipher_type": "permutation",
    "block_size": 32,
    "word_bitsize": 16,
    "nbr_words": 2,
    "nbr_rounds": 22,
    "round_structure": [
        {"layer_type": "rotation", "params": {"direction": "r", "amount": 7, "word_index": 0}},
        {"layer_type": "modadd", "params": {"input_indices": [[0, 1]], "output_indices": [0]}},
        {"layer_type": "rotation", "params": {"direction": "l", "amount": 2, "word_index": 1}},
        {"layer_type": "xor", "params": {"input_indices": [[0, 1]], "output_indices": [1]}},
    ],
    "test_vectors": [{"input": [0x6574, 0x694C], "output": [0x689D, 0x44B7]}],
}

# --- SIMON-32 (AND-RX permutation): three rotations of word 0 into temp words
# 2,3,4, an AND-XOR, an XOR, then swap the two words. ---
SIMON32 = {
    "name": "SIMON32",
    "cipher_type": "permutation",
    "block_size": 32,
    "word_bitsize": 16,
    "nbr_words": 2,
    "nbr_temp_words": 3,
    "nbr_rounds": 32,
    "round_structure": [
        {"layer_type": "rotation", "params": {"direction": "l", "amount": 1, "word_index": 0, "out_index": 2}},
        {"layer_type": "rotation", "params": {"direction": "l", "amount": 8, "word_index": 0, "out_index": 3}},
        {"layer_type": "rotation", "params": {"direction": "l", "amount": 2, "word_index": 0, "out_index": 4}},
        {"layer_type": "andxor", "params": {"input_indices": [[2, 3, 1]], "output_indices": [1]}},
        {"layer_type": "xor", "params": {"input_indices": [[1, 4]], "output_indices": [1]}},
        {"layer_type": "permutation", "params": {"table": [1, 0]}},
    ],
    "test_vectors": [{"input": [0x6565, 0x6877], "output": [0xDB3C, 0x569B]}],
}

# --- MiniSPN (compact synthetic SPN): a 4-bit S-box on each word, then a word
# permutation. Shows the S-box table / index grouping / permutation-table format. ---
MINI_SPN = {
    "name": "MiniSPN",
    "cipher_type": "permutation",
    "block_size": 16,
    "word_bitsize": 4,
    "nbr_words": 4,
    "nbr_rounds": 4,
    "sbox_tables": {
        "S4": [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]
    },
    "round_structure": [
        {"layer_type": "sbox", "params": {"sbox_name": "S4", "index": [[0], [1], [2], [3]]}},
        {"layer_type": "permutation", "params": {"table": [1, 2, 3, 0]}},
    ],
    "test_vectors": [{"input": [0x1, 0x2, 0x3, 0x4], "output": [0x4, 0x2, 0xB, 0x5]}],
}

# --- MiniBlock (compact synthetic SPN block cipher): shows the key path -
# add-round-key, key schedule, subkey extraction, and block-cipher key params -
# on top of an SPN round (a permutation is the same cipher WITHOUT these). ---
MINI_BLOCK = {
    "name": "MiniBlock",
    "cipher_type": "blockcipher",
    "block_size": 16,
    "word_bitsize": 4,
    "nbr_words": 4,
    "nbr_rounds": 4,
    "key_size": 16,
    "key_word_bitsize": 4,
    "key_nbr_words": 4,
    "key_extract_indices": [0, 1, 2, 3],
    "sbox_tables": {
        "S4": [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]
    },
    # Evolving key schedule (SPECK/PRESENT/AES style): the KEY_SCHEDULE state is
    # updated every round by FIXED layers, and the per-round difference comes from a
    # rotation, a per-round constant table, and a word rotation - NOT from changing the
    # layer parameters each round. This is how round-dependent key schedules (e.g.
    # FUTURE's K0/K1 rotate-and-alternate) are modeled: rotate a key word in place, XOR
    # a per-round constant, then rotate which key words are used; key_extract_indices
    # pulls the subkey out each round.
    "key_schedule": [
        {"layer_type": "rotation", "params": {"direction": "l", "amount": 1, "word_index": 0}},
        {"layer_type": "add_constant", "params": {"add_type": "xor", "constant_mask": [1, None, None, None], "constant_table": [[1], [2], [3], [4]]}},
        {"layer_type": "permutation", "params": {"table": [1, 2, 3, 0]}},
    ],
    "round_structure": [
        {"layer_type": "add_round_key", "params": {"operator": "xor", "mask": [1, 1, 1, 1]}},
        {"layer_type": "sbox", "params": {"sbox_name": "S4", "index": [[0], [1], [2], [3]]}},
        {"layer_type": "permutation", "params": {"table": [1, 2, 3, 0]}},
    ],
    "test_vectors": [
        {"plaintext": [0x1, 0x2, 0x3, 0x4], "key": [0x5, 0x6, 0x7, 0x8], "output": [4, 15, 13, 4]}
    ],
}

# --- MiniSPNbit (compact synthetic BIT-ORIENTED SPN, PRESENT/GIFT style): the
# state is a bit array (word_bitsize=1), a 4-bit S-box is applied to groups of 4
# bits, then the bits are permuted. This is how bit-sliced ciphers (PRESENT, GIFT,
# KNOT) must be modeled - contrast with MiniSPN, which is word-oriented. ---
MINI_SPN_BIT = {
    "name": "MiniSPNbit",
    "cipher_type": "permutation",
    "block_size": 16,
    "word_bitsize": 1,
    "nbr_words": 16,
    "nbr_rounds": 4,
    "sbox_tables": {
        "S4": [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]
    },
    "round_structure": [
        {"layer_type": "sbox", "params": {"sbox_name": "S4", "index": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]}},
        {"layer_type": "permutation", "params": {"table": [0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15]}},
    ],
    "test_vectors": [
        {"input": [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1],
         "output": [1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1]}
    ],
}

# --- High-level BIT-SLICED example using the compact `layout` form (KNOT /
# RECTANGLE class). The state is a rows x cols bit grid; the expander turns
# subcolumn_sbox into a column S-box, shift_rows into a bit permutation, and
# add_round_constant{d,lfsr} into an LFSR round-constant schedule. Prefer this
# over hand-expanding index/permutation tables: for a real cipher (e.g. KNOT-256,
# 4x64) those tables have hundreds of entries and an LLM gets them wrong, whereas
# rows/cols/offsets/LFSR are a handful of numbers the expander turns into the
# concrete word_bitsize=1 layers deterministically. Use shift_rows only when
# diffusion is a per-row rotation; for an arbitrary bit permutation (PRESENT/GIFT)
# use the concrete MiniSPNbit form instead. ---
MINI_LAYOUT = {
    "name": "MiniLayout",
    "cipher_type": "permutation",
    "nbr_rounds": 4,
    "layout": {"rows": 4, "cols": 4},
    "sbox_tables": {
        "S4": [4, 0, 10, 7, 11, 14, 1, 13, 9, 15, 6, 8, 5, 2, 12, 3]
    },
    "round_structure": [
        {"layer_type": "add_round_constant", "params": {"d": 4, "lfsr": {"width": 4, "taps": [3, 2], "init": 1}}},
        {"layer_type": "subcolumn_sbox", "params": {"sbox_name": "S4"}},
        {"layer_type": "shift_rows", "params": {"offsets": [0, 1, 2, 3], "direction": "l"}},
    ],
    "test_vectors": [
        {"input": [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1],
         "output": [1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1]}
    ],
}

# --- WORD-oriented SPN with a GF(2^n) DIFFUSION MATRIX (AES MixColumns style). The
# matrix uses INTEGER coefficients (the GF element's integer form: 2=x, 3=x+1, 1=1),
# NOT symbols like "alpha^3"; "indices" groups the words each application acts on;
# "polynomial" is the reduction poly minus its top term. This is how AES/FUTURE (GF
# matrices) and SKINNY (a binary GF(2) matrix, which omits polynomial) are modeled. ---
MINI_MDS = {
    "name": "MiniMDS",
    "cipher_type": "permutation",
    "block_size": 16,
    "word_bitsize": 4,
    "nbr_words": 4,
    "nbr_rounds": 3,
    "sbox_tables": {
        "S4": [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]
    },
    "round_structure": [
        {"layer_type": "sbox", "params": {"sbox_name": "S4", "index": [[0], [1], [2], [3]]}},
        {"layer_type": "matrix", "params": {
            "matrix": [[2, 3, 1, 1], [1, 2, 3, 1], [1, 1, 2, 3], [3, 1, 1, 2]],
            "indices": [[0, 1, 2, 3]],
            "polynomial": "0x3",
        }},
    ],
    "test_vectors": [{"input": [1, 2, 3, 4], "output": [6, 1, 1, 8]}],
}

# --- TWEAKABLE block cipher (SKINNY/Deoxys tweakey style). OCP has no separate tweak
# input: the tweak is concatenated with the key, so key_size = key_bits + tweak_bits and
# the whole thing is the key state. The tweakey schedule updates the state every round -
# here a bit-level GF(2) LFSR ("gf2_linear") on the tweak branch's words plus a word
# permutation - and key_extract_indices pulls a NON-CONTIGUOUS subkey (words 0,2,4,6).
# gf2_linear is a per-word BIT matrix (a tweakey LFSR), distinct from "matrix" (a GF(2^n)
# word-diffusion matrix). ---
MINI_TWEAK = {
    "name": "MiniTweak",
    "cipher_type": "blockcipher",
    "block_size": 16,
    "word_bitsize": 4,
    "nbr_words": 4,
    "nbr_rounds": 3,
    "key_size": 32,          # 16-bit key + 16-bit tweak, treated as one key state
    "key_word_bitsize": 4,
    "key_nbr_words": 8,
    "key_extract_indices": [0, 2, 4, 6],   # non-contiguous subkey selection
    "sbox_tables": {
        "S4": [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]
    },
    "key_schedule": [
        {"layer_type": "gf2_linear", "params": {"matrix": [[0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [1, 1, 0, 0]], "index_in": [4, 5, 6, 7], "index_out": [4, 5, 6, 7]}},
        {"layer_type": "permutation", "params": {"table": [4, 5, 6, 7, 0, 1, 2, 3]}},
    ],
    "round_structure": [
        {"layer_type": "add_round_key", "params": {"operator": "xor", "mask": [1, 1, 1, 1]}},
        {"layer_type": "sbox", "params": {"sbox_name": "S4", "index": [[0], [1], [2], [3]]}},
        {"layer_type": "permutation", "params": {"table": [1, 2, 3, 0]}},
    ],
    "test_vectors": [
        {"plaintext": [1, 2, 3, 4], "key": [5, 6, 7, 8, 9, 10, 11, 12], "output": [6, 6, 4, 3]}
    ],
}

EXAMPLE_SPECS = {
    "speck32": SPECK32,
    "simon32": SIMON32,
    "mini_spn": MINI_SPN,
    "mini_spn_bit": MINI_SPN_BIT,
    "mini_layout": MINI_LAYOUT,
    "mini_mds": MINI_MDS,
    "mini_block": MINI_BLOCK,
    "mini_tweak": MINI_TWEAK,
}

_DESCRIPTIONS = {
    "speck32": (
        "SPECK-32, an ARX permutation: 32-bit state, two 16-bit words, 22 rounds. "
        "Each round rotates word 0 right by 7, modular-adds words 0 and 1 into word 0, "
        "rotates word 1 left by 2, then XORs words 0 and 1 into word 1."
    ),
    "simon32": (
        "SIMON-32, an AND-RX permutation: 32-bit state, two 16-bit words, 32 rounds, "
        "using three temporary words (indices 2,3,4) to hold rotated copies of word 0. "
        "Each round: rotate word 0 left by 1, 8, 2 into temp words 2, 3, 4; set word 1 = "
        "(word2 AND word3) XOR word1; XOR word 4 into word 1; then swap the two words."
    ),
    "mini_spn": (
        "A small WORD-ORIENTED SPN permutation (AES style, where the state is words/"
        "bytes): 16-bit state, four 4-bit words (word_bitsize=4), 4 rounds. Each round "
        "applies a 4-bit S-box to every word (index [[0],[1],[2],[3]]), then permutes "
        "the four words. Use this layout when the S-box acts on whole words/bytes."
    ),
    "mini_mds": (
        "A WORD-ORIENTED SPN with a GF(2^n) DIFFUSION MATRIX (AES MixColumns style): "
        "16-bit state, four 4-bit words, 3 rounds. Each round applies a 4-bit S-box to "
        "every word, then multiplies the four words by an MDS matrix over GF(2^4). The "
        "matrix uses INTEGER coefficients (the GF element's integer form: 2=x, 3=x+1, "
        "1=1, NEVER symbols like alpha^3 -> alpha^3 is 8); 'indices' groups the words "
        "each application acts on; 'polynomial' is the reduction poly minus its top term "
        "(here x^4+x+1 -> '0x3'; AES GF(2^8) uses '0x1B'; a binary GF(2) matrix like "
        "SKINNY's omits polynomial). Use this for a MixColumns/MDS/near-MDS matrix "
        "(AES, FUTURE, SKINNY)."
    ),
    "mini_spn_bit": (
        "A small BIT-ORIENTED SPN permutation (PRESENT/GIFT style, bit-sliced): the "
        "state is a bit array, so word_bitsize=1 and nbr_words = block size in bits "
        "(16 here), 4 rounds. Each round applies a 4-bit S-box to GROUPS of 4 bits "
        "(index [[0,1,2,3],[4,5,6,7],...]) then permutes the individual bits (a bit "
        "permutation table). Use this layout for bit-sliced ciphers where the S-box "
        "spans a column of bits and diffusion is a bit permutation (PRESENT, GIFT, KNOT)."
    ),
    "mini_layout": (
        "A BIT-SLICED permutation in the compact LAYOUT form (KNOT/RECTANGLE style). "
        "The state is a rows x cols bit grid (layout: 4 rows x 4 cols = 16 bits here); "
        "you give layout + high-level layers and OCP expands them. Each round: "
        "add_round_constant{d, lfsr} XORs an LFSR-generated d-bit round constant into the "
        "first row; subcolumn_sbox applies the S-box down each column of bits (row 0 = LSB); "
        "shift_rows rotates each row by offsets[r]. Use this whenever a cipher has round "
        "constants (LFSR), per-row rotations, or a large state where hand-writing the S-box "
        "index groups and permutation table would be error-prone (KNOT, RECTANGLE, ASCON)."
    ),
    "mini_block": (
        "A small SPN block cipher with an EVOLVING key schedule: 16-bit state and 16-bit key, "
        "four 4-bit words, 4 rounds. Each round XORs the round subkey into all four words, "
        "applies a 4-bit S-box to every word, then permutes the four words. KEY SCHEDULE (the "
        "pattern for round-dependent key schedules like SPECK/PRESENT/AES/FUTURE): the key state "
        "is updated every round by the SAME fixed layers - rotate a key word in place "
        "(rotation), XOR a per-round constant (add_constant with a per-round constant_table), "
        "then rotate which key words are used (permutation) - and key_extract_indices pulls the "
        "subkey out each round. The round-dependence comes from the constant table + word "
        "rotation, NOT from changing layer parameters per round (which the model can't express). "
        "For a schedule that alternates between key words (e.g. FUTURE's K0/K1), let the word "
        "permutation rotate them into a fixed position that the fixed layers then act on."
    ),
    "mini_tweak": (
        "A TWEAKABLE block cipher in the SKINNY/Deoxys tweakey style: 16-bit state, four 4-bit "
        "words, 3 rounds. OCP has NO separate tweak input - concatenate the tweak with the key "
        "so key_size = key_bits + tweak_bits (32 here = 16 key + 16 tweak) and treat the whole "
        "thing as the key state. The tweakey schedule updates the state every round with a "
        "bit-level GF(2) LFSR (layer_type 'gf2_linear': a word_bitsize x word_bitsize BINARY "
        "matrix applied to each listed word - distinct from 'matrix', which is a GF(2^n) "
        "word-diffusion matrix) on the tweak branch's words, plus a word permutation; then "
        "key_extract_indices pulls the subkey, which may be NON-CONTIGUOUS (words 0,2,4,6). "
        "Use this for any tweakable cipher (SKINNY, Deoxys, CRAFT) or any key/tweakey LFSR that "
        "mixes the bits of a word."
    ),
}


def _spec_to_facts(spec):
    """Render a CipherSpec dict in the CipherFacts shape the text-first prompt emits."""
    facts = {
        "name": spec["name"],
        "primitive_type": spec["cipher_type"],
        "rounds": {"nbr_rounds": spec["nbr_rounds"]},
        "operations": [
            {"type": layer["layer_type"], "params": layer["params"]}
            for layer in spec["round_structure"]
        ],
        "tables": {"sbox_tables": spec.get("sbox_tables", {})},
        "test_vectors": spec.get("test_vectors", []),
    }
    if "layout" in spec:
        # Bit-sliced layout: state scalars are derived by expansion, not given.
        facts["layout"] = spec["layout"]
        facts["state"] = {}
    else:
        facts["state"] = {
            "block_size": spec["block_size"],
            "word_bitsize": spec["word_bitsize"],
            "nbr_words": spec["nbr_words"],
            "nbr_temp_words": spec.get("nbr_temp_words", 0),
        }
    if spec["cipher_type"] == "blockcipher":
        facts["key_schedule"] = {
            "key_size": spec.get("key_size"),
            "key_word_bitsize": spec.get("key_word_bitsize"),
            "key_nbr_words": spec.get("key_nbr_words"),
            "key_extract_indices": spec.get("key_extract_indices"),
            "round_structure": [
                {"type": layer["layer_type"], "params": layer["params"]}
                for layer in spec.get("key_schedule", [])
            ],
        }
    return facts


_ANTI_COPY = (
    "These are only format references. Model the cipher the user actually describes: "
    "do not copy the examples' rounds, word counts, operations, or test vectors."
)

# Weighted keyword signals per example family, used to pick the closest example(s)
# to a described cipher so we spend few-shot tokens only on relevant ones. Bare
# "and" is deliberately avoided (natural language "words 0 and 1" is noise); the
# bitwise-AND signal relies on stronger markers. Matched case-insensitively.
_FAMILY_KEYWORDS = {
    "speck32": [("modular add", 3), ("modadd", 3), ("mod add", 3), ("addition modulo", 3),
                ("rotate", 1), ("rotation", 1), ("rotl", 1), ("rotr", 1), (">>>", 1), ("<<<", 1)],
    "simon32": [("bitwise and", 5), ("and-rx", 5), ("andrx", 5), (" & ", 4),
                ("boolean and", 4), ("logical and", 4)],
    # word-oriented SPN (S-box acts on whole words/bytes), diffusion by word permutation
    "mini_spn": [("s-box", 2), ("sbox", 2), ("s box", 2), ("substitution", 2),
                 ("byte", 3), ("nibble", 3), ("word-oriented", 5), ("per word", 3),
                 ("each word", 3), ("per byte", 3), ("each byte", 3), ("permute", 2)],
    # word-oriented SPN with a GF(2^n)/binary DIFFUSION MATRIX (AES/FUTURE/SKINNY)
    "mini_mds": [("mixcolumns", 5), ("mix columns", 5), ("mix_columns", 5), ("mds", 5),
                 ("near-mds", 5), ("diffusion matrix", 5), ("gf(2", 4), ("finite field", 3),
                 ("galois field", 3), ("branch number", 4), ("optimal diffusion", 5),
                 ("matrix", 3), ("aes", 3), ("skinny", 4), ("future", 3)],
    # bit-oriented / bit-sliced SPN with an ARBITRARY bit permutation (PRESENT/GIFT)
    "mini_spn_bit": [("s-box", 2), ("sbox", 2), ("substitution", 2),
                     ("bit permutation", 5), ("bit-permutation", 5), ("bitpermutation", 5),
                     ("bit-sliced", 3), ("bitsliced", 3), ("bit slice", 3), ("bit-oriented", 4),
                     ("present", 4), ("gift", 4), ("1-bit", 4), ("one-bit", 4)],
    # bit-sliced LAYOUT form: round constants (LFSR) and/or per-row rotations (KNOT)
    "mini_layout": [("round constant", 4), ("round_constant", 4), ("roundconstant", 4),
                  ("lfsr", 5), ("shift row", 5), ("shiftrow", 5), ("shift-row", 5),
                  ("rotate each row", 5), ("row rotation", 4), ("rotate rows", 4),
                  ("knot", 5), ("rectangle", 4), ("subcolumn", 5), ("sub-column", 5),
                  ("bit-sliced", 3), ("bitsliced", 3)],
    "mini_block": [("key schedule", 5), ("key evolution", 5), ("round key", 4), ("round key generation", 5),
                   ("subkey", 4), ("add round key", 4), ("addroundkey", 4), ("block cipher", 3),
                   ("master key", 3), ("whitening key", 4), ("key expansion", 5), ("round constant", 2)],
    # tweakable / tweakey framework: tweak folded into the key, per-word bit LFSR (gf2_linear)
    "mini_tweak": [("tweakable", 6), ("tweakey", 6), ("tweak", 5), ("deoxys", 6), ("craft", 4),
                   ("qarma", 4), ("key lfsr", 5), ("tweakey schedule", 6)],
}


def select_examples(text, k=2):
    """Pick the k example keys whose family best matches the described cipher.

    Deterministic keyword scoring - no LLM. Always returns at least one; when a
    block-cipher signal is present it includes the block example alongside the best
    round-family example (so both the round format and the key format are shown).
    Falls back to ARX + SPN when nothing matches.
    """
    t = (text or "").lower()
    scores = {key: sum(w for kw, w in kws if kw in t) for key, kws in _FAMILY_KEYWORDS.items()}
    if max(scores.values(), default=0) == 0:
        return ["speck32", "mini_spn"][:k]

    ranked = sorted(scores, key=lambda key: scores[key], reverse=True)
    chosen = []
    for key in ranked:  # best round-family (non-block) with a signal
        if key != "mini_block" and scores[key] > 0:
            chosen.append(key)
            break
    if scores["mini_block"] > 0 and "mini_block" not in chosen:
        chosen.append("mini_block")
    for key in ranked:  # fill remaining slots by score
        if len(chosen) >= k:
            break
        if key not in chosen and scores[key] > 0:
            chosen.append(key)
    return chosen[:k] or ["speck32"]


def _slim(spec):
    """Drop test vectors from a spec for the prompt: they teach no structure and
    the TV format is documented in the prompt rules. S-box tables are kept (small,
    and they teach the name->table format)."""
    return {key: value for key, value in spec.items() if key != "test_vectors"}


def _render(keys, as_facts):
    # Compact JSON (no whitespace) - the model parses it fine and it costs far
    # fewer tokens than pretty-printed examples.
    blocks = []
    for idx, key in enumerate(keys, 1):
        slim = _slim(EXAMPLE_SPECS[key])
        if as_facts:
            body = json.dumps({"cipher_facts": _spec_to_facts(slim)}, separators=(",", ":"))
        else:
            body = "CipherSpec: " + json.dumps(slim, separators=(",", ":"))
        blocks.append(f"Example {idx}: {_DESCRIPTIONS[key]}\n{body}")
    return _ANTI_COPY + "\n\n" + "\n\n".join(blocks)


def few_shot_spec_text(text=None, k=2):
    """Few-shot in CipherSpec form, limited to the example(s) closest to `text`."""
    return _render(select_examples(text, k), as_facts=False)


def few_shot_facts_text(text=None, k=2):
    """Few-shot in CipherFacts form, limited to the example(s) closest to `text`."""
    return _render(select_examples(text, k), as_facts=True)
