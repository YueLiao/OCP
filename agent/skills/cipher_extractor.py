"""Skill for extracting cipher specifications from PDF documents or images.

Cryptographic papers typically describe new cipher algorithms in PDF format.
This skill reads the document, uses the LLM to extract the cipher structure,
and produces a CipherSpec that can be built by CipherDefinitionSkill.

Supports:
- PDF files (.pdf): extracts text via PyMuPDF (fitz) or pdfplumber
- Images (.png, .jpg, .jpeg, .bmp, .tiff): uses LLM vision (base64 encoding)
- Plain text files (.txt): reads directly

Usage flow:
1. User provides a file path
2. Skill extracts text/image content
3. Content is sent to LLM with a specialized prompt
4. LLM returns a structured CipherSpec JSON
5. CipherSpec is stored in session for CipherDefinitionSkill to build
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill
from agent.skills.cipher_spec import CipherSpec


# Supported file extensions
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
TEXT_EXTENSIONS = {".txt", ".md", ".rst"}


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file.

    Tries PyMuPDF (fitz) first, then pdfplumber as fallback.
    """
    # Try PyMuPDF first (faster, better formatting)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except ImportError:
        pass

    # Try pdfplumber as fallback
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except ImportError:
        pass

    raise ImportError(
        "No PDF reader available. Install one of:\n"
        "  pip install PyMuPDF     (recommended)\n"
        "  pip install pdfplumber"
    )


def extract_text_from_file(file_path: str) -> str:
    """Extract text from a plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def encode_image_to_base64(file_path: str) -> str:
    """Read an image file and return its base64-encoded content."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime_type(file_path: str) -> str:
    """Get MIME type for an image file."""
    ext = Path(file_path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "image/png")


_CIPHER_EXTRACTION_SCHEMA = """
## Required JSON fields:
{
  "name": "cipher name",
  "cipher_type": "permutation" or "blockcipher",
  "block_size": integer (total bits),
  "word_bitsize": integer (bits per word),
  "nbr_words": integer (number of words),
  "nbr_rounds": integer,
  "round_structure": [
    // List of layers applied each round, in order. Each layer is:
    {"layer_type": "rotation", "params": {"direction": "l"/"r", "amount": N, "word_index": N}},
    {"layer_type": "xor", "params": {"input_indices": [[a,b]], "output_indices": [c]}},
    {"layer_type": "modadd", "params": {"input_indices": [[a,b]], "output_indices": [c]}},
    {"layer_type": "sbox", "params": {"sbox_name": "name", "index": [[0,1,2,3],...]}},
    {"layer_type": "permutation", "params": {"table": [0,4,8,12,...]}},
    {"layer_type": "matrix", "params": {"matrix": [[...]], "indices": [[...]], "polynomial": N}},
    {"layer_type": "add_round_key", "params": {"operator": "xor"/"modadd"}}
  ],
  "sbox_tables": {"sbox_name": [0,1,2,...,15]},  // if S-boxes are used

  // For block ciphers only:
  "key_size": integer,
  "key_word_bitsize": integer,
  "key_nbr_words": integer,
  "key_schedule": [...],  // same layer format as round_structure
  "key_extract_indices": [0, 1, ...]  // which key words form the round subkey
}

## Important notes:
- Identify the cipher type: ARX (uses rotation, modadd, xor), SPN (uses sbox, permutation), Feistel, etc.
- For word_bitsize=1, the cipher operates at bit level (like PRESENT with 64 1-bit words)
- For word_bitsize>1, the cipher operates at word level (like SPECK with 2 16-bit words)
- Extract S-box tables exactly as specified in the document
- Extract permutation tables exactly as specified
- For rotation operations, identify direction (left/right) and amount
- For XOR/modadd, identify which words are inputs and which is the output

Return ONLY valid JSON, no extra text.
"""


def build_extraction_prompt(content, focus=None):
    """Build the cipher extraction prompt with document content."""
    header = (
        "You are a cryptography expert. Analyze the following document content "
        "which describes a cryptographic algorithm.\n"
        "Extract the cipher specification and return it as a JSON object matching the CipherSpec format.\n"
    )
    if focus:
        header += f"The user is specifically interested in: {focus}\n"
    return header + _CIPHER_EXTRACTION_SCHEMA + f"\n## Document content:\n{content}"

# Vision prompt for image-based extraction
CIPHER_VISION_PROMPT = """\
You are a cryptography expert. This image describes a cryptographic algorithm (possibly a diagram, pseudocode, or specification table).
Extract the cipher specification from the image and return it as a JSON object matching the CipherSpec format.

## Required JSON format:
{
  "name": "cipher name",
  "cipher_type": "permutation" or "blockcipher",
  "block_size": integer,
  "word_bitsize": integer,
  "nbr_words": integer,
  "nbr_rounds": integer,
  "round_structure": [list of layer specs],
  "sbox_tables": {"name": [table]} // if applicable
}

Layer types: rotation, xor, modadd, sbox, permutation, matrix, add_round_key.
See the round_structure format examples:
- {"layer_type": "rotation", "params": {"direction": "r", "amount": 7, "word_index": 0}}
- {"layer_type": "xor", "params": {"input_indices": [[0,1]], "output_indices": [1]}}
- {"layer_type": "modadd", "params": {"input_indices": [[0,1]], "output_indices": [0]}}
- {"layer_type": "sbox", "params": {"sbox_name": "S", "index": [[0,1,2,3],[4,5,6,7]]}}

Return ONLY valid JSON.
"""


class CipherExtractorSkill(BaseSkill):
    """Extract cipher specifications from PDF documents or images using LLM."""

    @property
    def name(self) -> SkillName:
        return SkillName.CIPHER_EXTRACTION

    @property
    def description(self) -> str:
        return (
            "Extract cipher algorithm specifications from PDF documents, images, or text files. "
            "Uses LLM to parse the document and produce a structured CipherSpec. "
            "Supported formats: PDF, PNG, JPG, TXT."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "required": True,
                "description": "Path to the PDF, image, or text file describing the cipher.",
            },
            "focus": {
                "type": "string",
                "required": False,
                "description": "Optional: specific cipher or section to focus on (e.g., 'the SPECK cipher', 'Section 3.2').",
            },
            "pages": {
                "type": "string",
                "required": False,
                "description": "For PDFs: page range to extract (e.g., '1-5', '3,7,8'). Default: all pages.",
            },
            "auto_build": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "If True, automatically build the cipher after extraction.",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        params = request.params
        file_path = params.get("file_path", "")
        focus = params.get("focus", "")
        pages = params.get("pages", "")
        auto_build = params.get("auto_build", False)

        if not file_path:
            return SkillResult(
                success=False,
                skill=self.name,
                error="No file_path provided.",
            )

        file_path = os.path.expanduser(file_path)
        if not os.path.exists(file_path):
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"File not found: {file_path}",
            )

        ext = Path(file_path).suffix.lower()
        file_type = None
        if ext in PDF_EXTENSIONS:
            file_type = "pdf"
        elif ext in IMAGE_EXTENSIONS:
            file_type = "image"
        elif ext in TEXT_EXTENSIONS:
            file_type = "text"
        else:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Unsupported file type: {ext}. Supported: PDF, PNG, JPG, TXT.",
            )

        # Extract content
        try:
            if file_type == "pdf":
                content = extract_text_from_pdf(file_path)
                if pages:
                    content = self._filter_pages(file_path, pages)
            elif file_type == "text":
                content = extract_text_from_file(file_path)
            elif file_type == "image":
                content = None  # Will use vision API
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Failed to read file: {e}",
            )

        # Store extraction data in session for LLM to process
        extraction_data = {
            "file_path": file_path,
            "file_type": file_type,
            "focus": focus,
        }

        if file_type == "image":
            extraction_data["image_base64"] = encode_image_to_base64(file_path)
            extraction_data["mime_type"] = get_image_mime_type(file_path)
            extraction_data["prompt"] = CIPHER_VISION_PROMPT
        else:
            # Truncate if too long (keep first ~30k chars for LLM context)
            if len(content) > 30000:
                content = content[:30000] + "\n\n[... content truncated ...]"
            extraction_data["content"] = content
            extraction_data["prompt"] = build_extraction_prompt(content, focus=focus)

        session.set_metadata("extraction_data", extraction_data)
        session.set_metadata("extraction_auto_build", auto_build)

        file_name = Path(file_path).name
        content_preview = ""
        if file_type != "image" and content:
            preview_lines = content[:500].strip()
            content_preview = f"\nContent preview:\n{preview_lines}..."

        return SkillResult(
            success=True,
            skill=self.name,
            data=extraction_data,
            summary=(
                f"Loaded {file_type} file: {file_name}. "
                f"Content ready for LLM extraction. "
                f"{'Focus: ' + focus + '. ' if focus else ''}"
                f"{'Auto-build enabled.' if auto_build else 'Use cipher_definition to build after extraction.'}"
                f"{content_preview}"
            ),
        )

    def _filter_pages(self, file_path, pages_str):
        """Extract text from specific pages of a PDF."""
        page_nums = set()
        for part in pages_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                page_nums.update(range(int(start), int(end) + 1))
            else:
                page_nums.add(int(part))

        try:
            import fitz
            doc = fitz.open(file_path)
            text_parts = []
            for i, page in enumerate(doc, 1):
                if i in page_nums:
                    text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts)
        except ImportError:
            pass

        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    if i in page_nums:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
            return "\n".join(text_parts)
        except ImportError:
            pass

        raise ImportError("No PDF reader available.")
