"""
table_extractor.py — Converts raw pdfplumber tables into structured records.

Strategy:
  - Eligibility table  → one dict per company row
  - Hiring table       → one dict per company row
  - Statistics table   → one dict per company row
  - Trend table        → one dict per (company, year) pair
  - Conflict table     → one dict per record, with conflict flag

Each record is also serialised to a natural-language passage for embedding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger


# ── Data model ────────────────────────────────────────────────────────────

@dataclass
class StructuredRecord:
    """One unit of structured data ready for chunking."""
    record_type: str              # "eligibility" | "hiring" | "trend" | "conflict" | "statistics"
    company:     str
    data:        dict[str, Any]
    metadata:    dict[str, Any]   # will be stored as ChromaDB metadata
    nl_passage:  str              # natural-language serialisation for embedding


# ── Helpers ───────────────────────────────────────────────────────────────

def _clean(val: str) -> str:
    return val.strip().replace("R&D;", "R&D").replace("\n", " ")


def _to_float(val: str, default: float = 0.0) -> float:
    try:
        return float(re.sub(r"[^\d.]", "", val))
    except (ValueError, TypeError):
        return default


def _to_int(val: str, default: int = 0) -> int:
    try:
        return int(re.sub(r"[^\d]", "", val))
    except (ValueError, TypeError):
        return default


# ── Eligibility table ─────────────────────────────────────────────────────

ELIGIBILITY_HEADERS = [
    "company", "min_cgpa", "max_backlogs", "package_lpa", "bond_years",
    "key_topics", "tech_focus"
]


def extract_eligibility(table: list[list[str]]) -> list[StructuredRecord]:
    """
    Section 1 table: 20 rows (header + 19 companies).
    Returns one StructuredRecord per company.
    """
    records: list[StructuredRecord] = []

    for row in table:
        if len(row) < 6:
            continue
        company = _clean(row[0])
        if not company or company.lower() in ("company", ""):
            continue

        data = {
            "company":      company,
            "min_cgpa":     _to_float(row[1]),
            "max_backlogs": _to_int(row[2]),
            "package_lpa":  _to_float(row[3]),
            "bond_years":   _to_int(row[4]),
            "key_topics":   _clean(row[5]) if len(row) > 5 else "",
            "tech_focus":   _clean(row[6]) if len(row) > 6 else "",
        }

        nl = (
            f"{company} requires a minimum CGPA of {data['min_cgpa']} "
            f"and allows up to {data['max_backlogs']} backlogs. "
            f"The package offered is {data['package_lpa']} LPA "
            f"with a bond period of {data['bond_years']} year(s). "
            f"Key interview topics are {data['key_topics']}. "
            f"Technical focus: {data['tech_focus']}."
        )

        records.append(StructuredRecord(
            record_type="eligibility",
            company=company,
            data=data,
            metadata={
                "section":       "eligibility",
                "company":       company,
                "min_cgpa":      data["min_cgpa"],
                "max_backlogs":  data["max_backlogs"],
                "package_lpa":   data["package_lpa"],
                "bond_years":    data["bond_years"],
                "tech_focus":    data["tech_focus"],
                "source":        "official",
            },
            nl_passage=nl,
        ))

    logger.info(f"Eligibility: extracted {len(records)} company records")
    return records


# ── Hiring distribution table ─────────────────────────────────────────────

def extract_hiring(table: list[list[str]]) -> list[StructuredRecord]:
    """
    Section 3 table: company × {SDE, Analyst, Officer, Intern, Total}.
    Returns one StructuredRecord per company.
    """
    records: list[StructuredRecord] = []

    for row in table:
        if len(row) < 5:
            continue
        company = _clean(row[0])
        if not company or company.lower() in ("company", ""):
            continue

        data = {
            "company": company,
            "sde":      _to_int(row[1]),
            "analyst":  _to_int(row[2]),
            "officer":  _to_int(row[3]),
            "intern":   _to_int(row[4]),
            "total":    _to_int(row[5]) if len(row) > 5 else 0,
        }

        nl = (
            f"{company} hiring distribution: "
            f"SDE={data['sde']}, Analyst={data['analyst']}, "
            f"Officer={data['officer']}, Intern={data['intern']}, "
            f"Total={data['total']}."
        )

        records.append(StructuredRecord(
            record_type="hiring",
            company=company,
            data=data,
            metadata={"section": "hiring", "company": company},
            nl_passage=nl,
        ))

    logger.info(f"Hiring: extracted {len(records)} company records")
    return records


# ── Statistics table ──────────────────────────────────────────────────────

def extract_statistics(table: list[list[str]]) -> list[StructuredRecord]:
    records: list[StructuredRecord] = []

    for row in table:
        if len(row) < 6:
            continue
        company = _clean(row[0])
        if not company or company.lower() in ("company", ""):
            continue

        bond_free = "yes" in _clean(row[6]).lower() if len(row) > 6 else False

        data = {
            "company":          company,
            "avg_package":      _to_float(row[1]),
            "max_offers":       _to_int(row[2]),
            "min_offers":       _to_int(row[3]),
            "avg_cgpa_cutoff":  _to_float(row[4]),
            "bond_free":        bond_free,
        }

        nl = (
            f"{company} overall stats: avg package {data['avg_package']} LPA, "
            f"max offers {data['max_offers']}, min offers {data['min_offers']}, "
            f"average CGPA cutoff {data['avg_cgpa_cutoff']}, "
            f"bond-free: {'yes' if bond_free else 'no'}."
        )

        records.append(StructuredRecord(
            record_type="statistics",
            company=company,
            data=data,
            metadata={"section": "statistics", "company": company, "bond_free": bond_free},
            nl_passage=nl,
        ))

    logger.info(f"Statistics: extracted {len(records)} records")
    return records


# ── Trend table ───────────────────────────────────────────────────────────

TREND_YEARS = [2021, 2022, 2023, 2024]


def extract_trend(table: list[list[str]]) -> list[StructuredRecord]:
    """
    Section 5 table: company × {2021, 2022, 2023, 2024, trend}.
    Returns one record per (company, year).
    """
    records: list[StructuredRecord] = []

    for row in table:
        if len(row) < 5:
            continue
        company = _clean(row[0])
        if not company or "company" in company.lower():
            continue

        for idx, year in enumerate(TREND_YEARS, start=1):
            if idx >= len(row):
                break
            pkg = _to_float(row[idx])
            if pkg == 0.0:
                continue

            nl = (
                f"{company} offered a package of {pkg} LPA in {year}."
            )
            records.append(StructuredRecord(
                record_type="trend",
                company=company,
                data={"company": company, "year": year, "package_lpa": pkg},
                metadata={
                    "section": "trend",
                    "company": company,
                    "year":    str(year),
                    "package_lpa": pkg,
                },
                nl_passage=nl,
            ))

    logger.info(f"Trend: extracted {len(records)} (company, year) records")
    return records


# ── Conflict table ────────────────────────────────────────────────────────

def extract_conflict(table: list[list[str]]) -> list[StructuredRecord]:
    """
    Section 6 conflict table.
    Returns two records per company (official + portal), both flagged.
    """
    records: list[StructuredRecord] = []

    for row in table:
        if len(row) < 5:
            continue
        company = _clean(row[0])
        if not company or "company" in company.lower():
            continue

        cgpa_official = _to_float(row[1])
        cgpa_portal   = _to_float(row[2])
        pkg_official  = _to_float(row[3])
        pkg_portal    = _to_float(row[4])

        for source, cgpa, pkg in [
            ("official", cgpa_official, pkg_official),
            ("portal",   cgpa_portal,   pkg_portal),
        ]:
            nl = (
                f"[{source.upper()}] {company}: CGPA cutoff = {cgpa}, "
                f"package = {pkg} LPA. "
                f"NOTE: conflicting data exists between official and portal sources."
            )
            records.append(StructuredRecord(
                record_type="conflict",
                company=company,
                data={
                    "company": company, "source": source,
                    "cgpa": cgpa, "package_lpa": pkg,
                },
                metadata={
                    "section":   "conflict",
                    "company":   company,
                    "source":    source,
                    "conflict":  True,
                    "cgpa":      cgpa,
                    "package_lpa": pkg,
                },
                nl_passage=nl,
            ))

    logger.info(f"Conflict: extracted {len(records)} conflicting records")
    return records