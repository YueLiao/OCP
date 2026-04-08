"""Skill that dynamically builds an OCP Primitive from a CipherSpec.

This is the core skill that bridges the gap between a structured cipher description
and an actual OCP cipher object that can be analyzed, visualized, and implemented.
"""

import math
from typing import Any, Dict, List

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill
from agent.skills.cipher_spec import CipherSpec, LayerSpec


def create_sbox_class(name, table):
    """Create an Sbox operator class from a lookup table at runtime.

    Args:
        name: Name for the S-box class.
        table: Lookup table (list of ints). Length must be a power of 2.

    Returns:
        A new Sbox subclass with the given table.
    """
    from operators.Sbox import Sbox

    input_bitsize = int(math.log2(len(table)))
    output_bitsize = input_bitsize  # assume square S-box

    class CustomSbox(Sbox):
        def __init__(self, input_vars, output_vars, ID=None):
            super().__init__(input_vars, output_vars, input_bitsize, output_bitsize, ID=ID)
            self.table = list(table)

    CustomSbox.__name__ = name
    CustomSbox.__qualname__ = name
    return CustomSbox


def _apply_layer(func, round_idx, layer_idx, layer_spec, sbox_classes):
    """Apply a single LayerSpec to a Layered_Function.

    Args:
        func: OCP Layered_Function instance.
        round_idx: Current round number.
        layer_idx: Current layer index within the round.
        layer_spec: LayerSpec describing the operation.
        sbox_classes: Dict mapping S-box names to Sbox operator classes.
    """
    from operators.boolean_operators import XOR
    from operators.modular_operators import ModAdd

    lt = layer_spec.layer_type
    p = layer_spec.params

    if lt == "rotation":
        direction = p["direction"]
        amount = p["amount"]
        word_index = p["word_index"]
        out_index = p.get("out_index")
        if out_index is not None:
            rot = [direction, amount, word_index, out_index]
        else:
            rot = [direction, amount, word_index]
        func.RotationLayer(f"ROT_{layer_idx}", round_idx, layer_idx, rot)

    elif lt == "xor":
        input_indices = p["input_indices"]
        output_indices = p["output_indices"]
        func.SingleOperatorLayer(f"XOR_{layer_idx}", round_idx, layer_idx, XOR, input_indices, output_indices)

    elif lt == "modadd":
        input_indices = p["input_indices"]
        output_indices = p["output_indices"]
        func.SingleOperatorLayer(f"ADD_{layer_idx}", round_idx, layer_idx, ModAdd, input_indices, output_indices)

    elif lt == "sbox":
        sbox_name = p["sbox_name"]
        index = p.get("index")
        mask = p.get("mask")
        sbox_cls = sbox_classes[sbox_name]
        func.SboxLayer(f"SB_{layer_idx}", round_idx, layer_idx, sbox_cls, mask=mask, index=index)

    elif lt == "permutation":
        table = p["table"]
        func.PermutationLayer(f"P_{layer_idx}", round_idx, layer_idx, table)

    elif lt == "matrix":
        mat = p["matrix"]
        indices = p["indices"]
        polynomial = p.get("polynomial")
        func.MatrixLayer(f"MAT_{layer_idx}", round_idx, layer_idx, mat, indices, polynomial=polynomial)

    elif lt == "add_round_key":
        operator = p.get("operator", "xor")
        mask = p.get("mask")
        op_cls = XOR if operator == "xor" else ModAdd
        SK = func._parent_cipher.functions["SUBKEYS"]
        func.AddRoundKeyLayer(f"ARK_{layer_idx}", round_idx, layer_idx, op_cls, SK, mask=mask)

    elif lt == "add_constant":
        add_type = p.get("add_type", "xor")
        constant_mask = p["constant_mask"]
        constant_table = p["constant_table"]
        func.AddConstantLayer(f"C_{layer_idx}", round_idx, layer_idx, add_type, constant_mask, constant_table)

    else:
        raise ValueError(f"Unknown layer type: {lt}")


def build_permutation_from_spec(spec):
    """Build an OCP Permutation from a CipherSpec.

    Args:
        spec: CipherSpec with cipher_type="permutation".

    Returns:
        An OCP Permutation primitive.
    """
    from primitives.primitives import Permutation
    import variables.variables as var

    # Create S-box classes
    sbox_classes = {}
    for sbox_name, table in spec.sbox_tables.items():
        sbox_classes[sbox_name] = create_sbox_class(sbox_name, table)

    # Create input/output variables
    s_input = [var.Variable(spec.word_bitsize, ID=f"in{i}") for i in range(spec.nbr_words)]
    s_output = [var.Variable(spec.word_bitsize, ID=f"out{i}") for i in range(spec.nbr_words)]

    nbr_layers = len(spec.round_structure)
    config = [nbr_layers, spec.nbr_words, spec.nbr_temp_words, spec.word_bitsize]

    # Create permutation using a dynamic subclass
    class DynamicPermutation(Permutation):
        def __init__(self, name, s_in, s_out, nbr_rounds, cfg):
            super().__init__(name, s_in, s_out, nbr_rounds, cfg)
            S = self.functions["PERMUTATION"]
            for i in range(1, nbr_rounds + 1):
                for layer_idx, layer_spec in enumerate(spec.round_structure):
                    _apply_layer(S, i, layer_idx, layer_spec, sbox_classes)

    perm = DynamicPermutation(
        f"{spec.name}_PERM", s_input, s_output, spec.nbr_rounds, config
    )
    if spec.test_vectors:
        perm.test_vectors = spec.test_vectors
    perm.post_initialization()
    return perm


def build_blockcipher_from_spec(spec):
    """Build an OCP Block_cipher from a CipherSpec.

    Args:
        spec: CipherSpec with cipher_type="blockcipher".

    Returns:
        An OCP Block_cipher primitive.
    """
    from primitives.primitives import Block_cipher
    import variables.variables as var
    import operators.operators as op

    # Create S-box classes
    sbox_classes = {}
    for sbox_name, table in spec.sbox_tables.items():
        sbox_classes[sbox_name] = create_sbox_class(sbox_name, table)

    key_word_bitsize = spec.key_word_bitsize or spec.word_bitsize
    key_nbr_words = spec.key_nbr_words or (spec.key_size // key_word_bitsize)

    # Create input/output variables
    p_input = [var.Variable(spec.word_bitsize, ID=f"p{i}") for i in range(spec.nbr_words)]
    k_input = [var.Variable(key_word_bitsize, ID=f"k{i}") for i in range(key_nbr_words)]
    c_output = [var.Variable(spec.word_bitsize, ID=f"c{i}") for i in range(spec.nbr_words)]

    s_nbr_layers = len(spec.round_structure)
    k_nbr_layers = len(spec.key_schedule) if spec.key_schedule else 1
    sk_nbr_layers = 1
    sk_nbr_words = len(spec.key_extract_indices)

    s_config = [s_nbr_layers, spec.nbr_words, spec.nbr_temp_words, spec.word_bitsize]
    k_config = [k_nbr_layers, key_nbr_words, spec.key_nbr_temp_words, key_word_bitsize]
    sk_config = [sk_nbr_layers, sk_nbr_words, 0, spec.word_bitsize]

    k_nbr_rounds = spec.nbr_rounds  # key schedule rounds = cipher rounds

    class DynamicBlockCipher(Block_cipher):
        def __init__(self, name, p_in, k_in, c_out, nbr_rounds, k_rounds, s_cfg, k_cfg, sk_cfg):
            super().__init__(name, p_in, k_in, c_out, nbr_rounds, k_rounds, s_cfg, k_cfg, sk_cfg)

            S = self.functions["PERMUTATION"]
            KS = self.functions["KEY_SCHEDULE"]
            SK = self.functions["SUBKEYS"]

            # Subkey extraction
            for i in range(1, nbr_rounds + 1):
                SK.ExtractionLayer("SK_EX", i, 0, spec.key_extract_indices, KS.vars[i][0])

            # Key schedule
            if spec.key_schedule:
                for i in range(1, nbr_rounds):
                    for layer_idx, layer_spec in enumerate(spec.key_schedule):
                        _apply_layer(KS, i, layer_idx, layer_spec, sbox_classes)

            # Round function - store parent ref for add_round_key layers
            S._parent_cipher = self
            for i in range(1, nbr_rounds + 1):
                for layer_idx, layer_spec in enumerate(spec.round_structure):
                    _apply_layer(S, i, layer_idx, layer_spec, sbox_classes)

    cipher = DynamicBlockCipher(
        spec.name, p_input, k_input, c_output,
        spec.nbr_rounds, k_nbr_rounds,
        s_config, k_config, sk_config,
    )
    if spec.test_vectors:
        cipher.test_vectors = spec.test_vectors
    cipher.post_initialization()
    return cipher


class CipherDefinitionSkill(BaseSkill):
    """Build an OCP cipher from a CipherSpec specification."""

    @property
    def name(self) -> SkillName:
        return SkillName.CIPHER_DEFINITION

    @property
    def description(self) -> str:
        return (
            "Define and build a custom cipher from a structured specification (CipherSpec). "
            "Supports permutations and block ciphers with arbitrary round structures "
            "including S-boxes, rotations, XOR, modular addition, permutations, and matrices."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "spec": {
                "type": "object",
                "required": True,
                "description": "CipherSpec as a dict. See agent/skills/cipher_spec.py for the full schema.",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        params = request.params

        # Accept spec as dict or from session metadata
        spec_data = params.get("spec")
        if spec_data is None:
            spec_data = session.get_metadata("pending_cipher_spec")

        if spec_data is None:
            return SkillResult(
                success=False,
                skill=self.name,
                error="No cipher specification provided. Pass 'spec' parameter or use cipher_dialogue first.",
            )

        # Build CipherSpec from dict
        if isinstance(spec_data, dict):
            spec = CipherSpec.from_dict(spec_data)
        elif isinstance(spec_data, CipherSpec):
            spec = spec_data
        else:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Invalid spec type: {type(spec_data)}. Expected dict or CipherSpec.",
            )

        # Validate
        errors = spec.validate()
        if errors:
            return SkillResult(
                success=False,
                skill=self.name,
                error="Cipher specification validation failed:\n" + "\n".join(f"  - {e}" for e in errors),
            )

        # Build the cipher
        try:
            if spec.cipher_type == "permutation":
                cipher = build_permutation_from_spec(spec)
            elif spec.cipher_type == "blockcipher":
                cipher = build_blockcipher_from_spec(spec)
            else:
                return SkillResult(
                    success=False,
                    skill=self.name,
                    error=f"Unsupported cipher_type: {spec.cipher_type}",
                )

            session.set_cipher(cipher)
            session.set_metadata("cipher_spec", spec.to_dict())

            return SkillResult(
                success=True,
                skill=self.name,
                data={"cipher_name": cipher.name, "type": spec.cipher_type,
                      "rounds": spec.nbr_rounds, "block_size": spec.block_size},
                summary=f"Built custom cipher: {cipher.name} ({spec.cipher_type}, "
                        f"{spec.block_size}-bit, {spec.nbr_rounds} rounds, "
                        f"{len(spec.round_structure)} layers/round)",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Failed to build cipher: {e}",
            )
