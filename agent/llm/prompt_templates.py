"""Prompt templates and data catalogs for LLM integration.

This module provides structured data and prompt templates that LLMProvider
implementations can use to construct effective prompts for their chosen model.
"""

import json
from typing import List

from agent.skills.cipher_instantiation import CIPHER_CATALOG


# Valid attack goals
DIFFERENTIAL_GOALS = [
    "DIFFERENTIAL_SBOXCOUNT",
    "DIFFERENTIALPATH_PROB",
    "DIFFERENTIAL_PROB",
    "TRUNCATEDDIFF_SBOXCOUNT",
]

LINEAR_GOALS = [
    "LINEAR_SBOXCOUNT",
    "LINEARPATH_CORR",
    "LINEARHULL_CORR",
    "TRUNCATEDLINEAR_SBOXCOUNT",
]

# JSON schema for LLM response format
INTENT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "needs_clarification": {
            "type": "boolean",
            "description": "True if the request is ambiguous and needs user clarification",
        },
        "clarification_prompt": {
            "type": "string",
            "description": "Question to ask user if needs_clarification is true",
        },
        "requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "enum": [
                            "cipher_instantiation",
                            "code_generation",
                            "visualization",
                            "differential_analysis",
                            "linear_analysis",
                            "cipher_definition",
                            "cipher_dialogue",
                            "cipher_extraction",
                        ],
                    },
                    "params": {"type": "object"},
                },
                "required": ["skill", "params"],
            },
        },
    },
    "required": ["needs_clarification", "requests"],
}

TEXT_CIPHER_FACTS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "cipher_facts": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "primitive_type": {"type": ["string", "null"], "enum": ["permutation", "blockcipher", None]},
                "state": {"type": "object"},
                "rounds": {"type": "object"},
                "operations": {"type": "array"},
                "tables": {"type": "object"},
                "key_schedule": {"type": "object"},
                "test_vectors": {"type": "array"},
                "ambiguities": {"type": "array"},
                "source_spans": {"type": "array"},
            },
            "required": ["name", "primitive_type", "state", "rounds", "operations"],
        }
    },
    "required": ["cipher_facts"],
}


def _format_cipher_catalog_for_prompt():
    """Format the cipher catalog into a readable string for prompts."""
    lines = []
    for name, entry in sorted(CIPHER_CATALOG.items()):
        types = list(entry["factories"].keys())
        defaults = entry.get("default_version", {})
        versions = entry.get("valid_versions", {})
        lines.append(f"  - {name}: types={types}, defaults={defaults}")
        if versions:
            for t, v in versions.items():
                lines.append(f"      {t} versions: {v}")
    return "\n".join(lines)


SYSTEM_PROMPT_TEMPLATE = """\
You are an assistant for the OCP (Open Cryptanalysis Platform) automated cryptanalysis tool.
Your task is to parse user requests about cryptographic analysis into structured skill invocations.

## Available Ciphers
{cipher_catalog}

## Available Skills
{skills}

## Attack Goals
Differential: {diff_goals}
Linear: {linear_goals}

## Solver Types
- milp (default): MILP-based solver (Gurobi)
- sat: SAT-based solver (PySAT)

## Current Session State
{session_context}

## Instructions
Parse the user's request and return a JSON object matching this schema:
{schema}

Key rules:
1. If the user mentions a known cipher but no cipher is loaded, include a cipher_instantiation request FIRST.
2. For analysis tasks, default to MILP solver and DIFFERENTIALPATH_PROB/LINEARPATH_CORR goals unless specified.
3. If the user wants both differential and linear analysis, include both as separate requests.
4. For code generation, default to Python unless specified.
5. If the request is unclear, set needs_clarification=true with a helpful question.
6. If the user describes a NEW/CUSTOM cipher not in the catalog, use cipher_dialogue with action="start" to begin collecting its specification, then cipher_definition to build it.
7. If the user provides cipher parameters during a dialogue, use cipher_dialogue with action="update" and the structured data.

## Custom Cipher Definition
When a user describes a new cipher, extract a CipherSpec:
- cipher_type: "permutation" or "blockcipher"
- block_size, word_bitsize, nbr_words, nbr_rounds
- round_structure: list of layers, each with layer_type and params:
  - rotation: {{"direction": "l"/"r", "amount": N, "word_index": N}}
  - xor: {{"input_indices": [[a,b]], "output_indices": [c]}}
  - modadd: {{"input_indices": [[a,b]], "output_indices": [c]}}
  - sbox: {{"sbox_name": "name", "index": [[0,1,2,3],...]}}
  - permutation: {{"table": [...]}}
  - add_round_key: {{"operator": "xor"/"modadd"}}
- sbox_tables: {{"name": [lookup_table]}}
- For block ciphers: key_size, key_nbr_words, key_schedule, key_extract_indices

## Experimental File Import
When a user explicitly provides a PDF, image, or text file path, use the
cipher_extraction skill only as an experimental import helper:
- cipher_extraction: {{"file_path": "/path/to/file.pdf", "focus": "optional section", "pages": "1-5", "auto_build": false}}
- Supports .pdf, .png, .jpg, .txt files.
- Prefer text-first extraction from pasted plain text, Markdown, LaTeX, or pseudocode.
- Do not set auto_build=true for PDF/image imports.

Return ONLY valid JSON, no extra text.
"""


def build_parse_prompt(
    user_message: str,
    available_skills: List[dict],
    session_context: dict,
) -> str:
    """Build the system prompt for parsing user requests."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        cipher_catalog=_format_cipher_catalog_for_prompt(),
        skills=json.dumps(available_skills, indent=2),
        diff_goals=DIFFERENTIAL_GOALS,
        linear_goals=LINEAR_GOALS,
        session_context=json.dumps(session_context, indent=2),
        schema=json.dumps(INTENT_RESPONSE_SCHEMA, indent=2),
    )


TEXT_CIPHER_FACTS_PROMPT_TEMPLATE = """\
You are extracting a cryptographic primitive specification for OCP.

Return ONLY valid JSON matching this schema:
{schema}

Rules:
1. Extract facts from the provided text. Do not invent missing values.
2. Use primitive_type "permutation" or "blockcipher" only when supported by the text.
3. Put state size facts in state: block_size, word_bitsize, nbr_words, and any layout notes.
4. Put round count facts in rounds: nbr_rounds and any naming notes.
5. Put each round operation in operations with type and params. Supported types:
   xor, and, or, not, rotation, shift, modadd, sbox, permutation, matrix,
   add_round_key, add_constant.
6. Put S-box, permutation, matrix, constants, and test vectors under tables or
   test_vectors. Preserve table order exactly.
7. Put uncertain or missing details in ambiguities instead of guessing.
8. Add source_spans when possible with line_start, line_end, and text.

Input metadata:
- source_type: {source_type}
- format_hint: {format_hint}
- language_hint: {language_hint}
- source_name: {source_name}

Cipher text:
{normalized_text}
"""


def build_cipher_facts_extraction_prompt(cipher_input) -> str:
    """Build the text-first prompt for extracting CipherFacts."""

    return TEXT_CIPHER_FACTS_PROMPT_TEMPLATE.format(
        schema=json.dumps(TEXT_CIPHER_FACTS_RESPONSE_SCHEMA, indent=2),
        source_type=cipher_input.source_type,
        format_hint=cipher_input.format_hint,
        language_hint=cipher_input.language_hint,
        source_name=cipher_input.source_name or "",
        normalized_text=cipher_input.normalized_text,
    )


RESPONSE_PROMPT_TEMPLATE = """\
You are an assistant for the OCP cryptanalysis tool. Summarize the results of the following analysis operations for the user.
Be concise and focus on the key findings (trail counts, weights, generated files, etc.).

## Results
{results}

## Session
{session_context}

Respond in a helpful, natural tone. If there were errors, explain what went wrong and suggest fixes.
"""


def build_response_prompt(
    results: List[dict],
    session_context: dict,
) -> str:
    """Build the prompt for generating user-facing responses."""
    results_str = json.dumps(
        [{"skill": r["skill"], "success": r["success"], "summary": r["summary"], "error": r.get("error")}
         for r in results],
        indent=2,
    )
    return RESPONSE_PROMPT_TEMPLATE.format(
        results=results_str,
        session_context=json.dumps(session_context, indent=2),
    )
