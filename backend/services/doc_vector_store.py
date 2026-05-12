"""
backend/services/doc_vector_store.py
======================================
Builds and queries a per-document FAISS vector index.

Each uploaded document gets its own isolated vector store at:
    vector_db/doc_index/<stem>/

This lets the RAG query answer questions about the *specific uploaded document*
rather than the general knowledge base.
"""

import re
import logging
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from config.settings import DOC_INDEX_DIR, EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)

# ─── Shared embeddings (loaded once) ─────────────────────────────────────────
_embeddings: HuggingFaceEmbeddings | None = None

def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info("Loading embedding model for doc index...")
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Embedding model ready.")
    return _embeddings


# ─── Text chunking ────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """Split text into overlapping character-level chunks."""
    text = re.sub(r'\s+', ' ', text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ─── Public API ──────────────────────────────────────────────────────────────

def build_doc_index(stem: str, text: str) -> Path:
    """
    Build a FAISS vector store for a single document.

    Args:
        stem:  filename without extension (used as the index folder name)
        text:  full extracted text of the document

    Returns:
        Path to the saved index directory
    """
    index_dir = DOC_INDEX_DIR / stem
    index_dir.mkdir(parents=True, exist_ok=True)

    chunks = _chunk_text(text)
    if not chunks:
        logger.warning(f"No text chunks for doc '{stem}'. Skipping index build.")
        return index_dir

    logger.info(f"Building doc index for '{stem}' ({len(chunks)} chunks)...")
    embeddings = _get_embeddings()
    store = FAISS.from_texts(chunks, embeddings)
    store.save_local(str(index_dir))
    logger.info(f"Doc index saved → {index_dir}")
    return index_dir


def query_doc_index(stem: str, query: str, k: int = 5) -> list[str]:
    """
    Query the per-document FAISS index for a given stem.

    Returns:
        List of relevant text passages, or empty list if index not found.
    """
    index_dir = DOC_INDEX_DIR / stem
    if not index_dir.exists():
        logger.warning(f"No doc index found for '{stem}' at {index_dir}")
        return []

    embeddings = _get_embeddings()
    store = FAISS.load_local(
        str(index_dir),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    docs = store.similarity_search(query, k=k)
    return [d.page_content for d in docs]


def get_latest_doc_stem() -> str | None:
    """
    Returns the stem of the most recently indexed document,
    based on folder modification time.
    """
    if not DOC_INDEX_DIR.exists():
        return None
    subdirs = [d for d in DOC_INDEX_DIR.iterdir() if d.is_dir()]
    if not subdirs:
        return None
    latest = max(subdirs, key=lambda d: d.stat().st_mtime)
    return latest.name


def list_doc_stems() -> list[str]:
    """Return all available per-document index stems."""
    if not DOC_INDEX_DIR.exists():
        return []
    return [d.name for d in DOC_INDEX_DIR.iterdir() if d.is_dir()]
