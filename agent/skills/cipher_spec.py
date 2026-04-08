"""Data model for describing custom cipher algorithms.

A CipherSpec fully describes a cipher's structure in a way that can be:
1. Constructed from natural language via LLM dialogue
2. Written as JSON/dict by the user directly
3. Used to dynamically build an OCP Primitive object

Example - SPECK32 as a CipherSpec:
    spec = CipherSpec(
        name="MySpeck32",
        cipher_type="permutation",
        block_size=32,
        word_bitsize=16,
        nbr_words=2,
        nbr_rounds=22,
        round_structure=[
            LayerSpec("rotation", {"direction": "r", "amount": 7, "word_index": 0}),
            LayerSpec("modadd", {"input_indices": [[0, 1]], "output_indices": [0]}),
            LayerSpec("rotation", {"direction": "l", "amount": 2, "word_index": 1}),
            LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]}),
        ],
    )
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LayerSpec:
    """Specification of a single layer in a cipher round.

    Supported layer_type values and their params:

    "sbox":
        sbox_name: str - key into CipherSpec.sbox_tables
        index: List[List[int]] - grouping of word indices for S-box application
            e.g., [[0,1,2,3],[4,5,6,7]] applies 4-bit S-box to words 0-3, then 4-7
        mask: Optional[List[int]] - which groups to apply (1) vs identity (0)

    "permutation":
        table: List[int] - permutation mapping (output[j] = input[table[j]])

    "rotation":
        direction: str - "l" (left) or "r" (right)
        amount: int - rotation amount in bits
        word_index: int - which word to rotate
        out_index: Optional[int] - output position (defaults to word_index)

    "xor":
        input_indices: List[List[int]] - groups of input word indices
        output_indices: List[int] - output word indices
        e.g., input_indices=[[0,1]], output_indices=[1] means w1 = XOR(w0, w1)

    "modadd":
        input_indices: List[List[int]] - groups of input word indices
        output_indices: List[int] - output word indices
        e.g., input_indices=[[0,1]], output_indices=[0] means w0 = (w0 + w1) mod 2^n

    "matrix":
        matrix: List[List[int]] - square matrix for multiplication
        indices: List[List[int]] - groups of word indices to apply matrix to
        polynomial: Optional[int] - irreducible polynomial for GF(2^n)

    "add_round_key":
        operator: str - "xor" or "modadd"
        mask: Optional[List[int]] - which words get key addition (1) vs identity (0)

    "add_constant":
        add_type: str - "xor" or "modadd"
        constant_mask: List - which words receive constants (True/None)
        constant_table: List[List[int]] - per-round constant values
    """

    layer_type: str
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {"layer_type": self.layer_type, "params": self.params}

    @classmethod
    def from_dict(cls, d):
        return cls(layer_type=d["layer_type"], params=d.get("params", {}))


@dataclass
class CipherSpec:
    """Complete specification of a cipher algorithm.

    This dataclass captures everything needed to dynamically build an OCP Primitive.
    """

    # Basic parameters
    name: str = "CustomCipher"
    cipher_type: str = "permutation"  # "permutation" or "blockcipher"
    block_size: int = 64
    word_bitsize: int = 32
    nbr_words: int = 2
    nbr_rounds: int = 16
    nbr_temp_words: int = 0

    # Round structure (applied identically each round)
    round_structure: List[LayerSpec] = field(default_factory=list)

    # Block cipher key parameters (only if cipher_type == "blockcipher")
    key_size: Optional[int] = None
    key_word_bitsize: Optional[int] = None
    key_nbr_words: Optional[int] = None
    key_nbr_temp_words: int = 0
    key_schedule: Optional[List[LayerSpec]] = None  # layers per key round
    key_extract_indices: Optional[List[int]] = None  # which key words form the subkey

    # S-box tables: name -> lookup table
    sbox_tables: Dict[str, List[int]] = field(default_factory=dict)

    # Test vectors: list of ([inputs], outputs)
    test_vectors: Optional[list] = None

    def validate(self) -> List[str]:
        """Validate the spec and return a list of error messages (empty if valid)."""
        errors = []
        if not self.name:
            errors.append("Cipher name is required.")
        if self.cipher_type not in ("permutation", "blockcipher"):
            errors.append(f"Invalid cipher_type: '{self.cipher_type}'. Use 'permutation' or 'blockcipher'.")
        if self.block_size <= 0:
            errors.append("block_size must be positive.")
        if self.word_bitsize <= 0:
            errors.append("word_bitsize must be positive.")
        if self.nbr_words <= 0:
            errors.append("nbr_words must be positive.")
        if self.nbr_rounds <= 0:
            errors.append("nbr_rounds must be positive.")
        if not self.round_structure:
            errors.append("round_structure must have at least one layer.")

        valid_layer_types = {"sbox", "permutation", "rotation", "xor", "modadd", "matrix", "add_round_key", "add_constant"}
        for i, layer in enumerate(self.round_structure):
            if layer.layer_type not in valid_layer_types:
                errors.append(f"Round layer {i}: invalid type '{layer.layer_type}'. Valid: {valid_layer_types}")

        # Validate S-box references
        for i, layer in enumerate(self.round_structure):
            if layer.layer_type == "sbox":
                sbox_name = layer.params.get("sbox_name", "")
                if sbox_name and sbox_name not in self.sbox_tables:
                    errors.append(f"Round layer {i}: S-box '{sbox_name}' not found in sbox_tables.")

        # Block cipher validation
        if self.cipher_type == "blockcipher":
            if self.key_size is None or self.key_size <= 0:
                errors.append("Block cipher requires a positive key_size.")
            if self.key_nbr_words is None or self.key_nbr_words <= 0:
                errors.append("Block cipher requires key_nbr_words.")
            if self.key_extract_indices is None:
                errors.append("Block cipher requires key_extract_indices (which key words form the subkey).")

        return errors

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict."""
        d = {
            "name": self.name,
            "cipher_type": self.cipher_type,
            "block_size": self.block_size,
            "word_bitsize": self.word_bitsize,
            "nbr_words": self.nbr_words,
            "nbr_rounds": self.nbr_rounds,
            "nbr_temp_words": self.nbr_temp_words,
            "round_structure": [l.to_dict() for l in self.round_structure],
            "sbox_tables": self.sbox_tables,
        }
        if self.cipher_type == "blockcipher":
            d.update({
                "key_size": self.key_size,
                "key_word_bitsize": self.key_word_bitsize,
                "key_nbr_words": self.key_nbr_words,
                "key_nbr_temp_words": self.key_nbr_temp_words,
                "key_schedule": [l.to_dict() for l in (self.key_schedule or [])],
                "key_extract_indices": self.key_extract_indices,
            })
        if self.test_vectors:
            d["test_vectors"] = self.test_vectors
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CipherSpec":
        """Construct from a dict (e.g., parsed from JSON)."""
        spec = cls(
            name=d.get("name", "CustomCipher"),
            cipher_type=d.get("cipher_type", "permutation"),
            block_size=d.get("block_size", 64),
            word_bitsize=d.get("word_bitsize", 32),
            nbr_words=d.get("nbr_words", 2),
            nbr_rounds=d.get("nbr_rounds", 16),
            nbr_temp_words=d.get("nbr_temp_words", 0),
            round_structure=[LayerSpec.from_dict(l) for l in d.get("round_structure", [])],
            sbox_tables=d.get("sbox_tables", {}),
            test_vectors=d.get("test_vectors"),
        )
        if spec.cipher_type == "blockcipher":
            spec.key_size = d.get("key_size")
            spec.key_word_bitsize = d.get("key_word_bitsize")
            spec.key_nbr_words = d.get("key_nbr_words")
            spec.key_nbr_temp_words = d.get("key_nbr_temp_words", 0)
            spec.key_schedule = [LayerSpec.from_dict(l) for l in d.get("key_schedule", [])]
            spec.key_extract_indices = d.get("key_extract_indices")
        return spec
