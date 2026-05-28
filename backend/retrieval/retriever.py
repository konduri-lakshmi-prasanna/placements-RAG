"""
retriever.py — Central retrieval dispatcher.

Takes a classified query and routes to:
  - Direct section query   (easy lookup)
  - Multi-hop resolver     (complex joins)
  - Conflict retrieval     (section 6 data)
  - Fallback detector      (out-of-corpus)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from config import FINAL_TOP_K, SIMILARITY_THRESHOLD
from retrieval.conflict_detector import ConflictReport, detect_conflicts
from retrieval.multihop_resolver import MultihopResolver, MultihopResult
from retrieval.vector_store import RetrievedChunk, VectorStore


@dataclass
class RetrievalResult:
    query:            str
    query_type:       str
    chunks:           list[RetrievedChunk]
    conflict_reports: list[ConflictReport]
    multihop_result:  Optional[MultihopResult]
    is_out_of_corpus: bool
    fallback_reason:  Optional[str]


class Retriever:
    """
    Unified retrieval interface.

    Usage
    -----
        retriever = Retriever(vs)
        result = retriever.retrieve(query, classified_query)
    """

    def __init__(self, vs: VectorStore) -> None:
        self._vs       = vs
        self._multihop = MultihopResolver(vs)

    def retrieve(self, query: str, classified: dict) -> RetrievalResult:
        """
        Main retrieval function.

        Parameters
        ----------
        query      : raw user query string
        classified : output of prompt_router.classify_query()
            {
              "query_type": str,
              "is_out_of_corpus": bool,
              "fallback_reason": Optional[str],
              "params": dict,
              "section_hint": Optional[str],
            }
        """
        query_type       = classified.get("query_type", "general")
        is_ooc           = classified.get("is_out_of_corpus", False)
        fallback_reason  = classified.get("fallback_reason")
        params           = classified.get("params", {})
        section_hint     = classified.get("section_hint")

        # ── Out-of-corpus: no retrieval needed ────────────────────────
        if is_ooc:
            return RetrievalResult(
                query=query,
                query_type="out_of_corpus",
                chunks=[],
                conflict_reports=[],
                multihop_result=None,
                is_out_of_corpus=True,
                fallback_reason=fallback_reason,
            )

        # ── Multi-hop queries ─────────────────────────────────────────
        if query_type in ("eligibility_package", "tech_package",
                          "eligibility_analyst", "bond_package"):
            mh_result = self._multihop.resolve(query, query_type, params)
            # Also get supporting chunks from top-K for LLM context
            extra = self._vs.query(query, top_k=FINAL_TOP_K)
            all_chunks = mh_result.supporting_chunks + extra
            conflict_reports = detect_conflicts(all_chunks)

            return RetrievalResult(
                query=query,
                query_type=query_type,
                chunks=all_chunks[:FINAL_TOP_K],
                conflict_reports=conflict_reports,
                multihop_result=mh_result,
                is_out_of_corpus=False,
                fallback_reason=None,
            )

        # ── Conflict-specific queries ─────────────────────────────────
        if query_type == "conflict":
            company = params.get("company", "")
            chunks  = self._vs.get_conflict_records(company) if company else []
            chunks += self._vs.query(query, top_k=FINAL_TOP_K)
            chunks  = chunks[:FINAL_TOP_K]
            reports = detect_conflicts(chunks)
            return RetrievalResult(
                query=query,
                query_type="conflict",
                chunks=chunks,
                conflict_reports=reports,
                multihop_result=None,
                is_out_of_corpus=False,
                fallback_reason=None,
            )

        # ── Section-specific queries ──────────────────────────────────
        if section_hint:
            chunks = self._vs.query_section(query, section=section_hint, top_k=FINAL_TOP_K)
        else:
            chunks = self._vs.query(query, top_k=FINAL_TOP_K)

        # Low similarity → possible OOC
        if chunks and min(c.score for c in chunks) > (1.0 - SIMILARITY_THRESHOLD):
            logger.warning(
                f"Low similarity scores for query: '{query}' "
                f"(best={min(c.score for c in chunks):.3f}) — possible OOC"
            )

        conflict_reports = detect_conflicts(chunks)

        return RetrievalResult(
            query=query,
            query_type=query_type,
            chunks=chunks,
            conflict_reports=conflict_reports,
            multihop_result=None,
            is_out_of_corpus=False,
            fallback_reason=None,
        )