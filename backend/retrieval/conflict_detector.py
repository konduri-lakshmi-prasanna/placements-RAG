"""
conflict_detector.py — Detect and surface conflicting data.

When the retriever finds both an 'official' and 'portal' record for the
same company + field, the response builder must warn the user rather
than silently returning one value (which would be hallucination).

This module inspects retrieved chunks and returns a ConflictReport
if conflicts are detected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from retrieval.vector_store import RetrievedChunk


@dataclass
class ConflictField:
    field_name:      str
    official_value:  str
    portal_value:    str


@dataclass
class ConflictReport:
    company:          str
    conflicting_fields: list[ConflictField]
    warning_message:  str

    @property
    def has_conflict(self) -> bool:
        return len(self.conflicting_fields) > 0


def detect_conflicts(chunks: list[RetrievedChunk]) -> list[ConflictReport]:
    """
    Scan a list of retrieved chunks for conflicting official/portal records.

    Algorithm
    ---------
    1. Group chunks by company where metadata.conflict == True.
    2. For each company, compare official vs portal values.
    3. Return a ConflictReport for each company with discrepancies.
    """
    # Group conflict chunks by company
    by_company: dict[str, dict[str, dict]] = {}

    for chunk in chunks:
        meta = chunk.metadata
        if not meta.get("conflict"):
            continue

        company = meta.get("company", "")
        source  = meta.get("source", "")
        if not company or not source:
            continue

        if company not in by_company:
            by_company[company] = {}
        by_company[company][source] = meta

    reports: list[ConflictReport] = []

    for company, sources in by_company.items():
        official = sources.get("official", {})
        portal   = sources.get("portal",   {})

        if not official or not portal:
            continue

        conflicts: list[ConflictField] = []

        # Check CGPA
        off_cgpa = official.get("cgpa")
        por_cgpa = portal.get("cgpa")
        if off_cgpa and por_cgpa and off_cgpa != por_cgpa:
            conflicts.append(ConflictField(
                field_name="CGPA cutoff",
                official_value=str(off_cgpa),
                portal_value=str(por_cgpa),
            ))

        # Check package
        off_pkg = official.get("package_lpa")
        por_pkg = portal.get("package_lpa")
        if off_pkg and por_pkg and off_pkg != por_pkg:
            conflicts.append(ConflictField(
                field_name="Package (LPA)",
                official_value=str(off_pkg),
                portal_value=str(por_pkg),
            ))

        if conflicts:
            field_desc = ", ".join(
                f"{cf.field_name}: official={cf.official_value} vs portal={cf.portal_value}"
                for cf in conflicts
            )
            warning = (
                f"⚠️ Conflicting data detected for {company}. "
                f"{field_desc}. "
                f"Please verify with the official placement cell before applying."
            )
            reports.append(ConflictReport(
                company=company,
                conflicting_fields=conflicts,
                warning_message=warning,
            ))
            logger.warning(f"Conflict detected: {company} — {field_desc}")

    return reports


def format_conflict_warning(reports: list[ConflictReport]) -> Optional[str]:
    """Return a formatted warning string if any conflicts exist."""
    if not reports:
        return None
    parts = [r.warning_message for r in reports]
    return "\n".join(parts)