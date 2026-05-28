"""
vector_store.py — ChromaDB wrapper for the placement RAG system.

Responsibilities:
  - Build the collection from Document chunks
  - Persist to disk (survives restarts)
  - Query with metadata filters
  - Return top-K results with scores
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger

from config import CHROMA_COLLECTION, CHROMA_DIR, EMBED_BATCH_SIZE, EMBED_MODEL, RETRIEVAL_TOP_K
from ingestion.chunker import Document


@dataclass
class RetrievedChunk:
    """One chunk returned from vector search."""
    id:         str
    text:       str
    metadata:   dict[str, Any]
    score:      float          # cosine distance (lower = more similar)


class VectorStore:
    """
    Thin wrapper around ChromaDB with SentenceTransformer embeddings.

    Usage
    -----
        vs = VectorStore()
        vs.build(docs)          # first run
        vs.load()               # subsequent runs
        results = vs.query("What CGPA does TCS require?")
    """

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._ef = SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL,
            normalize_embeddings=True,
        )
        self._collection: chromadb.Collection | None = None

    # ── Build ─────────────────────────────────────────────────────────

    def build(self, documents: list[Document], force_rebuild: bool = False) -> None:
        """
        Embed all documents and store in ChromaDB.
        If the collection already exists and force_rebuild=False, skip.
        """
        existing = [c.name for c in self._client.list_collections()]

        if CHROMA_COLLECTION in existing and not force_rebuild:
            logger.info(f"Collection '{CHROMA_COLLECTION}' already exists. Loading.")
            self.load()
            return

        if CHROMA_COLLECTION in existing:
            self._client.delete_collection(CHROMA_COLLECTION)

        self._collection = self._client.create_collection(
            name=CHROMA_COLLECTION,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

        # Batch insert
        batch_size = EMBED_BATCH_SIZE
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            self._collection.add(
                ids=[d.id for d in batch],
                documents=[d.text for d in batch],
                metadatas=[d.metadata for d in batch],
            )
            logger.debug(f"Inserted batch {i//batch_size + 1}: {len(batch)} chunks")

        logger.success(
            f"Vector store built: {len(documents)} chunks in '{CHROMA_COLLECTION}'"
        )

    # ── Load ──────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load an existing persisted collection."""
        self._collection = self._client.get_collection(
            name=CHROMA_COLLECTION,
            embedding_function=self._ef,
        )
        count = self._collection.count()
        logger.info(f"Vector store loaded: {count} chunks in '{CHROMA_COLLECTION}'")

    # ── Query ─────────────────────────────────────────────────────────

    def query(
        self,
        query_text:    str,
        top_k:         int = RETRIEVAL_TOP_K,
        where:         Optional[dict] = None,   # ChromaDB metadata filter
    ) -> list[RetrievedChunk]:
        """
        Semantic search with optional metadata filter.

        Parameters
        ----------
        query_text : natural language query
        top_k      : number of candidates to return
        where      : ChromaDB $eq/$in filter dict, e.g. {"section": {"$eq": "eligibility"}}
        """
        if self._collection is None:
            raise RuntimeError("Vector store not initialised. Call build() or load() first.")

        kwargs: dict[str, Any] = {
            "query_texts":   [query_text],
            "n_results":     min(top_k, self._collection.count()),
            "include":       ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        chunks: list[RetrievedChunk] = []
        for doc, meta, dist, chunk_id in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
            results["ids"][0],
        ):
            chunks.append(RetrievedChunk(
                id=chunk_id,
                text=doc,
                metadata=meta,
                score=dist,
            ))

        return chunks

    # ── Filtered helpers ──────────────────────────────────────────────

    def query_section(
        self,
        query_text: str,
        section:    str,
        top_k:      int = RETRIEVAL_TOP_K,
    ) -> list[RetrievedChunk]:
        """Query restricted to a specific section."""
        return self.query(
            query_text,
            top_k=top_k,
            where={"section": {"$eq": section}},
        )

    def get_by_company(self, company: str, section: Optional[str] = None) -> list[RetrievedChunk]:
        """Retrieve all chunks for a specific company."""
        where: dict = {"company": {"$eq": company}}
        if section:
            where = {"$and": [where, {"section": {"$eq": section}}]}

        results = self._collection.get(
            where=where,
            include=["documents", "metadatas"],
        )
        return [
            RetrievedChunk(id=i, text=d, metadata=m, score=0.0)
            for i, d, m in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_conflict_records(self, company: str) -> list[RetrievedChunk]:
        """Retrieve both official and portal records for a company."""
        return self.get_by_company(company, section="conflict")

    @property
    def count(self) -> int:
        if self._collection is None:
            return 0
        return self._collection.count()