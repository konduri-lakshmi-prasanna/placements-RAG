"""
rag_chain.py — LangChain RAG chain using Claude.

Builds the context window from retrieved chunks,
injects conflict warnings, multi-hop reasoning chains,
and calls Claude for the final answer.
"""

from __future__ import annotations

from typing import Optional

from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from loguru import logger

from config import ANTHROPIC_API_KEY, LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE
from retrieval.conflict_detector import format_conflict_warning
from retrieval.retriever import RetrievalResult


# ── System prompt ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are PlacementIQ, an intelligent placement advisor for SVECW students.
You answer questions strictly based on the provided context from the placement intelligence dataset.

Rules:
1. Answer ONLY from the provided context. Do not hallucinate company data.
2. If conflicting data is flagged, surface BOTH values and recommend verification.
3. For multi-hop answers, show your reasoning steps clearly.
4. If information is not in context, say clearly: "I don't have this information in the dataset."
5. Be precise with numbers — CGPA, package (LPA), backlogs, bond years.
6. For eligibility queries, always state the exact criteria met or not met.
7. Keep answers concise and structured. Use bullet points for comparisons.
"""

HUMAN_TEMPLATE = """Context from placement database:
{context}

{conflict_warning}
{multihop_reasoning}

User Question: {question}

Answer based strictly on the context above:"""


class RAGChain:
    """
    Builds context from retrieval results and generates answers with Claude.
    """

    def __init__(self) -> None:
        self._llm = ChatAnthropic(
            model=LLM_MODEL,
            api_key=ANTHROPIC_API_KEY,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
        )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human",  HUMAN_TEMPLATE),
        ])
        self._chain = self._prompt | self._llm

    def answer(self, question: str, retrieval: RetrievalResult) -> dict:
        """
        Generate an answer from a RetrievalResult.

        Returns
        -------
        dict with keys:
          answer          : str
          sources         : list[dict]
          conflict_warning: Optional[str]
          multihop_steps  : list[str]
          query_type      : str
        """
        # ── Out-of-corpus: no LLM call needed ─────────────────────────
        if retrieval.is_out_of_corpus:
            return {
                "answer": (
                    "I don't have enough information in the provided documents to answer this. "
                    f"{retrieval.fallback_reason or ''}"
                ),
                "sources":          [],
                "conflict_warning": None,
                "multihop_steps":   [],
                "query_type":       "out_of_corpus",
            }

        # ── Build context string ───────────────────────────────────────
        context_parts = []
        for i, chunk in enumerate(retrieval.chunks, 1):
            section = chunk.metadata.get("section", "general")
            company = chunk.metadata.get("company", "")
            header  = f"[{i}] Section={section}" + (f", Company={company}" if company else "")
            context_parts.append(f"{header}\n{chunk.text}")
        context = "\n\n".join(context_parts) if context_parts else "No relevant context found."

        # ── Conflict warning ───────────────────────────────────────────
        conflict_warning = format_conflict_warning(retrieval.conflict_reports) or ""
        if conflict_warning:
            conflict_warning = f"⚠️ DATA CONFLICT WARNING:\n{conflict_warning}\n"

        # ── Multi-hop reasoning chain ──────────────────────────────────
        multihop_steps: list[str] = []
        multihop_block = ""
        if retrieval.multihop_result:
            mh = retrieval.multihop_result
            multihop_steps = mh.reasoning
            if mh.final_answer:
                # Include pre-computed answer as a hint to guide the LLM
                chain_text = "\n".join(f"  {s}" for s in mh.reasoning)
                multihop_block = (
                    f"Multi-hop reasoning chain:\n{chain_text}\n"
                    f"Pre-computed answer: {mh.final_answer}\n"
                )

        # ── LLM call ───────────────────────────────────────────────────
        try:
            response = self._chain.invoke({
                "context":           context,
                "conflict_warning":  conflict_warning,
                "multihop_reasoning": multihop_block,
                "question":          question,
            })
            answer = response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            answer = f"An error occurred while generating the answer: {e}"

        # ── Build source citations ─────────────────────────────────────
        sources = [
            {
                "section": c.metadata.get("section", ""),
                "company": c.metadata.get("company", ""),
                "score":   round(c.score, 3),
                "snippet": c.text[:120] + "..." if len(c.text) > 120 else c.text,
            }
            for c in retrieval.chunks
        ]

        logger.info(
            f"Answer generated for query_type={retrieval.query_type}, "
            f"chunks_used={len(retrieval.chunks)}, "
            f"conflicts={len(retrieval.conflict_reports)}"
        )

        return {
            "answer":           answer,
            "sources":          sources,
            "conflict_warning": conflict_warning or None,
            "multihop_steps":   multihop_steps,
            "query_type":       retrieval.query_type,
        }