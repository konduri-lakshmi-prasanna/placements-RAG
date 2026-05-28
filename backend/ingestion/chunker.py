"""
chunker.py — Orchestrates all chunking strategies into a unified chunk list.

Different content types get different strategies:
  eligibility  → row-per-company (from table_extractor)
  interview    → semantic paragraph split (300 tokens)
  hiring       → full table as single chunk
  statistics   → full table as single chunk
  trend        → row-per-(company, year)
  conflict     → row-per-record WITH conflict flag
  multihop     → kept as-is (reasoning examples, not for retrieval)
  adversarial  → NOT embedded (eval-only)

Output: list of Document objects ready for ChromaDB ingestion.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from config import CHUNK_SIZES
from ingestion.deduplicator import TextChunk, deduplicate
from ingestion.pdf_parser import RawPage
from ingestion.table_extractor import (
    StructuredRecord,
    extract_conflict,
    extract_eligibility,
    extract_hiring,
    extract_statistics,
    extract_trend,
)


@dataclass
class Document:
    """Final unit ready for vector store ingestion."""
    id:       str
    text:     str
    metadata: dict[str, Any]


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ── Interview text chunker ────────────────────────────────────────────────

def _split_interview_text(text: str, company: str, max_tokens: int = 300) -> list[Document]:
    """
    Split a company's interview text into semantic paragraphs.
    Rough token estimate: 1 token ≈ 4 chars.
    """
    # Split on blank lines or round headers
    paragraphs = re.split(r"\n{2,}|(?=Round\s+\d)", text.strip())
    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 40]

    docs: list[Document] = []
    buffer = ""

    for para in paragraphs:
        if len(buffer) + len(para) < max_tokens * 4:
            buffer += "\n" + para
        else:
            if buffer.strip():
                docs.append(Document(
                    id=_make_id("interview"),
                    text=buffer.strip(),
                    metadata={"section": "interview", "company": company},
                ))
            buffer = para

    if buffer.strip():
        docs.append(Document(
            id=_make_id("interview"),
            text=buffer.strip(),
            metadata={"section": "interview", "company": company},
        ))

    return docs


# ── Company name extractor from interview text ────────────────────────────

_COMPANY_PATTERN = re.compile(
    r"■\s*(TCS|Amazon|Google|Infosys|Microsoft|Deloitte|Accenture|Flipkart|"
    r"Wipro|Cognizant|Capgemini|IBM|Adobe|Oracle|SAP|HCL|Tech Mahindra|"
    r"Qualcomm|Intel|Samsung R&D)",
    re.IGNORECASE,
)


def _extract_interview_blocks(text: str) -> list[tuple[str, str]]:
    """Return list of (company, block_text) from raw interview page text."""
    blocks: list[tuple[str, str]] = []
    matches = list(_COMPANY_PATTERN.finditer(text))

    for i, match in enumerate(matches):
        company   = match.group(1)
        start     = match.start()
        end       = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block     = text[start:end].strip()
        blocks.append((company, block))

    return blocks


# ── Main chunking pipeline ────────────────────────────────────────────────

def chunk_pages(pages: list[RawPage]) -> list[Document]:
    """
    Process all parsed pages and return a flat list of Documents.

    Stages:
    1. Table-based sections  → StructuredRecord → Document
    2. Interview text         → paragraph split → deduplicate → Document
    3. Chart captions (if any) → Document (added separately via ingest pipeline)
    """
    all_docs: list[Document] = []

    interview_chunks: list[TextChunk] = []   # collected before dedup

    for page in pages:
        section = page.section_key
        section_type = page.section_meta.get("section", "")

        # ── Skip eval-only sections ────────────────────────────────────
        if section_type in ("adversarial", "eval_queries", "chunking_guide", "meta"):
            continue

        # ── Eligibility table (Section 1) ─────────────────────────────
        if section_type == "eligibility":
            for table in page.tables:
                records = extract_eligibility(table)
                for r in records:
                    all_docs.append(Document(
                        id=_make_id("elig"),
                        text=r.nl_passage,
                        metadata=r.metadata,
                    ))

        # ── Interview experiences (Section 2) ─────────────────────────
        elif section_type == "interview":
            blocks = _extract_interview_blocks(page.text)
            for company, block in blocks:
                chunks = _split_interview_text(block, company)
                for c in chunks:
                    interview_chunks.append(
                        TextChunk(text=c.text, metadata=c.metadata)
                    )

        # ── Hiring table (Section 3) ───────────────────────────────────
        elif section_type == "hiring":
            for table in page.tables:
                records = extract_hiring(table)
                if records:
                    # Embed full table as one chunk for cross-company queries
                    full_text = "\n".join(r.nl_passage for r in records)
                    all_docs.append(Document(
                        id=_make_id("hiring_full"),
                        text=full_text,
                        metadata={"section": "hiring", "company": "ALL"},
                    ))
                    # Also per-company chunks for targeted queries
                    for r in records:
                        all_docs.append(Document(
                            id=_make_id("hiring"),
                            text=r.nl_passage,
                            metadata=r.metadata,
                        ))

        # ── Statistics table (Section 7) ──────────────────────────────
        elif section_type == "statistics":
            for table in page.tables:
                records = extract_statistics(table)
                if records:
                    full_text = "\n".join(r.nl_passage for r in records)
                    all_docs.append(Document(
                        id=_make_id("stats_full"),
                        text=full_text,
                        metadata={"section": "statistics", "company": "ALL"},
                    ))
                    for r in records:
                        all_docs.append(Document(
                            id=_make_id("stats"),
                            text=r.nl_passage,
                            metadata=r.metadata,
                        ))

        # ── Trend table (Section 5) ────────────────────────────────────
        elif section_type == "trend":
            for table in page.tables:
                records = extract_trend(table)
                for r in records:
                    all_docs.append(Document(
                        id=_make_id("trend"),
                        text=r.nl_passage,
                        metadata=r.metadata,
                    ))

        # ── Conflict table (Section 6) ─────────────────────────────────
        elif section_type == "conflict":
            for table in page.tables:
                records = extract_conflict(table)
                for r in records:
                    all_docs.append(Document(
                        id=_make_id("conflict"),
                        text=r.nl_passage,
                        metadata=r.metadata,
                    ))

        # ── Multi-hop reasoning examples (Section 4) ───────────────────
        elif section_type == "multihop":
            # These are reference answers — useful as context, not retrieval
            if page.text.strip():
                all_docs.append(Document(
                    id=_make_id("multihop"),
                    text=page.text.strip(),
                    metadata={"section": "multihop", "company": "MULTI"},
                ))

    # ── Deduplicate interview chunks ──────────────────────────────────
    deduped = deduplicate(interview_chunks)
    for chunk in deduped:
        all_docs.append(Document(
            id=_make_id("interview"),
            text=chunk.text,
            metadata=chunk.metadata,
        ))

    logger.success(
        f"Chunking complete: {len(all_docs)} total chunks "
        f"(including {len(deduped)} deduplicated interview chunks)"
    )
    return all_docs