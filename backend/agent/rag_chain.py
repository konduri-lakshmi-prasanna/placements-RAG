"""
rag_chain.py — LangChain RAG chain using Groq.

Enhancements over base version:
  1. Strict hallucination-mitigation prompt (never answer from training data)
  2. Self-consistency check — asks LLM 3 times, returns most common answer
  3. Confidence score — based on average retrieval similarity scores
  4. Lookback ratio — measures how grounded the answer is in context
  5. Evidence citation — LLM is forced to cite section + company
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from loguru import logger

from config import GROQ_API_KEY, LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE
from retrieval.conflict_detector import format_conflict_warning
from retrieval.retriever import RetrievalResult


# ── Hallucination-mitigating system prompt ────────────────────────────────

SYSTEM_PROMPT = """You are PlacementIQ, an intelligent placement advisor for SVECW students.

STRICT ANTI-HALLUCINATION RULES — FOLLOW THESE WITHOUT EXCEPTION:
1. Answer ONLY from the provided context below. NEVER use your training data.
2. If the context does not contain the answer, say EXACTLY:
   "I don't have reliable information about this in the dataset."
3. NEVER make up or guess CGPA cutoffs, package figures, or company names.
4. NEVER say a company is eligible/ineligible unless the context explicitly states it.
5. If you are uncertain, prefix your answer with "Based on available data..."
6. Always cite the source: end every answer with "Source: [Section], [Company]"
7. If conflicting data is flagged, surface BOTH values and say "Verify with official portal."
8. For multi-hop answers, show each reasoning step numbered clearly.
9. Be precise with numbers — CGPA, LPA, backlogs, bond years.
10. Keep answers concise and structured. Use bullet points for comparisons.
"""

HUMAN_TEMPLATE = """Context from placement dataset:
{context}

{conflict_warning}
{multihop_reasoning}

User Question: {question}

Instructions:
- Answer STRICTLY from the context above.
- If the answer is not in the context, say "I don't have this in the dataset."
- End with: Source: [section name], [company name if applicable]

Answer:"""


# ── Hallucination detection helpers ───────────────────────────────────────

def calculate_confidence(chunks: list) -> float:
    """
    Confidence score 0.0–1.0 based on average retrieval similarity.

    Similarity scores from ChromaDB are distances (lower = better).
    We invert and normalize to a 0–1 confidence scale.

    Score meaning:
      > 0.75  → High confidence   (answer is well-grounded)
      0.5–0.75 → Medium confidence
      < 0.5   → Low confidence    (verify manually)
    """
    if not chunks:
        return 0.0
    scores = [c.score for c in chunks if hasattr(c, "score") and c.score is not None]
    if not scores:
        return 0.5
    # ChromaDB distance: 0 = identical, 2 = opposite
    # Convert to similarity: 1 - (distance/2)
    similarities = [max(0.0, 1.0 - (s / 2.0)) for s in scores]
    avg = sum(similarities) / len(similarities)
    return round(min(1.0, max(0.0, avg)), 2)


def lookback_ratio(answer: str, context: str) -> float:
    """
    Measures how much the answer is grounded in the retrieved context.

    Method: what fraction of meaningful answer words appear in context?

    Ratio meaning:
      > 0.5  → Answer is well-grounded in context (good)
      0.3–0.5 → Partially grounded
      < 0.3  → Answer may be hallucinated (warn user)
    """
    if not context or not answer:
        return 0.0

    # Tokenize + remove stopwords
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "in", "of",
        "to", "and", "or", "for", "with", "this", "that", "it",
        "be", "as", "at", "by", "from", "on", "has", "have",
        "i", "you", "we", "they", "he", "she", "based", "above",
        "below", "please", "answer", "question", "context", "note",
    }

    def tokenize(text: str) -> set:
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        return {w for w in words if w not in stopwords}

    answer_words  = tokenize(answer)
    context_words = tokenize(context)

    if not answer_words:
        return 0.0

    overlap = answer_words & context_words
    ratio   = len(overlap) / len(answer_words)
    return round(ratio, 2)


def self_consistent_answer(chain, prompt_vars: dict, n: int = 3) -> str:
    """
    Call the LLM n times and return the most consistent answer.

    This reduces hallucination on borderline queries by picking
    the answer that appears most often across n independent calls.

    Only used for critical query types (eligibility, threshold_filter).
    For speed on simple queries, n=1 is used.
    """
    answers = []
    for i in range(n):
        try:
            response = chain.invoke(prompt_vars)
            answers.append(response.content.strip())
        except Exception as e:
            logger.warning(f"Self-consistency call {i+1} failed: {e}")

    if not answers:
        return "Unable to generate a reliable answer. Please try again."

    if len(answers) == 1:
        return answers[0]

    # Pick the most common answer
    # For short answers (CGPA/package numbers), exact match works well
    # For longer prose, use the longest answer that appears most
    counter = Counter(answers)
    most_common = counter.most_common(1)[0][0]
    logger.info(f"Self-consistency: {n} calls, {len(counter)} unique answers, using most common")
    return most_common


class RAGChain:
    """
    Builds context from retrieval results and generates answers with Groq.

    Features:
    - Hallucination-mitigating prompt
    - Self-consistency for critical queries
    - Confidence scoring
    - Lookback ratio grounding check
    """

    # Query types that benefit from self-consistency (slower but more accurate)
    _CRITICAL_TYPES = {"eligibility_package", "threshold_filter", "conflict", "bond_package"}

    def __init__(self) -> None:
        self._llm = ChatGroq(
            model=LLM_MODEL,
            api_key=GROQ_API_KEY,
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
          answer           : str
          sources          : list[dict]
          conflict_warning : Optional[str]
          multihop_steps   : list[str]
          query_type       : str
          confidence       : float   (0.0–1.0)
          lookback_ratio   : float   (0.0–1.0)
          hallucination_warning : Optional[str]
        """
        # ── Out-of-corpus: no LLM call needed ─────────────────────────
        if retrieval.is_out_of_corpus:
            return {
                "answer": (
                    "I don't have enough information in the provided documents to answer this. "
                    f"{retrieval.fallback_reason or ''}"
                ),
                "sources":               [],
                "conflict_warning":      None,
                "multihop_steps":        [],
                "query_type":            "out_of_corpus",
                "confidence":            0.0,
                "lookback_ratio":        0.0,
                "hallucination_warning": None,
            }

        # ── Build context string ───────────────────────────────────────
        context_parts = []
        for i, chunk in enumerate(retrieval.chunks, 1):
            section = chunk.metadata.get("section", "general")
            company = chunk.metadata.get("company", "")
            header  = f"[{i}] Section={section}" + (f", Company={company}" if company else "")
            context_parts.append(f"{header}\n{chunk.text}")
        context = "\n\n".join(context_parts) if context_parts else "No relevant context found."

        # ── Confidence score ───────────────────────────────────────────
        confidence = calculate_confidence(retrieval.chunks)

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
                chain_text  = "\n".join(f"  {s}" for s in mh.reasoning)
                multihop_block = (
                    f"Multi-hop reasoning chain:\n{chain_text}\n"
                    f"Pre-computed answer: {mh.final_answer}\n"
                )

        prompt_vars = {
            "context":            context,
            "conflict_warning":   conflict_warning,
            "multihop_reasoning": multihop_block,
            "question":           question,
        }

        # ── LLM call (with self-consistency for critical queries) ──────
        try:
            use_self_consistency = retrieval.query_type in self._CRITICAL_TYPES
            n_calls = 3 if use_self_consistency else 1

            if n_calls > 1:
                logger.info(f"Using self-consistency (n={n_calls}) for type={retrieval.query_type}")

            answer = self_consistent_answer(self._chain, prompt_vars, n=n_calls)

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            answer = f"An error occurred while generating the answer: {e}"

        # ── Lookback ratio — grounding check ───────────────────────────
        lb_ratio = lookback_ratio(answer, context)

        # ── Hallucination warning if grounding is low ──────────────────
        hallucination_warning = None
        if lb_ratio < 0.3 and confidence < 0.5 and retrieval.query_type != "out_of_corpus":
            hallucination_warning = (
                "⚠️ Low confidence answer — this response may not be fully grounded "
                "in the dataset. Please verify with official placement records."
            )
            logger.warning(
                f"Potential hallucination detected: "
                f"lookback_ratio={lb_ratio}, confidence={confidence}, "
                f"query='{question[:60]}'"
            )

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
            f"Answer generated: type={retrieval.query_type}, "
            f"chunks={len(retrieval.chunks)}, "
            f"confidence={confidence}, lookback={lb_ratio}, "
            f"conflicts={len(retrieval.conflict_reports)}"
        )

        return {
            "answer":                answer,
            "sources":               sources,
            "conflict_warning":      conflict_warning or None,
            "multihop_steps":        multihop_steps,
            "query_type":            retrieval.query_type,
            "confidence":            confidence,
            "lookback_ratio":        lb_ratio,
            "hallucination_warning": hallucination_warning,
        }