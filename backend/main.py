"""
main.py — FastAPI application entry point.

Endpoints:
  POST /query          — main RAG query
  GET  /companies      — list all companies with eligibility data
  GET  /stats          — chunk count, collection info
  POST /eval           — run full evaluation suite
  GET  /health         — health check
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
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


# ── Logging setup ─────────────────────────────────────────────────────────
logger.add(LOG_FILE, level=LOG_LEVEL, rotation="10 MB", retention="7 days")


# ── App state (singletons) ────────────────────────────────────────────────
vs        = VectorStore()
retriever: Optional[Retriever]  = None
rag_chain: Optional[RAGChain]   = None
tool_agent: Optional[ToolAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ingest PDF and build vector store."""
    global retriever, rag_chain, tool_agent

    logger.info("Starting PlacementIQ RAG system...")

    # ── Build or load vector store ────────────────────────────────────
    if not PDF_PATH.exists():
        logger.warning(
            f"PDF not found at {PDF_PATH}. "
            "Place the dataset PDF in backend/data/ and restart."
        )
    else:
        pages    = parse_pdf(PDF_PATH)
        docs     = chunk_pages(pages)
        vs.build(docs)

    retriever  = Retriever(vs)
    rag_chain  = RAGChain()
    tool_agent = ToolAgent()

    logger.success(f"PlacementIQ ready. Vector store: {vs.count} chunks.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="PlacementIQ RAG API",
    description="Placement Intelligence Retrieval-Augmented Generation System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    use_agent: bool = False   # True → use ToolAgent for computed queries


class QueryResponse(BaseModel):
    answer:           str
    query_type:       str
    sources:          list[dict]
    conflict_warning: Optional[str]
    multihop_steps:   list[str]
    is_out_of_corpus: bool
    is_conflict:      bool


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "chunks": vs.count}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if retriever is None or rag_chain is None:
        raise HTTPException(503, "RAG system not ready. Check logs.")

    classified = classify_query(req.question)

    # Computed queries → ToolAgent
    if req.use_agent or classified.get("query_type") == "computed":
        retrieval  = retriever.retrieve(req.question, classified)
        context    = "\n".join(c.text for c in retrieval.chunks)
        raw_answer = tool_agent.run(req.question, context)
        llm_out    = {
            "answer":           raw_answer,
            "query_type":       "computed",
            "sources":          [],
            "conflict_warning": None,
            "multihop_steps":   [],
        }
    else:
        retrieval = retriever.retrieve(req.question, classified)
        llm_out   = rag_chain.answer(req.question, retrieval)

    response = build_response(llm_out)
    return QueryResponse(**response.to_dict())


@app.get("/companies")
async def list_companies():
    """Return all companies with their eligibility data."""
    if retriever is None:
        raise HTTPException(503, "Not ready")

    chunks = vs.query_section("company eligibility", section="eligibility", top_k=30)
    companies = {}
    for chunk in chunks:
        m = chunk.metadata
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
        "chunk_count": vs.count,
        "model":       "claude-sonnet-4-20250514",
        "embed_model": "all-MiniLM-L6-v2",
        "vector_store": "ChromaDB",
    }


@app.post("/eval")
async def run_eval():
    if retriever is None or rag_chain is None:
        raise HTTPException(503, "Not ready")
    summary = run_evaluation(retriever, rag_chain)
    return summary


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
    )