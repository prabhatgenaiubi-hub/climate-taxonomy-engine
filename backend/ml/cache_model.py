"""
backend/ml/cache_model.py
==========================
One-time script to download and cache the sentence-transformer embedding
model locally so the app works fully offline.
Run once: python -m backend.ml.cache_model
"""

from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL_NAME, EMBEDDING_CACHE_DIR

if __name__ == "__main__":
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, cache_folder=EMBEDDING_CACHE_DIR)
    print(f"✅ Model '{EMBEDDING_MODEL_NAME}' cached to {EMBEDDING_CACHE_DIR}")
