"""
prompt_router.py — Query classification and routing.

Classifies incoming queries into one of these types:
  direct_lookup       — simple table lookup (easy)
  threshold_filter    — filter with one condition (medium)
  multi_filter        — multiple conditions
  eligibility_package — CGPA + backlog → best package (multi-hop)
  tech_package        — tech focus → best package (multi-hop)
  eligibility_analyst — 3-hop: eligibility + analyst + package
  bond_package        — bond=0 + package threshold
  conflict            — conflicting data query
  temporal            — year-indexed trend query
  out_of_corpus       — graceful fallback

Also extracts numeric params (CGPA, backlogs, package threshold)
for use by the multi-hop resolver.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from loguru import logger

from config import OUT_OF_CORPUS_PATTERNS


# ── Regex helpers ─────────────────────────────────────────────────────────

_CGPA_RE   = re.compile(r"cgpa[\s:of]*([0-9]+\.?[0-9]*)", re.IGNORECASE)
_BKLOG_RE  = re.compile(r"(\d+)\s*backlog", re.IGNORECASE)
_PKG_RE    = re.compile(r"([0-9]+\.?[0-9]*)\s*lpa", re.IGNORECASE)
_YEAR_RE   = re.compile(r"\b(2021|2022|2023|2024)\b")

_COMPANY_RE = re.compile(
    r"\b(TCS|Amazon|Google|Infosys|Microsoft|Deloitte|Accenture|Flipkart|"
    r"Wipro|Cognizant|Capgemini|IBM|Adobe|Oracle|SAP|HCL|"
    r"Tech Mahindra|Qualcomm|Intel|Samsung R&D)\b",
    re.IGNORECASE,
)

_TECH_RE = re.compile(
    r"\b(Python|Java|C\+\+|Cloud|System Design|DBMS|Algorithms)\b",
    re.IGNORECASE,
)

_TEMPORAL_KEYWORDS = [
    "2021", "2022", "2023", "2024", "year", "trend", "grew",
    "increased", "decreased", "from", "since", "history", "growth",
]

_CONFLICT_KEYWORDS = [
    "conflicting", "conflict", "official", "portal",
    "discrepancy", "different", "which is correct", "verify",
    "6.4 or 7.0", "7.0 or 6.4",
]

_MULTIHOP_ELIGIBILITY_PATTERNS = [
    r"cgpa.*backlog.*highest",
    r"highest.*qualify",
    r"best.*package.*cgpa",
    r"maximum.*pay.*qualify",
    r"which.*company.*can.*apply",
]

_MULTIHOP_TECH_PATTERNS = [
    r"python.*highest.*package",
    r"java.*best.*pay",
    r"which.*python.*company.*pay",
    r"tech.*focus.*package",
]

_MULTIHOP_BOND_PATTERNS = [
    r"no bond.*40",
    r"bond.free.*40",
    r"zero bond.*package",
    r"bond.*0.*lpa",
]


# ── Main classifier ───────────────────────────────────────────────────────

def classify_query(query: str) -> dict[str, Any]:
    """
    Classify a user query and extract parameters.

    Returns
    -------
    dict with keys:
      query_type        : str
      is_out_of_corpus  : bool
      fallback_reason   : Optional[str]
      params            : dict  (cgpa, backlogs, package_threshold, company, tech_focus)
      section_hint      : Optional[str]
    """
    q = query.lower().strip()

    result: dict[str, Any] = {
        "query_type":       "general",
        "is_out_of_corpus": False,
        "fallback_reason":  None,
        "params":           {},
        "section_hint":     None,
    }

    # ── Out-of-corpus detection ────────────────────────────────────────
    for pattern in OUT_OF_CORPUS_PATTERNS:
        if pattern.lower() in q:
            result["is_out_of_corpus"] = True
            result["query_type"]       = "out_of_corpus"
            result["fallback_reason"]  = (
                f"This information is not available in the placement dataset "
                f"(matched out-of-corpus pattern: '{pattern}')."
            )
            logger.info(f"Query classified as out-of-corpus: {query[:60]}")
            return result

    # ── CGPA too low ───────────────────────────────────────────────────
    cgpa_match = _CGPA_RE.search(query)
    if cgpa_match:
        cgpa = float(cgpa_match.group(1))
        result["params"]["cgpa"] = cgpa
        if cgpa < 6.1:
            result["is_out_of_corpus"] = True
            result["query_type"]       = "out_of_corpus"
            result["fallback_reason"]  = (
                f"No company in this dataset has a CGPA cutoff ≤ {cgpa}. "
                f"The lowest cutoff is 6.1 (Microsoft)."
            )
            return result

    # ── Extract other params ───────────────────────────────────────────
    backlog_match = _BKLOG_RE.search(query)
    if backlog_match:
        result["params"]["backlogs"] = int(backlog_match.group(1))

    pkg_match = _PKG_RE.search(query)
    if pkg_match:
        result["params"]["min_package"] = float(pkg_match.group(1))

    company_match = _COMPANY_RE.search(query)
    if company_match:
        result["params"]["company"] = company_match.group(1)

    tech_match = _TECH_RE.search(query)
    if tech_match:
        result["params"]["tech_focus"] = tech_match.group(1)

    # ── Conflict queries ───────────────────────────────────────────────
    if any(kw in q for kw in _CONFLICT_KEYWORDS):
        result["query_type"]   = "conflict"
        result["section_hint"] = "conflict"
        logger.info(f"Query classified as conflict: {query[:60]}")
        return result

    # ── Temporal queries ───────────────────────────────────────────────
    if any(kw in q for kw in _TEMPORAL_KEYWORDS):
        result["query_type"]   = "temporal"
        result["section_hint"] = "trend"
        logger.info(f"Query classified as temporal: {query[:60]}")
        return result

    # ── Multi-hop: bond + package ──────────────────────────────────────
    if any(re.search(p, q) for p in _MULTIHOP_BOND_PATTERNS):
        result["query_type"] = "bond_package"
        result["params"].setdefault("min_package", 40.0)
        return result

    # ── Multi-hop: eligibility + package ──────────────────────────────
    if any(re.search(p, q) for p in _MULTIHOP_ELIGIBILITY_PATTERNS):
        result["query_type"] = "eligibility_package"
        result["params"].setdefault("cgpa",     7.0)
        result["params"].setdefault("backlogs", 0)
        return result

    # ── Multi-hop: tech focus + package ───────────────────────────────
    if any(re.search(p, q) for p in _MULTIHOP_TECH_PATTERNS):
        result["query_type"] = "tech_package"
        result["params"].setdefault("tech_focus", "Python")
        return result

    # ── Section hints from keywords ────────────────────────────────────
    if any(kw in q for kw in ["cgpa", "backlog", "bond", "package", "eligible", "qualify"]):
        result["section_hint"] = "eligibility"
        result["query_type"]   = "threshold_filter"

    elif any(kw in q for kw in ["sde", "analyst", "intern", "officer", "hires", "hiring"]):
        result["section_hint"] = "hiring"
        result["query_type"]   = "direct_lookup"

    elif any(kw in q for kw in ["round", "interview", "prepare", "tip", "preparation"]):
        result["section_hint"] = "interview"
        result["query_type"]   = "direct_lookup"

    logger.info(
        f"Query classified: type={result['query_type']}, "
        f"section={result['section_hint']}, params={result['params']}"
    )
    return result