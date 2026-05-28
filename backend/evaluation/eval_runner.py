"""
eval_runner.py — Runs the full 30-query evaluation suite and scores results.

Metrics:
  - Routing accuracy    : correct query_type classification
  - OOC accuracy        : correct out-of-corpus detection
  - Answer correctness  : key-value substring match (quick heuristic)
  - Conflict detection  : correct conflict flag raised
  - Full RAGAS eval     : faithfulness, answer relevance (optional, needs OpenAI)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from loguru import logger

from agent.prompt_router import classify_query
from agent.rag_chain import RAGChain
from evaluation.eval_queries import EVAL_QUERIES
from response.response_builder import build_response
from retrieval.retriever import Retriever


def _substring_score(answer: str, expected: str) -> float:
    """
    Rough correctness check: what fraction of key tokens in expected
    appear in the model answer?
    """
    if expected == "NOT_IN_CORPUS":
        return 1.0 if "don't have" in answer.lower() or "not available" in answer.lower() else 0.0
    if expected == "SUBJECTIVE — present objective comparison only":
        return 1.0 if "google" in answer.lower() and "microsoft" in answer.lower() else 0.0

    tokens = [t.strip(".,()") for t in expected.split() if len(t) > 2]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t.lower() in answer.lower())
    return round(hits / len(tokens), 2)


def run_evaluation(
    retriever: Retriever,
    rag_chain:  RAGChain,
    output_path: Path = Path("logs/eval_results.json"),
) -> dict:
    """
    Run all 30 eval queries and return a results dict.
    """
    results   = []
    scores    = []
    routing   = []
    ooc_acc   = []

    logger.info("Starting evaluation run — 30 queries")

    for q in EVAL_QUERIES:
        qid        = q["id"]
        question   = q["question"]
        expected   = q["expected_answer"]
        exp_type   = q["expected_query_type"]
        difficulty = q["difficulty"]

        t0 = time.time()

        # Step 1: classify
        classified = classify_query(question)

        # Step 2: retrieve
        retrieval = retriever.retrieve(question, classified)

        # Step 3: generate
        llm_out  = rag_chain.answer(question, retrieval)
        response = build_response(llm_out)

        elapsed = round(time.time() - t0, 2)

        # ── Score ───────────────────────────────────────────────────────
        ans_score    = _substring_score(response.answer, expected)
        route_ok     = int(classified["query_type"] == exp_type)
        ooc_ok       = int(
            response.is_out_of_corpus == (exp_type == "out_of_corpus")
        )

        scores.append(ans_score)
        routing.append(route_ok)
        ooc_acc.append(ooc_ok)

        result_entry = {
            "id":              qid,
            "difficulty":      difficulty,
            "question":        question,
            "expected_type":   exp_type,
            "got_type":        classified["query_type"],
            "routing_ok":      bool(route_ok),
            "ooc_ok":          bool(ooc_ok),
            "answer_score":    ans_score,
            "answer_preview":  response.answer[:200],
            "conflict_raised": response.is_conflict,
            "elapsed_s":       elapsed,
        }
        results.append(result_entry)

        status = "✓" if ans_score >= 0.5 else "✗"
        logger.info(
            f"[{qid}] {status} score={ans_score:.2f} routing={'✓' if route_ok else '✗'} "
            f"({elapsed}s)"
        )

    # ── Aggregate ──────────────────────────────────────────────────────
    summary = {
        "total_queries":       len(EVAL_QUERIES),
        "avg_answer_score":    round(sum(scores)   / len(scores),   2),
        "routing_accuracy":    round(sum(routing)  / len(routing),  2),
        "ooc_accuracy":        round(sum(ooc_acc)  / len(ooc_acc),  2),
        "by_difficulty": {
            diff: round(
                sum(r["answer_score"] for r in results if r["difficulty"] == diff) /
                max(sum(1 for r in results if r["difficulty"] == diff), 1),
                2,
            )
            for diff in ["easy", "medium", "hard", "expert"]
        },
        "results": results,
    }

    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2))
    logger.success(
        f"Evaluation complete. "
        f"avg_score={summary['avg_answer_score']}, "
        f"routing={summary['routing_accuracy']}, "
        f"ooc={summary['ooc_accuracy']}"
    )
    return summary