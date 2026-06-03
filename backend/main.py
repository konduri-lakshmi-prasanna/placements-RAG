"""
main.py — FastAPI application entry point.

Endpoints:
  POST /query          — main RAG query
  GET  /companies      — list all companies with eligibility data
  GET  /stats          — chunk count, collection info
  POST /eval           — run full evaluation suite
  GET  /health         — health check

Query routing:
  web_search          → ToolAgent (web_search_tool)
  student_eligibility → ToolAgent (mysql_tool)
  computed            → ToolAgent (calculator_tool)
  out_of_corpus       → friendly fallback
  everything else     → RAGChain (PDF corpus) with hallucination checks
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from agent.prompt_router import classify_query
from agent.rag_chain import RAGChain
from agent.tool_agent import ToolAgent
from config import API_HOST, API_PORT, API_RELOAD, LOG_FILE, LOG_LEVEL, PDF_PATH
from evaluation.eval_runner import run_evaluation
from ingestion.chunker import chunk_pages
from ingestion.pdf_parser import parse_pdf
from response.response_builder import build_response
from retrieval.retriever import Retriever
from retrieval.vector_store import VectorStore


# ── Logging ───────────────────────────────────────────────────────────────
logger.add(LOG_FILE, level=LOG_LEVEL, rotation="10 MB", retention="7 days")

# ── Singletons ────────────────────────────────────────────────────────────
vs         = VectorStore()
retriever:  Optional[Retriever]  = None
rag_chain:  Optional[RAGChain]   = None
tool_agent: Optional[ToolAgent]  = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global retriever, rag_chain, tool_agent
    logger.info("Starting PlacementIQ RAG system...")

    if vs.count > 0:
        logger.success(f"Vector store already loaded: {vs.count} chunks.")
    elif PDF_PATH.exists():
        pages = parse_pdf(PDF_PATH)
        docs  = chunk_pages(pages)
        vs.build(docs)
    else:
        logger.warning("No PDF and no vector store found!")

    retriever  = Retriever(vs)
    rag_chain  = RAGChain()
    tool_agent = ToolAgent()

    logger.success(f"PlacementIQ ready. Chunks: {vs.count}")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="PlacementIQ RAG API",
    description="Placement Intelligence RAG System with Hallucination Mitigation",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question:  str
    use_agent: bool = False


class QueryResponse(BaseModel):
    answer:                str
    query_type:            str
    sources:               list[dict]
    conflict_warning:      Optional[str]
    multihop_steps:        list[str]
    is_out_of_corpus:      bool
    is_conflict:           bool
    confidence:            float         # 0.0–1.0
    lookback_ratio:        float         # 0.0–1.0
    hallucination_warning: Optional[str]


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "chunks": vs.count}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if retriever is None or rag_chain is None:
        raise HTTPException(503, "RAG system not ready. Check logs.")

    classified = classify_query(req.question)
    query_type = classified.get("query_type")

    logger.info(f"Query: '{req.question[:80]}' → type={query_type}")

    USE_TOOL_AGENT = (
        req.use_agent
        or query_type == "computed"
        or query_type == "web_search"
        or query_type == "student_eligibility"
    )

    if USE_TOOL_AGENT:
        try:
            retrieval = retriever.retrieve(req.question, classified)
            context   = "\n".join(c.text for c in retrieval.chunks)
        except Exception:
            context = ""

        raw_answer = tool_agent.run(req.question, context)
        llm_out = {
            "answer":                raw_answer,
            "query_type":            query_type,
            "sources":               [],
            "conflict_warning":      None,
            "multihop_steps":        [],
            "confidence":            1.0,   # tool answers are fetched live
            "lookback_ratio":        1.0,
            "hallucination_warning": None,
        }

    elif classified.get("is_out_of_corpus"):
        llm_out = {
            "answer": (
                "I couldn't find this information in the placement dataset. "
                "I can help you with:\n"
                "• Company eligibility criteria (CGPA, backlogs, branches)\n"
                "• Package and salary information\n"
                "• Interview rounds and preparation tips\n"
                "• CEO names, stock prices, news (just ask naturally!)\n"
                "• Student eligibility checks (share your roll number or CGPA)\n\n"
                f"Reason: {classified.get('fallback_reason', 'Query outside dataset scope.')}"
            ),
            "query_type":            "out_of_corpus",
            "sources":               [],
            "conflict_warning":      None,
            "multihop_steps":        [],
            "confidence":            0.0,
            "lookback_ratio":        0.0,
            "hallucination_warning": None,
        }

    else:
        retrieval = retriever.retrieve(req.question, classified)
        llm_out   = rag_chain.answer(req.question, retrieval)

    response = build_response(llm_out)
    return QueryResponse(**response.to_dict())


@app.get("/companies")
async def list_companies():
    if retriever is None:
        raise HTTPException(503, "Not ready")
    chunks    = vs.query_section("company eligibility", section="eligibility", top_k=30)
    companies = {}
    for chunk in chunks:
        m       = chunk.metadata
        company = m.get("company", "")
        if company and company not in companies:
            companies[company] = {
                "name":         company,
                "min_cgpa":     m.get("min_cgpa"),
                "max_backlogs": m.get("max_backlogs"),
                "package_lpa":  m.get("package_lpa"),
                "bond_years":   m.get("bond_years"),
                "tech_focus":   m.get("tech_focus"),
            }
    return {"companies": list(companies.values())}


@app.get("/stats")
async def stats():
    return {
        "chunk_count":  vs.count,
        "model":        "llama-3.3-70b-versatile",
        "embed_model":  "all-MiniLM-L6-v2",
        "vector_store": "ChromaDB",
    }


@app.post("/eval")
async def run_eval():
    if retriever is None or rag_chain is None:
        raise HTTPException(503, "Not ready")
    summary = run_evaluation(retriever, rag_chain)
    return summary


if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=API_RELOAD)