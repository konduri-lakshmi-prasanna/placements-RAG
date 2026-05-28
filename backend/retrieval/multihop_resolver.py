"""
multihop_resolver.py — Multi-hop reasoning over placement data.

Some queries require joining data from multiple sections:
  - Eligibility (CGPA, backlogs) + Package → "highest-paying job I qualify for"
  - Tech focus + Package           → "best Python company"
  - Eligibility + Hiring + Package → "company with most analysts and package > 20 LPA"

This resolver executes structured multi-hop chains when the query
classifier identifies a multi-hop query type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from loguru import logger

from retrieval.vector_store import RetrievedChunk, VectorStore


@dataclass
class MultihopResult:
    query_type:   str
    reasoning:    list[str]            # step-by-step chain
    final_answer: str
    supporting_chunks: list[RetrievedChunk]


class MultihopResolver:
    """
    Executes structured multi-hop retrieval chains.
    Each hop queries a specific section and filters the result set.
    """

    def __init__(self, vs: VectorStore) -> None:
        self._vs = vs

    # ── Public entry point ────────────────────────────────────────────

    def resolve(self, query: str, query_type: str, params: dict) -> MultihopResult:
        """
        Dispatch to the correct multi-hop strategy based on query_type.

        query_type values (set by prompt_router):
          "eligibility_package"   — filter by CGPA + backlogs, sort by package
          "tech_package"          — filter by tech focus, sort by package
          "eligibility_analyst"   — filter by CGPA + analysts + package
          "bond_package"          — filter by bond, sort by package
          "general"               — fall back to dense retrieval
        """
        strategies = {
            "eligibility_package": self._eligibility_then_package,
            "tech_package":        self._tech_then_package,
            "eligibility_analyst": self._eligibility_analyst_package,
            "bond_package":        self._bond_then_package,
        }
        handler = strategies.get(query_type, self._general_multihop)
        return handler(query, params)

    # ── Strategy: CGPA + backlogs → highest package ───────────────────

    def _eligibility_then_package(self, query: str, params: dict) -> MultihopResult:
        cgpa     = params.get("cgpa",     0.0)
        backlogs = params.get("backlogs", 0)
        reasoning = []

        reasoning.append(
            f"Step 1: Retrieve all eligibility records from vector store."
        )
        elig_chunks = self._vs.query_section(query, section="eligibility", top_k=25)

        reasoning.append(
            f"Step 2: Filter companies where min_cgpa ≤ {cgpa} "
            f"AND max_backlogs ≥ {backlogs}."
        )
        qualified: list[RetrievedChunk] = []
        for chunk in elig_chunks:
            m = chunk.metadata
            if (m.get("min_cgpa", 99) <= cgpa and
                    m.get("max_backlogs", -1) >= backlogs):
                qualified.append(chunk)

        if not qualified:
            return MultihopResult(
                query_type="eligibility_package",
                reasoning=reasoning,
                final_answer=(
                    f"No company in this dataset accepts students with "
                    f"CGPA {cgpa} and {backlogs} backlogs."
                ),
                supporting_chunks=[],
            )

        reasoning.append(
            f"Step 3: Sort {len(qualified)} eligible companies by package."
        )
        best = max(qualified, key=lambda c: c.metadata.get("package_lpa", 0))
        company = best.metadata.get("company", "Unknown")
        package = best.metadata.get("package_lpa", 0)

        return MultihopResult(
            query_type="eligibility_package",
            reasoning=reasoning,
            final_answer=(
                f"The highest-paying company you qualify for (CGPA {cgpa}, "
                f"{backlogs} backlog(s)) is **{company}** at **{package} LPA**."
            ),
            supporting_chunks=qualified,
        )

    # ── Strategy: tech focus → highest package ───────────────────────

    def _tech_then_package(self, query: str, params: dict) -> MultihopResult:
        tech     = params.get("tech_focus", "Python")
        reasoning = []

        reasoning.append(
            f"Step 1: Retrieve all eligibility records."
        )
        elig_chunks = self._vs.query_section(query, section="eligibility", top_k=25)

        reasoning.append(
            f"Step 2: Filter companies with tech_focus = '{tech}'."
        )
        matching = [
            c for c in elig_chunks
            if tech.lower() in c.metadata.get("tech_focus", "").lower()
        ]

        if not matching:
            return MultihopResult(
                query_type="tech_package",
                reasoning=reasoning,
                final_answer=f"No company in the dataset uses {tech} as primary tech focus.",
                supporting_chunks=[],
            )

        reasoning.append("Step 3: Sort by package descending.")
        best    = max(matching, key=lambda c: c.metadata.get("package_lpa", 0))
        company = best.metadata.get("company", "Unknown")
        package = best.metadata.get("package_lpa", 0)

        return MultihopResult(
            query_type="tech_package",
            reasoning=reasoning,
            final_answer=(
                f"Among {tech}-focused companies, **{company}** offers "
                f"the highest package at **{package} LPA**."
            ),
            supporting_chunks=matching,
        )

    # ── Strategy: eligibility + analyst hiring + package ─────────────

    def _eligibility_analyst_package(self, query: str, params: dict) -> MultihopResult:
        cgpa        = params.get("cgpa",          0.0)
        backlogs    = params.get("backlogs",       0)
        min_analyst = params.get("min_analyst",    40)
        min_package = params.get("min_package",    20.0)
        reasoning   = []

        reasoning.append("Step 1: Filter by CGPA and backlogs.")
        elig_chunks = self._vs.query_section(query, section="eligibility", top_k=25)
        qualified_companies = {
            c.metadata["company"]
            for c in elig_chunks
            if (c.metadata.get("min_cgpa", 99) <= cgpa and
                c.metadata.get("max_backlogs", -1) >= backlogs and
                c.metadata.get("package_lpa", 0) >= min_package)
        }

        reasoning.append(
            f"Step 2: From {len(qualified_companies)} eligible companies, "
            f"find those with Analyst hires > {min_analyst}."
        )
        hiring_chunks = self._vs.query_section(query, section="hiring", top_k=30)
        final: list[RetrievedChunk] = []
        for chunk in hiring_chunks:
            company  = chunk.metadata.get("company", "")
            analysts = chunk.metadata.get("analyst", 0)
            if company in qualified_companies and analysts > min_analyst:
                final.append(chunk)

        reasoning.append(
            f"Step 3: Sort remaining {len(final)} by analyst hiring volume."
        )
        if not final:
            return MultihopResult(
                query_type="eligibility_analyst",
                reasoning=reasoning,
                final_answer="No company matches all three criteria.",
                supporting_chunks=[],
            )

        best    = max(final, key=lambda c: c.metadata.get("analyst", 0))
        company = best.metadata.get("company", "Unknown")

        return MultihopResult(
            query_type="eligibility_analyst",
            reasoning=reasoning,
            final_answer=(
                f"**{company}** best matches: eligible for CGPA {cgpa}, "
                f"highest analyst hiring, and package > {min_package} LPA."
            ),
            supporting_chunks=final,
        )

    # ── Strategy: bond filter → package ──────────────────────────────

    def _bond_then_package(self, query: str, params: dict) -> MultihopResult:
        min_package = params.get("min_package", 40.0)
        reasoning   = []

        reasoning.append("Step 1: Retrieve all eligibility records.")
        elig_chunks = self._vs.query_section(query, section="eligibility", top_k=25)

        reasoning.append(
            f"Step 2: Filter bond_years = 0 AND package > {min_package} LPA."
        )
        matching = [
            c for c in elig_chunks
            if (c.metadata.get("bond_years", 1) == 0 and
                c.metadata.get("package_lpa", 0) > min_package)
        ]

        if not matching:
            return MultihopResult(
                query_type="bond_package",
                reasoning=reasoning,
                final_answer=f"No bond-free companies offer more than {min_package} LPA.",
                supporting_chunks=[],
            )

        companies = [(c.metadata["company"], c.metadata["package_lpa"]) for c in matching]
        companies.sort(key=lambda x: x[1], reverse=True)
        answer_parts = ", ".join(f"{name} ({pkg} LPA)" for name, pkg in companies)

        return MultihopResult(
            query_type="bond_package",
            reasoning=reasoning,
            final_answer=f"Bond-free companies offering > {min_package} LPA: {answer_parts}.",
            supporting_chunks=matching,
        )

    # ── Fallback: general multi-document retrieval ────────────────────

    def _general_multihop(self, query: str, params: dict) -> MultihopResult:
        chunks = self._vs.query(query, top_k=10)
        return MultihopResult(
            query_type="general",
            reasoning=["Performed broad semantic retrieval across all sections."],
            final_answer="",          # LLM synthesises from chunks
            supporting_chunks=chunks,
        )