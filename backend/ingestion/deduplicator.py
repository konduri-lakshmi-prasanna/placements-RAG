"""
deduplicator.py — Near-duplicate removal for interview experience text.

The dataset intentionally repeats each company's interview section 3×.
We detect duplicates via cosine similarity of sentence embeddings
and keep only the first occurrence (highest-quality chunk).

This is a RAG best-practice: embedding duplicates wastes vector store
space and distorts retrieval rankings.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer

from config import DEDUP_SIMILARITY_THRESHOLD, EMBED_MODEL


_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


@dataclass
class TextChunk:
    text:     str
    metadata: dict


def deduplicate(chunks: list[TextChunk]) -> list[TextChunk]:
    """
    Remove near-duplicate chunks using cosine similarity.

    Algorithm
    ---------
    1. Embed all chunks with SentenceTransformer.
    2. For each chunk, check cosine similarity against all already-kept chunks.
    3. If max similarity > threshold → skip (duplicate).
    4. Else → keep.

    Returns
    -------
    list[TextChunk]
        De-duplicated chunks, preserving order of first occurrence.
    """
    if not chunks:
        return []

    model  = _get_model()
    texts  = [c.text for c in chunks]
    embeds = model.encode(texts, batch_size=64, show_progress_bar=False)
    embeds = embeds / np.linalg.norm(embeds, axis=1, keepdims=True)  # L2-normalize

    kept_indices: list[int] = []
    kept_embeds:  list[np.ndarray] = []

    for i, emb in enumerate(embeds):
        if not kept_embeds:
            kept_indices.append(i)
            kept_embeds.append(emb)
            continue

        sims = np.array([float(np.dot(emb, ke)) for ke in kept_embeds])
        if sims.max() >= DEDUP_SIMILARITY_THRESHOLD:
            logger.debug(
                f"Dedup: skipping chunk {i} "
                f"(sim={sims.max():.3f} ≥ {DEDUP_SIMILARITY_THRESHOLD})"
            )
        else:
            kept_indices.append(i)
            kept_embeds.append(emb)

    kept = [chunks[i] for i in kept_indices]
    removed = len(chunks) - len(kept)
    logger.info(
        f"Deduplication: {len(chunks)} → {len(kept)} chunks "
        f"({removed} duplicates removed)"
    )
    return kept