"""Skill for extracting cipher specifications from PDF documents or images.

Uses a multi-step LLM pipeline to intelligently extract cipher descriptions
from complete academic papers:

Step 1 (Locate):   Scan the paper structure, identify sections that describe
                   the cipher algorithm (round function, S-box, key schedule, etc.)
Step 2 (Extract):  From the identified sections, extract the precise cipher
                   details in natural language
Step 3 (Formalize): Convert the natural language description into a structured
                   CipherSpec JSON

This approach is far more robust than dumping the entire paper text to the LLM,
because:
- Papers are often 20+ pages; only 2-3 pages describe the actual algorithm
- LLMs lose focus with too much context
- Step-by-step reasoning produces more accurate structured output
"""

import base64
import os
from pathlib import Path
from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill


# Supported file extensions
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
TEXT_EXTENSIONS = {".txt", ".md", ".rst"}


# ---------------------------------------------------------------------------
#  File reading utilities
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_path, page_nums=None):
    """Extract text from a PDF file, optionally from specific pages."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        parts = []
        for i, page in enumerate(doc, 1):
            if page_nums is None or i in page_nums:
                parts.append(f"--- Page {i} ---\n{page.get_text()}")
        doc.close()
        return "\n".join(parts)
    except ImportError:
        pass

    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                if page_nums is None or i in page_nums:
                    text = page.extract_text()
                    if text:
                        parts.append(f"--- Page {i} ---\n{text}")
        return "\n".join(parts)
    except ImportError:
        pass

    raise ImportError(
        "No PDF reader available. Install one of:\n"
        "  pip install PyMuPDF     (recommended)\n"
        "  pip install pdfplumber"
    )


def get_pdf_page_count(file_path):
    """Get the total number of pages in a PDF."""
    try:
        import fitz
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count
    except ImportError:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
    except ImportError:
        pass
    return None


def parse_page_range(pages_str):
    """Parse a page range string like '1-5,8,10-12' into a set of page numbers."""
    if not pages_str:
        return None
    nums = set()
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            nums.update(range(int(a), int(b) + 1))
        else:
            nums.add(int(part))
    return nums


def encode_image_to_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime_type(file_path):
    ext = Path(file_path).suffix.lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".bmp": "image/bmp", ".tiff": "image/tiff", ".webp": "image/webp"}.get(ext, "image/png")


# ---------------------------------------------------------------------------
#  Multi-step prompts
# ---------------------------------------------------------------------------

STEP1_LOCATE_PROMPT = """\
You are a cryptography expert reading an academic paper. Your task is to identify
which parts of this paper describe a cryptographic algorithm's specification.

Look for:
1. The cipher/algorithm NAME
2. Sections describing: block size, word size, number of rounds
3. The ROUND FUNCTION: what operations are applied each round (rotations, XOR,
   modular addition, S-box substitution, permutation, matrix multiplication, etc.)
4. S-BOX TABLES: the actual lookup tables if present
5. KEY SCHEDULE: how round keys are derived (for block ciphers)
6. Any PSEUDOCODE or ALGORITHM listings
7. FIGURES/DIAGRAMS describing the cipher structure

Return a JSON object with:
{
  "cipher_name": "name of the cipher",
  "cipher_type": "ARX" / "SPN" / "Feistel" / "other",
  "relevant_sections": ["list of section numbers/names that describe the cipher"],
  "relevant_pages": [list of page numbers containing cipher description],
  "summary": "brief 2-3 sentence summary of the cipher structure"
}

Return ONLY valid JSON.

--- PAPER CONTENT ---
"""

STEP2_EXTRACT_PROMPT = """\
You are a cryptography expert. Below are the relevant sections from a paper
describing the cipher "{cipher_name}" ({cipher_type}).

Extract ALL precise technical details needed to fully implement this cipher:

1. **Basic parameters**: exact block size (bits), word size (bits), number of words,
   number of rounds
2. **Round function**: the EXACT sequence of operations in each round, including:
   - Rotation directions (left/right) and amounts
   - Which words are XORed/added together and where the result goes
   - S-box application: which bits/words, which S-box
   - Permutation tables: the exact mapping
   - Matrix multiplication details
3. **S-box tables**: the COMPLETE lookup tables, every single entry
4. **Key schedule** (if block cipher): how round keys are computed
5. **Permutation tables**: the complete bit/word permutation mappings

Be extremely precise with numbers. Copy tables EXACTLY from the paper.

Return a JSON object:
{{
  "name": "cipher name",
  "block_size": integer,
  "word_bitsize": integer,
  "nbr_words": integer,
  "nbr_rounds": integer,
  "cipher_category": "ARX" / "SPN" / "Feistel",
  "round_operations": [
    "step-by-step description of each operation in the round function, in order"
  ],
  "sbox_tables": {{"name": [complete lookup table]}} or null,
  "permutation_tables": {{"name": [complete table]}} or null,
  "key_schedule": "description of key schedule" or null,
  "key_size": integer or null,
  "key_words": integer or null,
  "additional_details": "any other relevant info"
}}

Return ONLY valid JSON.

--- RELEVANT SECTIONS ---
{sections_content}
"""

STEP3_FORMALIZE_PROMPT = """\
You are a cryptography expert. Convert the following cipher description into
the exact CipherSpec JSON format used by the OCP analysis tool.

## Input cipher description:
{cipher_details}

## Target CipherSpec format:
The JSON must have these fields:
{{
  "name": "cipher name (string)",
  "cipher_type": "permutation" or "blockcipher",
  "block_size": integer (total bits),
  "word_bitsize": integer (bits per word),
  "nbr_words": integer (number of words = block_size / word_bitsize),
  "nbr_rounds": integer,
  "round_structure": [ordered list of layer operations],
  "sbox_tables": {{"name": [lookup_table]}} or {{}},
  "key_size": integer or null,
  "key_word_bitsize": integer or null,
  "key_nbr_words": integer or null,
  "key_schedule": [ordered list of key schedule operations] or null,
  "key_extract_indices": [indices] or null
}}

## Layer format rules:
Each layer in round_structure must be ONE of:
- {{"layer_type": "rotation", "params": {{"direction": "l" or "r", "amount": N, "word_index": N}}}}
- {{"layer_type": "xor", "params": {{"input_indices": [[a,b]], "output_indices": [c]}}}}
  means: word[c] = word[a] XOR word[b]
- {{"layer_type": "modadd", "params": {{"input_indices": [[a,b]], "output_indices": [c]}}}}
  means: word[c] = (word[a] + word[b]) mod 2^n
- {{"layer_type": "sbox", "params": {{"sbox_name": "name", "index": [[0,1,2,3],[4,5,6,7],...] }}}}
  index groups consecutive word indices for each S-box application
- {{"layer_type": "permutation", "params": {{"table": [0,4,8,12,1,5,9,13,...]}}}}
  output[j] = input[table[j]]
- {{"layer_type": "matrix", "params": {{"matrix": [[...]], "indices": [[...]], "polynomial": N}}}}
- {{"layer_type": "add_round_key", "params": {{"operator": "xor" or "modadd"}}}}

## Key rules:
- For SPN ciphers with bit-level operations: set word_bitsize=1, nbr_words=block_size
- For ARX ciphers with word-level operations: set word_bitsize=word_size, nbr_words=block_size/word_size
- Words are 0-indexed: word 0 is the first word
- Each operation in the round function becomes ONE layer in round_structure
- The order of layers must match the order of operations in the round function
- If the cipher has no key (permutation only), set cipher_type="permutation"
  and omit all key_* fields

Return ONLY the CipherSpec JSON, no extra text.
"""

# For images: single-step since we can't do multi-step easily
IMAGE_EXTRACTION_PROMPT = """\
You are a cryptography expert. This image describes a cryptographic algorithm
(possibly a diagram, pseudocode, or specification table).

Extract the cipher specification and return a CipherSpec JSON:
{
  "name": "cipher name",
  "cipher_type": "permutation" or "blockcipher",
  "block_size": integer, "word_bitsize": integer, "nbr_words": integer,
  "nbr_rounds": integer,
  "round_structure": [list of layer specs],
  "sbox_tables": {"name": [table]} or {}
}

Layer types and format:
- {"layer_type": "rotation", "params": {"direction": "r", "amount": 7, "word_index": 0}}
- {"layer_type": "xor", "params": {"input_indices": [[0,1]], "output_indices": [1]}}
- {"layer_type": "modadd", "params": {"input_indices": [[0,1]], "output_indices": [0]}}
- {"layer_type": "sbox", "params": {"sbox_name": "S", "index": [[0,1,2,3],[4,5,6,7]]}}
- {"layer_type": "permutation", "params": {"table": [0,4,8,12,...]}}

Return ONLY valid JSON.
"""


class CipherExtractorSkill(BaseSkill):
    """Extract cipher specifications from PDF, image, or text files via multi-step LLM pipeline."""

    @property
    def name(self):
        return SkillName.CIPHER_EXTRACTION

    @property
    def description(self):
        return (
            "Extract cipher specifications from PDF papers, images, or text files. "
            "Uses a 3-step LLM pipeline: (1) locate cipher sections, "
            "(2) extract technical details, (3) formalize into CipherSpec."
        )

    @property
    def param_schema(self):
        return {
            "file_path": {
                "type": "string", "required": True,
                "description": "Path to PDF, image, or text file.",
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
                "description": "Automatically build cipher after extraction.",
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

        ext = Path(file_path).suffix.lower()
        if ext in PDF_EXTENSIONS:
            file_type = "pdf"
        elif ext in IMAGE_EXTENSIONS:
            file_type = "image"
        elif ext in TEXT_EXTENSIONS:
            file_type = "text"
        else:
            return SkillResult(success=False, skill=self.name,
                               error=f"Unsupported file type: {ext}")

        # Read content
        try:
            if file_type == "pdf":
                page_nums = parse_page_range(pages)
                total_pages = get_pdf_page_count(file_path)
                full_text = extract_text_from_pdf(file_path, page_nums)
            elif file_type == "text":
                total_pages = None
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    full_text = f.read()
            else:
                full_text = None  # image mode
                total_pages = None
        except Exception as e:
            return SkillResult(success=False, skill=self.name,
                               error=f"Failed to read file: {e}")

        # Build extraction pipeline data
        extraction_data = {
            "file_path": file_path,
            "file_type": file_type,
            "file_name": Path(file_path).name,
            "focus": focus,
            "auto_build": auto_build,
            "total_pages": total_pages,
        }

        if file_type == "image":
            extraction_data["image_base64"] = encode_image_to_base64(file_path)
            extraction_data["mime_type"] = get_image_mime_type(file_path)
            extraction_data["pipeline"] = "single"  # image = single-step
        else:
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
        info = f"Loaded {file_type}: {file_name}"
        if total_pages:
            info += f" ({total_pages} pages)"
        if full_text:
            info += f", {len(full_text)} chars"
        if focus:
            info += f". Focus: {focus}"
        info += f". Pipeline: {pipeline}-step."

        return SkillResult(
            success=True, skill=self.name,
            data=extraction_data,
            summary=info,
        )
