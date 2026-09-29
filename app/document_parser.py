"""Converts uploaded files (PDF / TXT) into plain text.

Nothing in this module knows about claims or routing.
"""

from pathlib import Path

import fitz  # PyMuPDF

from app import config
from app.exceptions import (
    EmptyDocumentError,
    InvalidPdfError,
    UnsupportedFileTypeError,
)


def extract_text_from_txt(content: bytes) -> str:
    """Decode a text file (UTF-8 first, Latin-1 as a safe fallback)."""
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def extract_text_from_pdf(content: bytes) -> str:
    """Extract the text layer of a PDF. Scanned PDFs need OCR (not included)."""
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            if document.needs_pass:
                raise InvalidPdfError("The PDF is password-protected.")
            return "\n".join(page.get_text("text") for page in document)
    except InvalidPdfError:
        raise
    except Exception as exc:  # PyMuPDF raises several different errors
        raise InvalidPdfError(
            "The file is not a valid PDF or is corrupted."
        ) from exc


def parse_document(filename: str, content: bytes) -> str:
    """Return the plain text of an uploaded PDF or TXT file."""
    extension = Path(filename or "").suffix.lower()
    if extension not in config.SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension or 'unknown'}'. "
            "Please upload a .pdf or .txt file."
        )
    if not content:
        raise EmptyDocumentError("The uploaded file is empty.")

    if extension == ".pdf":
        text = extract_text_from_pdf(content)
    else:
        text = extract_text_from_txt(content)

    if not text.strip():
        raise EmptyDocumentError(
            "No readable text found in the document "
            "(scanned PDFs need OCR, which is not supported yet)."
        )
    return text
