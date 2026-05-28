"""
pdf_parser.py — PDF ingestion with section detection.

Uses pdfplumber (not PyPDF) for accurate text+table layout.
Returns a list of RawPage objects with text, tables, images, and detected section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber
from loguru import logger

from config import PDF_PATH, SECTION_META


@dataclass
class RawPage:
    """One parsed PDF page with its raw content."""
    page_num:    int
    text:        str
    tables:      list[list[list[str]]]   # list of tables, each is rows×cols
    images:      list[bytes]             # raw image bytes
    section_key: Optional[str]           # e.g. "Section 1"
    section_meta: dict                   # from config.SECTION_META


def _detect_section(text: str) -> Optional[str]:
    """Extract the section identifier from page text."""
    match = re.search(r"Section\s+(\d+)", text)
    if match:
        return f"Section {match.group(1)}"
    return None


def parse_pdf(pdf_path: Path = PDF_PATH) -> list[RawPage]:
    """
    Parse all pages of the PDF.

    Returns
    -------
    list[RawPage]
        One entry per page, in order.
    """
    pages: list[RawPage] = []
    logger.info(f"Parsing PDF: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            # ── Text ───────────────────────────────────────────────────
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""

            # ── Tables (pdfplumber detects borders/whitespace) ─────────
            raw_tables = page.extract_tables() or []
            # Clean None cells
            clean_tables = [
                [[cell or "" for cell in row] for row in table]
                for table in raw_tables
            ]

            # ── Images (for chart pages) ───────────────────────────────
            images: list[bytes] = []
            for img_obj in page.images:
                try:
                    cropped = page.crop((
                        img_obj["x0"], img_obj["top"],
                        img_obj["x1"], img_obj["bottom"]
                    ))
                    pil_img = cropped.to_image(resolution=150)
                    import io
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    images.append(buf.getvalue())
                except Exception as e:
                    logger.warning(f"Page {i}: image extraction failed — {e}")

            # ── Section detection ──────────────────────────────────────
            section_key  = _detect_section(text)
            section_meta = SECTION_META.get(section_key, {}) if section_key else {}

            pages.append(RawPage(
                page_num=i,
                text=text,
                tables=clean_tables,
                images=images,
                section_key=section_key,
                section_meta=section_meta,
            ))

            logger.debug(
                f"Page {i}: section={section_key}, "
                f"tables={len(clean_tables)}, images={len(images)}, "
                f"chars={len(text)}"
            )

    logger.success(f"Parsed {len(pages)} pages from {pdf_path.name}")
    return pages


if __name__ == "__main__":
    pages = parse_pdf()
    for p in pages:
        print(f"Page {p.page_num}: {p.section_key} | tables={len(p.tables)} | images={len(p.images)}")