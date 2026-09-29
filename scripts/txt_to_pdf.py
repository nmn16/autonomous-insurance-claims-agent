"""Convert a sample .txt FNOL into a PDF so you can demo PDF upload.

Usage:  python scripts/txt_to_pdf.py sample_documents/claim_injury.txt
"""

import sys
import textwrap
from pathlib import Path

import fitz  # PyMuPDF

LEFT, TOP, BOTTOM = 40, 50, 800
LINE_HEIGHT, WRAP_WIDTH, FONT_SIZE = 12, 90, 9


def txt_to_pdf(source: Path) -> Path:
    # The built-in PDF font has no rupee glyph, so write "Rs. " instead.
    text = source.read_text(encoding="utf-8").replace("₹", "Rs. ")
    document = fitz.open()
    page = document.new_page()
    y_position = TOP

    for line in text.splitlines():
        if not line.strip():
            y_position += LINE_HEIGHT
            continue
        for chunk in textwrap.wrap(line, WRAP_WIDTH):
            if y_position > BOTTOM:
                page = document.new_page()
                y_position = TOP
            page.insert_text((LEFT, y_position), chunk, fontsize=FONT_SIZE)
            y_position += LINE_HEIGHT

    target = source.with_suffix(".pdf")
    document.save(str(target))
    document.close()
    return target


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/txt_to_pdf.py <file.txt>")
    print(f"Created {txt_to_pdf(Path(sys.argv[1]))}")
