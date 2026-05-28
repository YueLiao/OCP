"""Experimental file import helpers for cipher extraction.

The primary Agentic path is text-first extraction from user-provided plain text,
Markdown, LaTeX, pseudocode, or structured notes. This module remains available
as an experimental helper for importing text from files or using vision-capable
providers on images, but its output must be reviewed before building a cipher.

The legacy multi-step LLM pipeline extracts cipher descriptions from complete
academic papers:

Step 1 (Locate):   Scan the paper structure, identify sections that describe
                   the cipher algorithm (round function, S-box, key schedule, etc.)
Step 2 (Extract):  From the identified sections, extract the precise cipher
                   details in natural language
Step 3 (Formalize): Convert the natural language description into a structured
                   CipherSpec JSON

This approach is more structured than dumping an entire paper into the LLM, but
it is still less reliable than user-provided text because PDFs and images can
lose formulas, tables, and bit-index conventions.
- Papers are often 20+ pages; only 2-3 pages describe the actual algorithm
- LLMs lose focus with too much context
- Step-by-step reasoning produces more accurate structured output
"""

import os
from pathlib import Path
from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill
from agent.skills.cipher_file_reader import (
    CipherFileReadError,
    IMAGE_EXTENSIONS,
    PDF_EXTENSIONS,
    TEXT_EXTENSIONS,
    detect_file_type,
    encode_image_to_base64,
    extract_text_from_pdf,
    get_image_mime_type,
    get_pdf_page_count,
    parse_page_range,
    read_cipher_file,
)
EXPERIMENTAL_FILE_EXTRACTION_NOTE = (
    "Experimental file extraction helper. Prefer text-first extraction for "
    "accurate cipher specifications, and review the draft before building."
)


# ---------------------------------------------------------------------------
#  Multi-step prompts
#
#  Design principle: papers use diverse terminology. The prompts guide the LLM
#  to UNDERSTAND the cipher in cryptographic terms first, then map to our format.
#  We never assume the paper uses our naming conventions.
# ---------------------------------------------------------------------------

from agent.skills.cipher_extraction_prompts import (
    IMAGE_EXTRACTION_PROMPT,
    STEP1_LOCATE_PROMPT,
    STEP2_EXTRACT_PROMPT,
    STEP3_FORMALIZE_PROMPT,
)


class CipherExtractorSkill(BaseSkill):
    """Experimental file extraction helper for PDF, image, or text files."""

    @property
    def name(self):
        return SkillName.CIPHER_EXTRACTION

    @property
    def description(self):
        return (
            "Experimental helper for importing cipher descriptions from PDF papers, "
            "images, or text files. Prefer text-first extraction for accuracy. "
            "Always review the resulting draft before building."
        )

    @property
    def param_schema(self):
        return {
            "experimental": {
                "type": "bool", "required": False, "default": True,
                "description": EXPERIMENTAL_FILE_EXTRACTION_NOTE,
            },
            "file_path": {
                "type": "string", "required": True,
                "description": "Path to PDF, image, or text file for experimental import.",
            },
            "focus": {
                "type": "string", "required": False,
                "description": "Specific cipher or section to focus on.",
            },
            "pages": {
                "type": "string", "required": False,
                "description": "PDF page range (e.g., '1-5,8'). Default: all.",
            },
            "auto_build": {
                "type": "bool", "required": False, "default": False,
                "description": "Automatically build after extraction. Not recommended for experimental file extraction.",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        params = request.params
        file_path = os.path.expanduser(params.get("file_path", ""))
        focus = params.get("focus", "")
        pages = params.get("pages", "")
        auto_build = params.get("auto_build", False)

        if not file_path or not os.path.exists(file_path):
            return SkillResult(success=False, skill=self.name,
                               error=f"File not found: {file_path}")

        try:
            file_type = detect_file_type(file_path)
        except ValueError as e:
            return SkillResult(success=False, skill=self.name,
                               error=str(e))

        try:
            page_nums = parse_page_range(pages) if file_type == "pdf" else None
        except ValueError as e:
            return SkillResult(success=False, skill=self.name, error=f"Invalid page range: {e}")

        try:
            file_content = read_cipher_file(file_path, file_type, page_nums)
        except CipherFileReadError as e:
            return SkillResult(success=False, skill=self.name,
                               error=f"Failed to read file: {e}")

        # Build extraction pipeline data
        extraction_data = {
            "file_path": file_path,
            "file_type": file_type,
            "file_name": Path(file_path).name,
            "focus": focus,
            "auto_build": auto_build,
            "experimental": True,
            "experimental_note": EXPERIMENTAL_FILE_EXTRACTION_NOTE,
            "total_pages": file_content.total_pages,
        }

        if file_type == "image":
            extraction_data["image_base64"] = file_content.image_base64
            extraction_data["mime_type"] = file_content.mime_type
            extraction_data["pipeline"] = "single"  # image = single-step
        else:
            full_text = file_content.full_text or ""
            extraction_data["full_text"] = full_text
            text_len = len(full_text)
            # Short documents (< 8k chars) -> single step is fine
            # Long documents (papers) -> multi-step pipeline
            if text_len < 8000:
                extraction_data["pipeline"] = "single"
            else:
                extraction_data["pipeline"] = "multi"

        session.set_metadata("extraction_data", extraction_data)
        session.set_metadata("extraction_auto_build", auto_build)

        file_name = Path(file_path).name
        pipeline = extraction_data["pipeline"]
        info = f"Loaded experimental {file_type}: {file_name}"
        if file_content.total_pages:
            info += f" ({file_content.total_pages} pages)"
        if file_content.full_text:
            info += f", {len(file_content.full_text)} chars"
        if focus:
            info += f". Focus: {focus}"
        info += f". Pipeline: {pipeline}-step."
        info += f" {EXPERIMENTAL_FILE_EXTRACTION_NOTE}"

        return SkillResult(
            success=True, skill=self.name,
            data=extraction_data,
            summary=info,
        )
