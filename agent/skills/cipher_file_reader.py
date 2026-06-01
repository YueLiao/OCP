"""File import helpers for the experimental cipher extraction skill."""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set


PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
TEXT_EXTENSIONS = {".txt", ".md", ".tex", ".rst"}


class CipherFileReadError(Exception):
    """Raised when an experimental file import cannot be read."""


@dataclass
class CipherFileContent:
    file_type: str
    full_text: Optional[str] = None
    image_base64: Optional[str] = None
    mime_type: Optional[str] = None
    total_pages: Optional[int] = None


def detect_file_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in TEXT_EXTENSIONS:
        return "text"
    raise ValueError(f"Unsupported file type: {ext}")


def parse_page_range(pages_str):
    """Parse a page range string like '1-5,8,10-12' into a set of page numbers."""
    if not pages_str:
        return None
    nums = set()

    def parse_page_number(value):
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"Invalid page number: {value!r}.") from exc

    for part in pages_str.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"Invalid page range segment in {pages_str!r}.")
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = parse_page_number(a), parse_page_number(b)
            if start <= 0 or end <= 0 or end < start:
                raise ValueError(f"Invalid page range segment: {part!r}.")
            nums.update(range(start, end + 1))
        else:
            page = parse_page_number(part)
            if page <= 0:
                raise ValueError(f"Invalid page number: {part!r}.")
            nums.add(page)
    return nums


def extract_text_from_pdf(file_path, page_nums: Optional[Set[int]] = None):
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
    except (OSError, RuntimeError, ValueError) as exc:
        raise CipherFileReadError(f"Failed to read PDF with PyMuPDF: {exc}") from exc

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
    except (OSError, RuntimeError, ValueError) as exc:
        raise CipherFileReadError(f"Failed to read PDF with pdfplumber: {exc}") from exc

    raise CipherFileReadError(
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
    except (OSError, RuntimeError, ValueError) as exc:
        raise CipherFileReadError(f"Failed to inspect PDF with PyMuPDF: {exc}") from exc
    try:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
    except ImportError:
        pass
    except (OSError, RuntimeError, ValueError) as exc:
        raise CipherFileReadError(f"Failed to inspect PDF with pdfplumber: {exc}") from exc
    return None


def encode_image_to_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime_type(file_path):
    ext = Path(file_path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
    }.get(ext, "image/png")


def read_cipher_file(file_path: str, file_type: str, page_nums=None) -> CipherFileContent:
    try:
        if file_type == "pdf":
            total_pages = get_pdf_page_count(file_path)
            return CipherFileContent(
                file_type=file_type,
                full_text=extract_text_from_pdf(file_path, page_nums),
                total_pages=total_pages,
            )
        if file_type == "text":
            return CipherFileContent(
                file_type=file_type,
                full_text=Path(file_path).read_text(encoding="utf-8", errors="ignore"),
            )
        if file_type == "image":
            return CipherFileContent(
                file_type=file_type,
                image_base64=encode_image_to_base64(file_path),
                mime_type=get_image_mime_type(file_path),
            )
    except (OSError, UnicodeError) as exc:
        raise CipherFileReadError(str(exc)) from exc
    raise ValueError(f"Unsupported file_type: {file_type}")
