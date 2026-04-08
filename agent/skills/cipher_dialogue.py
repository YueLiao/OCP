"""Multi-turn dialogue manager for collecting cipher specifications from users.

This skill manages a stateful conversation that guides users through describing
a new cipher algorithm step by step. It produces a CipherSpec that can then be
built by CipherDefinitionSkill.

Dialogue steps:
1. Basic parameters (name, type, block size, word size, rounds)
2. S-box tables (if the cipher uses S-boxes)
3. Round structure (layer by layer)
4. Key schedule (if block cipher)
5. Review and confirm
"""

from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill
from agent.skills.cipher_spec import CipherSpec, LayerSpec


# Dialogue states
STATE_INIT = "init"
STATE_BASIC_PARAMS = "basic_params"
STATE_SBOX = "sbox"
STATE_ROUND_STRUCTURE = "round_structure"
STATE_KEY_SCHEDULE = "key_schedule"
STATE_REVIEW = "review"
STATE_COMPLETE = "complete"


DIALOGUE_PROMPTS = {
    STATE_INIT: (
        "Let's define your custom cipher. I need the following basic information:\n"
        "1. **Name** of the cipher\n"
        "2. **Type**: 'permutation' (no key) or 'blockcipher' (with key)\n"
        "3. **Block size** in bits (e.g., 64)\n"
        "4. **Word size** in bits (e.g., 32 for 2-word, 16-word structure)\n"
        "5. **Number of words** (block_size / word_size)\n"
        "6. **Number of rounds** (e.g., 16)\n\n"
        "Please describe these parameters."
    ),
    STATE_SBOX: (
        "Does your cipher use any S-boxes? If yes, please provide:\n"
        "- **Name** for each S-box\n"
        "- **Lookup table** as a list of integers\n"
        "  Example: [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]\n\n"
        "If no S-boxes, just say 'no S-boxes' or 'none'."
    ),
    STATE_ROUND_STRUCTURE: (
        "Now describe the round function. List the operations in order.\n"
        "Supported operations:\n"
        "- **rotation**: rotate word N left/right by K bits\n"
        "- **xor**: XOR word A and word B, store in word C\n"
        "- **modadd**: modular add word A and word B, store in word C\n"
        "- **sbox**: apply S-box to word groups\n"
        "- **permutation**: bit/word permutation with a given table\n"
        "- **matrix**: matrix multiplication over GF(2^n)\n"
        "- **add_round_key**: add subkey via XOR or modular addition\n\n"
        "Example: 'Rotate word 0 right by 7, then modular add words 0 and 1 into word 0, "
        "then rotate word 1 left by 2, then XOR words 0 and 1 into word 1.'"
    ),
    STATE_KEY_SCHEDULE: (
        "Since this is a block cipher, I need the key schedule:\n"
        "1. **Key size** in bits\n"
        "2. **Key word size** in bits\n"
        "3. **Number of key words**\n"
        "4. **Subkey extraction**: which key word indices form the round subkey\n"
        "5. **Key schedule round operations** (same format as round structure)\n\n"
        "Please describe the key schedule."
    ),
    STATE_REVIEW: (
        "Here's the cipher specification I've built. "
        "Please review it and confirm, or tell me what to change."
    ),
}


def format_spec_summary(spec):
    """Format a CipherSpec into a human-readable summary."""
    lines = [
        f"**{spec.name}**",
        f"  Type: {spec.cipher_type}",
        f"  Block size: {spec.block_size} bits ({spec.nbr_words} x {spec.word_bitsize}-bit words)",
        f"  Rounds: {spec.nbr_rounds}",
    ]

    if spec.sbox_tables:
        lines.append(f"  S-boxes: {', '.join(spec.sbox_tables.keys())}")

    lines.append("  Round structure:")
    for i, layer in enumerate(spec.round_structure):
        lines.append(f"    {i+1}. {_describe_layer(layer)}")

    if spec.cipher_type == "blockcipher":
        lines.append(f"  Key size: {spec.key_size} bits ({spec.key_nbr_words} x {spec.key_word_bitsize}-bit words)")
        lines.append(f"  Subkey extraction: words {spec.key_extract_indices}")
        if spec.key_schedule:
            lines.append("  Key schedule:")
            for i, layer in enumerate(spec.key_schedule):
                lines.append(f"    {i+1}. {_describe_layer(layer)}")

    return "\n".join(lines)


def _describe_layer(layer):
    """Generate a human-readable description of a layer."""
    lt = layer.layer_type
    p = layer.params

    if lt == "rotation":
        dir_str = "left" if p.get("direction") == "l" else "right"
        out = f" -> word {p['out_index']}" if "out_index" in p else ""
        return f"Rotate word {p.get('word_index')} {dir_str} by {p.get('amount')}{out}"
    elif lt == "xor":
        ins = p.get("input_indices", [])
        outs = p.get("output_indices", [])
        return f"XOR {ins} -> word {outs}"
    elif lt == "modadd":
        ins = p.get("input_indices", [])
        outs = p.get("output_indices", [])
        return f"ModAdd {ins} -> word {outs}"
    elif lt == "sbox":
        return f"S-box '{p.get('sbox_name')}' on groups {p.get('index', 'all')}"
    elif lt == "permutation":
        return f"Permutation (table length {len(p.get('table', []))})"
    elif lt == "matrix":
        return f"Matrix multiplication ({len(p.get('matrix', []))}x{len(p.get('matrix', []))})"
    elif lt == "add_round_key":
        return f"Add round key ({p.get('operator', 'xor')})"
    elif lt == "add_constant":
        return f"Add constant ({p.get('add_type', 'xor')})"
    return f"{lt}: {p}"


class CipherDialogueSkill(BaseSkill):
    """Multi-turn dialogue skill for defining custom ciphers.

    This skill manages the conversation state and produces prompts that guide
    the user (or LLM) through providing all necessary cipher parameters.

    Usage flow:
    1. Call with action="start" to begin a new dialogue
    2. Call with action="update" + step data from LLM parsing to advance
    3. Call with action="status" to check current state
    4. When complete, the CipherSpec is stored in session for CipherDefinitionSkill
    """

    @property
    def name(self) -> SkillName:
        return SkillName.CIPHER_DIALOGUE

    @property
    def description(self) -> str:
        return (
            "Multi-turn dialogue for defining custom ciphers. "
            "Guides the user through providing basic params, S-boxes, round structure, "
            "and key schedule. Produces a CipherSpec for CipherDefinitionSkill."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "required": True,
                "description": "'start' to begin, 'update' to provide data for current step, 'status' to check state",
                "enum": ["start", "update", "status"],
            },
            "data": {
                "type": "object",
                "required": False,
                "description": "Data for the current step (depends on dialogue state)",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        action = request.params.get("action", "status")
        data = request.params.get("data", {})

        state = session.get_metadata("dialogue_state", STATE_INIT)
        spec_data = session.get_metadata("dialogue_spec", {})
        spec = CipherSpec.from_dict(spec_data) if spec_data else CipherSpec()

        if action == "start":
            session.set_metadata("dialogue_state", STATE_BASIC_PARAMS)
            session.set_metadata("dialogue_spec", {})
            return SkillResult(
                success=True,
                skill=self.name,
                data={"state": STATE_BASIC_PARAMS, "prompt": DIALOGUE_PROMPTS[STATE_INIT]},
                summary=DIALOGUE_PROMPTS[STATE_INIT],
            )

        if action == "status":
            summary = format_spec_summary(spec) if spec.round_structure else "No cipher defined yet."
            return SkillResult(
                success=True,
                skill=self.name,
                data={"state": state, "spec": spec.to_dict(), "summary": summary},
                summary=f"Dialogue state: {state}\n{summary}",
            )

        # action == "update"
        if state == STATE_BASIC_PARAMS:
            return self._handle_basic_params(data, spec, session)
        elif state == STATE_SBOX:
            return self._handle_sbox(data, spec, session)
        elif state == STATE_ROUND_STRUCTURE:
            return self._handle_round_structure(data, spec, session)
        elif state == STATE_KEY_SCHEDULE:
            return self._handle_key_schedule(data, spec, session)
        elif state == STATE_REVIEW:
            return self._handle_review(data, spec, session)
        else:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Unknown dialogue state: {state}. Use action='start' to begin.",
            )

    def _save_and_advance(self, spec, session, next_state):
        session.set_metadata("dialogue_spec", spec.to_dict())
        session.set_metadata("dialogue_state", next_state)
        prompt = DIALOGUE_PROMPTS.get(next_state, "")
        if next_state == STATE_REVIEW:
            prompt = DIALOGUE_PROMPTS[STATE_REVIEW] + "\n\n" + format_spec_summary(spec)
        return SkillResult(
            success=True,
            skill=self.name,
            data={"state": next_state, "prompt": prompt, "spec": spec.to_dict()},
            summary=prompt,
        )

    def _handle_basic_params(self, data, spec, session):
        spec.name = data.get("name", spec.name)
        spec.cipher_type = data.get("cipher_type", spec.cipher_type)
        spec.block_size = data.get("block_size", spec.block_size)
        spec.word_bitsize = data.get("word_bitsize", spec.word_bitsize)
        spec.nbr_words = data.get("nbr_words", spec.nbr_words)
        spec.nbr_rounds = data.get("nbr_rounds", spec.nbr_rounds)
        spec.nbr_temp_words = data.get("nbr_temp_words", 0)
        return self._save_and_advance(spec, session, STATE_SBOX)

    def _handle_sbox(self, data, spec, session):
        sbox_tables = data.get("sbox_tables", {})
        if sbox_tables:
            spec.sbox_tables = sbox_tables
        return self._save_and_advance(spec, session, STATE_ROUND_STRUCTURE)

    def _handle_round_structure(self, data, spec, session):
        layers = data.get("layers", [])
        spec.round_structure = [LayerSpec.from_dict(l) for l in layers]

        if spec.cipher_type == "blockcipher":
            return self._save_and_advance(spec, session, STATE_KEY_SCHEDULE)
        else:
            return self._save_and_advance(spec, session, STATE_REVIEW)

    def _handle_key_schedule(self, data, spec, session):
        spec.key_size = data.get("key_size", spec.key_size)
        spec.key_word_bitsize = data.get("key_word_bitsize", spec.word_bitsize)
        spec.key_nbr_words = data.get("key_nbr_words", spec.key_nbr_words)
        spec.key_extract_indices = data.get("key_extract_indices", spec.key_extract_indices)
        key_layers = data.get("layers", [])
        if key_layers:
            spec.key_schedule = [LayerSpec.from_dict(l) for l in key_layers]
        return self._save_and_advance(spec, session, STATE_REVIEW)

    def _handle_review(self, data, spec, session):
        confirmed = data.get("confirmed", False)
        if confirmed:
            session.set_metadata("pending_cipher_spec", spec.to_dict())
            session.set_metadata("dialogue_state", STATE_COMPLETE)
            return SkillResult(
                success=True,
                skill=self.name,
                data={"state": STATE_COMPLETE, "spec": spec.to_dict()},
                summary=f"Cipher '{spec.name}' specification confirmed. "
                        f"Use cipher_definition skill to build it.",
            )
        else:
            # User wants changes - go back to the specified step
            go_back = data.get("go_back", STATE_BASIC_PARAMS)
            return self._save_and_advance(spec, session, go_back)
