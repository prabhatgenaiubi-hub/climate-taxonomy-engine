"""
backend/ml/rag_engine.py
=========================
Builds and manages the FAISS vector store from mitigation/adaptation
knowledge documents. Moved from src/rag_engine.py.
"""

import re
import pickle
import logging
import shutil
from pathlib import Path

import torch
import pandas as pd
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from transformers import AutoTokenizer

from config.settings import (
    DOCUMENTS_DIR, VECTOR_DB_DIR, EMBEDDING_MODEL_NAME,
    EMBEDDING_CACHE_DIR, DISTILROBERTA_MODEL_DIR,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def clean_text(text: str) -> str:
    text = re.sub(r'http[s]?://\S+', '', text)
    return re.sub(r'\[\d+\]', '', text).strip()


def _pre_chunk(text: str, chunk_size: int = 2000) -> list[str]:
    return [text[i: i + chunk_size] for i in range(0, len(text), chunk_size)]


def _tokenize_and_split(text: str, tokenizer, source: str,
                         max_tokens: int = 400, overlap: int = 80) -> list[dict]:
    segments = []
    for chunk in _pre_chunk(text):
        tokens = tokenizer.encode(chunk, add_special_tokens=False, truncation=False)
        for i in range(0, len(tokens), max_tokens - overlap):
            seg = tokenizer.decode(tokens[i: i + max_tokens],
                                   skip_special_tokens=True,
                                   clean_up_tokenization_spaces=True)
            if seg.strip():
                segments.append({"text": seg, "source": source})
    return segments


def _process_excel(file_path: Path) -> tuple[str, str]:
    try:
        df = pd.read_excel(file_path, sheet_name="Sheet1")
        mit  = clean_text(" ".join(df["Mitigation"].dropna().astype(str)))
        adpt = clean_text(" ".join(df["Adaptation"].dropna().astype(str)))
        return mit, adpt
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        return "", ""


def build_vector_store() -> None:
    """Build FAISS vector store from documents/ knowledge base."""
    tokenizer = AutoTokenizer.from_pretrained(DISTILROBERTA_MODEL_DIR)
    documents = []

    for subdir_name in ["mitigation_knowledge", "adaptation knowledge"]:
        subdir = DOCUMENTS_DIR / subdir_name
        if not subdir.exists():
            logger.warning(f"Skipping missing directory: {subdir}")
            continue
        for fp in subdir.glob("*.txt"):
            try:
                text = clean_text(fp.read_text(encoding="utf-8"))
                documents.extend(_tokenize_and_split(text, tokenizer, str(fp)))
            except Exception as e:
                logger.error(f"Failed {fp}: {e}")
        for fp in subdir.glob("*.xlsx"):
            mit_text, adpt_text = _process_excel(fp)
            text = mit_text if "mitigation" in subdir_name else adpt_text
            if text:
                documents.extend(_tokenize_and_split(text, tokenizer, str(fp)))

    if not documents:
        logger.error("No documents loaded. Aborting vector store build.")
        return

    texts = [d["text"] for d in documents]
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": DEVICE},
        cache_folder=EMBEDDING_CACHE_DIR,
    )
    vector_store = FAISS.from_texts(texts, embeddings)
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(VECTOR_DB_DIR / "index.faiss"))
    with open(VECTOR_DB_DIR / "store.pkl", "wb") as f:
        pickle.dump(documents, f)
    logger.info(f"✅ Vector store built with {len(documents)} segments.")


if __name__ == "__main__":
    build_vector_store()
