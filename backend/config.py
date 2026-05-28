"""
config.py — Central configuration for Placement Intelligence RAG
All tuneable parameters live here. No magic strings in other modules.
"""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
DATA_DIR        = BASE_DIR / "data"
PDF_PATH        = DATA_DIR / "Placement_RAG_Dataset_Enhanced.pdf"
CHROMA_DIR      = BASE_DIR / "chroma_db"
LOGS_DIR        = BASE_DIR / "logs"

for d in [DATA_DIR, CHROMA_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── LLM ───────────────────────────────────────────────────────────────────
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
LLM_MODEL           = "llama-3.3-70b-versatile"   # Groq model
LLM_MAX_TOKENS      = 1024
LLM_TEMPERATURE     = 0.0          # deterministic for RAG

# ── Vision model (for chart captioning) ───────────────────────────────────
VISION_MODEL        = "meta-llama/llama-4-scout-17b-16e-instruct"  # Groq vision model

# ── Embeddings ────────────────────────────────────────────────────────────
EMBED_MODEL         = "all-MiniLM-L6-v2"   # fast, 384-dim, good for tables
EMBED_BATCH_SIZE    = 64

# ── ChromaDB ──────────────────────────────────────────────────────────────
CHROMA_COLLECTION   = "placement_rag"

# ── Chunking ──────────────────────────────────────────────────────────────
# Different content types have different ideal chunk sizes (tokens)
CHUNK_SIZES = {
    "eligibility":  "row_per_company",   # 1 row = 1 chunk
    "interview":    300,                  # semantic paragraph split
    "hiring":       "full_table",         # whole hiring table at once
    "statistics":   "full_table",
    "trend":        "row_per_company",
    "conflict":     "row_per_record",     # keep both records separately
}

# ── Retrieval ─────────────────────────────────────────────────────────────
RETRIEVAL_TOP_K     = 8             # candidates before re-ranking
FINAL_TOP_K         = 5             # chunks sent to LLM
SIMILARITY_THRESHOLD= 0.35          # below = likely out-of-corpus

# ── Deduplication ─────────────────────────────────────────────────────────
DEDUP_SIMILARITY_THRESHOLD = 0.92   # cosine similarity for near-duplicate detection

# ── Sections mapped to content types ─────────────────────────────────────
SECTION_META = {
    "Section 1":  {"section": "eligibility",  "content_type": "table"},
    "Section 2":  {"section": "interview",    "content_type": "text"},
    "Section 3":  {"section": "hiring",       "content_type": "table+image"},
    "Section 4":  {"section": "multihop",     "content_type": "reasoning"},
    "Section 5":  {"section": "trend",        "content_type": "timeseries"},
    "Section 6":  {"section": "conflict",     "content_type": "conflict"},
    "Section 7":  {"section": "statistics",   "content_type": "table"},
    "Section 8":  {"section": "adversarial",  "content_type": "eval_only"},
    "Section 9":  {"section": "eval_queries", "content_type": "eval_only"},
    "Section 10": {"section": "chunking_guide","content_type": "meta"},
}

# ── Adversarial / Out-of-corpus query patterns ────────────────────────────
# If a query matches these patterns AND similarity is low → fallback
OUT_OF_CORPUS_PATTERNS = [
    "campus visit date",
    "stock price",
    "work from home",
    "work-from-home",
    "how many students from svecw",
    "which is better for my career",
    "pays the highest in the world",
]

# ── API server ────────────────────────────────────────────────────────────
API_HOST    = "0.0.0.0"
API_PORT    = 8000
API_RELOAD  = True

# ── Logging ───────────────────────────────────────────────────────────────
LOG_LEVEL   = "INFO"
LOG_FILE    = LOGS_DIR / "rag.log"