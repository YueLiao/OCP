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
#
#  Design principle: papers use diverse terminology. The prompts guide the LLM
#  to UNDERSTAND the cipher in cryptographic terms first, then map to our format.
#  We never assume the paper uses our naming conventions.
# ---------------------------------------------------------------------------

STEP1_LOCATE_PROMPT = """\
You are a senior cryptography researcher reading an academic paper.
Your task is to find the sections that describe a cipher algorithm's SPECIFICATION.

Papers use many different terms. Look for content that describes ANY of the following
(they may appear under different names):

ALGORITHM STRUCTURE:
- "round function", "round transformation", "encryption process", "state update"
- "permutation", "internal function", "compression function"
- Block/state size (may be called "block length", "state size", "width", "n-bit")
- Number of rounds/steps/iterations

OPERATIONS (may use various names):
- Substitution: "S-box", "substitution box", "nonlinear layer", "SubBytes", "SubNibbles",
  "SubColumn", "SubCells", "gamma", "chi", "S-layer"
- Permutation: "P-layer", "bit permutation", "ShiftRows", "ShiftRow", "ShiftColumns",
  "pi", "wire crossing", "PermBits", "bit shuffle"
- Linear mixing: "MixColumns", "MDS matrix", "linear layer", "diffusion", "theta",
  "MixRow", "MixNibbles"
- Rotation: "cyclic shift", "ROT", "<<<", ">>>", "circular shift", "left/right rotation"
- Addition: "modular addition", "ADD", "mod 2^n", "boxplus"
- XOR: "exclusive-or", "bitwise addition mod 2", "oplus", "AddRoundKey"

STATE LAYOUT (critical for understanding S-box/permutation indices):
- States may be arranged as 2D arrays: "4x16 array", "4x4 matrix", "rectangular array"
- S-boxes may operate on COLUMNS (vertical) or ROWS (horizontal) of the 2D state
- Row/column rotations with different offsets per row/column

DATA TABLES:
- S-box lookup tables (may be in hex, decimal, matrix form)
- Permutation tables, wiring tables
- Round constants
- MDS/diffusion matrices

KEY SCHEDULE (for block ciphers):
- "key schedule", "key expansion", "subkey generation", "round key derivation"

Also look for: pseudocode, algorithm listings, figures showing the cipher structure.

Return JSON:
{
  "cipher_name": "the algorithm's name as used in the paper",
  "paper_terminology": {
    "state": "what the paper calls the internal state (e.g., 'state', 'block', 'register')",
    "round_function": "what the paper calls one round (e.g., 'round', 'step', 'iteration')",
    "sbox": "what the paper calls the S-box (e.g., 'S', 'Sbox', 'gamma', 'SubBytes') or null",
    "permutation": "what the paper calls the permutation layer or null",
    "linear_layer": "what the paper calls the linear mixing layer or null"
  },
  "design_type": "SPN / ARX / Feistel / GFN / stream / other",
  "relevant_sections": ["section numbers or names containing the specification"],
  "relevant_pages": [page numbers],
  "summary": "2-3 sentence description of the cipher in your own words as a cryptographer"
}

Return ONLY valid JSON.

--- PAPER CONTENT ---
"""

STEP2_EXTRACT_PROMPT = """\
You are a senior cryptography researcher. You are reading sections of a paper
that describes the cipher "{cipher_name}" (design type: {cipher_type}).

The paper uses this terminology: {terminology}

Your task: extract EVERY technical detail needed to fully implement this cipher
from scratch. Think step by step:

1. STATE STRUCTURE (very important - think carefully)
   - What is the total state/block size in bits?
   - How is the state divided? Into words? Bytes? Nibbles? Bits?
   - What is the size of each unit? How many units?
   - Example: "64-bit block divided into 16 nibbles of 4 bits" -> block=64, unit=4bit, count=16
   - Example: "128-bit state as 4 x 32-bit words" -> block=128, unit=32bit, count=4

   CRITICAL: Is the state arranged as a 2D array (matrix/rectangle)?
   - If yes: how many ROWS and how many COLUMNS?
   - How are the bits numbered? Row-major (row by row) or column-major?
   - Example: "4x16 rectangular array" with row 0 = bits 0-15, row 1 = bits 16-31, etc.
   - This affects how S-boxes and permutations index the bits!

2. ROUND FUNCTION - list EVERY operation in EXACT ORDER
   For each operation, determine:
   - What type is it? (substitution/permutation/rotation/XOR/addition/matrix/key-add)
   - What does it operate on? (which words/bytes/bits)
   - What are the parameters? (rotation amount, S-box table, permutation table, matrix)
   - Where does the result go?

   PAY SPECIAL ATTENTION to these patterns in 2D-state ciphers:
   - S-box on COLUMNS: takes one bit from each row at the same column position.
     Example: a 4-row state with S-box on column j takes bits [row0_j, row1_j, row2_j, row3_j]
   - Row rotations with DIFFERENT offsets per row:
     Example: "row 0 rotated by 0, row 1 by 1, row 2 by 12, row 3 by 13"
     This is NOT a single rotation - it's a full permutation of all bits
   Be careful: some operations may be described in mathematical notation.
   "x_i <- x_i <<< 3" means left-rotate word i by 3
   "x_0 <- x_0 + x_1 mod 2^n" means modular addition of word 0 and word 1, result in word 0
   "x_1 <- x_0 XOR x_1" means XOR word 0 and word 1, result in word 1

3. LOOKUP TABLES - copy the COMPLETE tables
   - S-box: every entry, in order from index 0. Note the format (hex/dec).
   - Permutation: the complete bit/byte mapping.
   - Round constants if any.
   If a table says [C, 5, 6, B, 9, 0, A, D, 3, E, F, 8, 4, 7, 1, 2]:
   this means S(0)=0xC, S(1)=0x5, S(2)=0x6, ..., S(15)=0x2

4. KEY SCHEDULE (if this is a block cipher / has a key)
   - Key size
   - How are round subkeys derived?
   - What operations are used?
   - Which part of the key state becomes the round subkey?

5. NUMBER OF ROUNDS
   - The default/recommended number of rounds

Return a detailed JSON:
{{
  "name": "cipher name",
  "state_size_bits": integer,
  "state_division": "how the state is divided, e.g., '2 words of 16 bits', '16 nibbles of 4 bits', '64 individual bits'",
  "unit_size_bits": integer,
  "num_units": integer,
  "state_2d_layout": {{
    "is_2d": true/false,
    "rows": integer,
    "cols": integer,
    "bit_numbering": "row-major: row 0 = bits 0..cols-1, row 1 = bits cols..2*cols-1, etc.",
    "sbox_direction": "column (vertical) or row (horizontal) or null"
  }},
  "num_rounds": integer,
  "design_type": "SPN/ARX/Feistel/other",
  "has_key": true/false,
  "round_operations": [
    {{
      "step": 1,
      "operation": "rotation/xor/modadd/sbox/permutation/matrix/key_addition",
      "description": "plain English description of exactly what happens",
      "operands": "which units are involved (by index, 0-based)",
      "parameters": "rotation amount, S-box name, etc."
    }}
  ],
  "sbox_tables": {{
    "name": {{
      "input_bits": integer,
      "output_bits": integer,
      "table": [complete lookup table as integers]
    }}
  }},
  "permutation_tables": {{
    "name": [complete permutation mapping]
  }},
  "key_info": {{
    "key_size_bits": integer,
    "key_unit_size_bits": integer,
    "key_num_units": integer,
    "subkey_extraction": "which key units form the round subkey",
    "key_round_operations": [same format as round_operations]
  }} or null,
  "round_constants": [list] or null,
  "notes": "any ambiguities or things that need clarification"
}}

Return ONLY valid JSON.

--- RELEVANT SECTIONS ---
{sections_content}
"""

STEP3_FORMALIZE_PROMPT = """\
You are converting a cipher description into the OCP analysis tool's CipherSpec format.

## Cipher description (from previous analysis):
{cipher_details}

## CRITICAL MAPPING RULES

You must decide the word_bitsize carefully. This determines how the cipher is modeled:

RULE 1 - ARX ciphers (use rotation + modular addition + XOR on words):
  -> word_bitsize = the word size used in the cipher (e.g., 16, 32, 64)
  -> nbr_words = state_size / word_bitsize
  -> Example: SPECK32 with 2 x 16-bit words -> word_bitsize=16, nbr_words=2
  -> Rotations, modadd, XOR all operate on these word-sized units

RULE 2 - SPN ciphers (use S-box + bit permutation):
  -> word_bitsize = 1 (bit-level modeling)
  -> nbr_words = state_size in bits
  -> Example: PRESENT-64 -> word_bitsize=1, nbr_words=64
  -> S-box is applied to groups of bits via the "index" parameter
  -> If the S-box is 4-bit: index=[[0,1,2,3],[4,5,6,7],...] groups every 4 bits

RULE 3 - SPN ciphers with word-level S-boxes:
  -> word_bitsize = S-box input size (e.g., 8 for AES-like byte S-boxes)
  -> nbr_words = state_size / word_bitsize
  -> Example: AES with 16 bytes -> word_bitsize=8, nbr_words=16

## Layer mapping:

Map each round operation to exactly ONE layer:

| Cipher operation | layer_type | params |
|-----------------|------------|--------|
| Cyclic rotation (<<<, >>>, ROT) | "rotation" | {{"direction": "l"/"r", "amount": N, "word_index": I}} |
| XOR of two words | "xor" | {{"input_indices": [[a,b]], "output_indices": [c]}} |
| Modular addition (mod 2^n) | "modadd" | {{"input_indices": [[a,b]], "output_indices": [c]}} |
| S-box substitution | "sbox" | {{"sbox_name": "S", "index": [[bit/word groups]]}} |
| Bit/word permutation | "permutation" | {{"table": [mapping]}} |
| Matrix multiplication | "matrix" | {{"matrix": [[M]], "indices": [[groups]], "polynomial": P}} |
| Round key XOR/addition | "add_round_key" | {{"operator": "xor" or "modadd"}} |

## input_indices and output_indices explained:
- "input_indices": [[0,1]] means the operation takes word[0] and word[1] as inputs
- "output_indices": [0] means the result is stored in word[0]
- So {{"input_indices": [[0,1]], "output_indices": [0]}} means word[0] = OP(word[0], word[1])
- Multiple operations: {{"input_indices": [[0,1],[2,3]], "output_indices": [0,2]}}

## S-box index explained (for bit-level SPN, word_bitsize=1):
The "index" parameter groups bits that feed into each S-box instance.
You MUST compute these groups based on the STATE LAYOUT:

CASE A - S-box on SEQUENTIAL bits (e.g., PRESENT):
  State is a flat array, S-box applies to consecutive bits.
  index = [[0,1,2,3], [4,5,6,7], [8,9,10,11], [12,13,14,15], ...]

CASE B - S-box on COLUMNS of a 2D state (e.g., RECTANGLE):
  State is a R x C bit matrix, numbered row-major:
    Row 0: bits 0 .. C-1
    Row 1: bits C .. 2C-1
    ...
    Row R-1: bits (R-1)*C .. R*C-1
  Column j = [j, j+C, j+2C, ..., j+(R-1)*C]
  For R=4, C=16: column 0 = [0, 16, 32, 48], column 1 = [1, 17, 33, 49], etc.
  index = [[j, j+C, j+2C, j+3C] for j in range(C)]

CASE C - S-box on ROWS or DIAGONALS:
  Compute the bit indices accordingly based on the 2D layout.

## Permutation table for row rotations (2D SPN ciphers):
When a cipher applies DIFFERENT rotation offsets to each row of a 2D state,
this is modeled as a single permutation layer with a computed table.

Example: 4x16 state (4 rows of 16 bits), left-rotate row i by offset[i]:
  offset = [0, 1, 12, 13]
  For each row r (bits r*16 to r*16+15):
    bit at position r*16 + j moves to r*16 + ((j - offset[r]) mod 16)
  Compute the full 64-entry permutation table from this.

  Concretely for the example above:
  Row 0 (offset 0): [0,1,2,...,15] -> [0,1,2,...,15]  (no change)
  Row 1 (offset 1): bit 16->31 become [17,18,...,31,16]
  Row 2 (offset 12): bit 32->47 become [44,45,46,47,32,33,...,43]
  Row 3 (offset 13): bit 48->63 become [61,62,63,48,49,...,60]
  Final table = row0 ++ row1 ++ row2 ++ row3 (concatenate all 64 positions)

## Output format:
{{
  "name": "cipher name",
  "cipher_type": "permutation" (no key) or "blockcipher" (has key),
  "block_size": total state bits,
  "word_bitsize": see rules above,
  "nbr_words": block_size / word_bitsize,
  "nbr_rounds": number of rounds,
  "round_structure": [list of layers in order],
  "sbox_tables": {{"name": [lookup table as ints]}} or {{}},
  "key_size": int or null,
  "key_word_bitsize": int or null,
  "key_nbr_words": int or null,
  "key_schedule": [layers] or null,
  "key_extract_indices": [which key word indices form subkey] or null
}}

Return ONLY the JSON, no explanation.
"""

IMAGE_EXTRACTION_PROMPT = """\
You are a senior cryptography researcher. This image describes a cryptographic
algorithm (could be a structure diagram, pseudocode, or specification table).

Analyze the image carefully:
1. Identify the cipher type (SPN, ARX, Feistel, etc.)
2. Determine state size, word size, number of rounds
3. List every operation in the round function in order
4. Note any S-box tables, permutation tables, or constants shown

Then produce a CipherSpec JSON. Key rules:
- ARX ciphers: word_bitsize = actual word size (e.g., 16, 32)
- SPN with bit permutation: word_bitsize = 1, nbr_words = block_size
- SPN with byte S-boxes: word_bitsize = 8

Layer types:
- {"layer_type": "rotation", "params": {"direction": "r", "amount": 7, "word_index": 0}}
- {"layer_type": "xor", "params": {"input_indices": [[0,1]], "output_indices": [1]}}
- {"layer_type": "modadd", "params": {"input_indices": [[0,1]], "output_indices": [0]}}
- {"layer_type": "sbox", "params": {"sbox_name": "S", "index": [[0,1,2,3],[4,5,6,7]]}}
- {"layer_type": "permutation", "params": {"table": [0,4,8,12,...]}}
- {"layer_type": "add_round_key", "params": {"operator": "xor"}}

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
