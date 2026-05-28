"""
response_builder.py — Assembles the final API response.

Combines:
  - LLM answer
  - Conflict warnings
  - Multi-hop reasoning steps
  - Source citations
  - Query type label
  - Out-of-corpus / fallback indicator
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Source:
    section: str
    company: str
    score:   float
    snippet: str


@dataclass
class FinalResponse:
    answer:           str
    query_type:       str
    sources:          list[Source]
    conflict_warning: Optional[str]
    multihop_steps:   list[str]
    is_out_of_corpus: bool
    is_conflict:      bool

    def to_dict(self) -> dict:
        return {
            "answer":           self.answer,
            "query_type":       self.query_type,
            "sources":          [asdict(s) for s in self.sources],
            "conflict_warning": self.conflict_warning,
            "multihop_steps":   self.multihop_steps,
            "is_out_of_corpus": self.is_out_of_corpus,
            "is_conflict":      self.is_conflict,
        }


def build_response(llm_output: dict) -> FinalResponse:
    """
    Build a FinalResponse from the LLM output dict.

    Parameters
    ----------
    llm_output : dict returned by RAGChain.answer() or ToolAgent.run()
    """
    sources = [
        Source(
            section=s.get("section", ""),
            company=s.get("company", ""),
            score=s.get("score", 0.0),
            snippet=s.get("snippet", ""),
        )
        for s in llm_output.get("sources", [])
    ]

    return FinalResponse(
        answer=llm_output.get("answer", ""),
        query_type=llm_output.get("query_type", "general"),
        sources=sources,
        conflict_warning=llm_output.get("conflict_warning"),
        multihop_steps=llm_output.get("multihop_steps", []),
        is_out_of_corpus=llm_output.get("query_type") == "out_of_corpus",
        is_conflict=llm_output.get("conflict_warning") is not None,
    )