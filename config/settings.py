"""
config/settings.py
==================
Single source of truth for all project-wide paths, thresholds, and constants.
All other modules import from here — no hardcoded paths anywhere else.
"""

from pathlib import Path

# ─── Project Root ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ─── Data Directories ────────────────────────────────────────────────────────
DATA_DIR             = PROJECT_ROOT / "data"
RAW_DIR              = DATA_DIR / "raw"
PROCESSED_DIR        = DATA_DIR / "processed"
FILTERED_DIR         = DATA_DIR / "filtered"
VULNERABILITIES_DIR  = DATA_DIR / "vulnerabilities"
CLASSIFIED_DIR       = DATA_DIR / "classified"
LABELED_DIR          = DATA_DIR / "labeled"
OCR_DIR              = DATA_DIR / "ocr_pdfs"
ADAPTATION_MAPS_DIR  = DATA_DIR / "adaptation_maps"

# ─── Model Directories ───────────────────────────────────────────────────────
MODELS_DIR                   = PROJECT_ROOT / "models"
DISTILROBERTA_MODEL_DIR      = str(MODELS_DIR / "distilroberta-base-climate-f")
CLIMATEBERT_FINETUNED_DIR    = str(MODELS_DIR / "climatebert-finetuned")
EMBEDDING_MODEL_NAME         = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_CACHE_DIR          = str(Path.home() / ".cache" / "huggingface" / "hub")

# ─── Vector DB ───────────────────────────────────────────────────────────────
VECTOR_DB_DIR        = PROJECT_ROOT / "vector_db"
VECTOR_DB_INDEX_DIR  = VECTOR_DB_DIR / "index.faiss"
DOC_INDEX_DIR        = VECTOR_DB_DIR / "doc_index"   # per-document FAISS stores

# ─── Documents / Knowledge Base ──────────────────────────────────────────────
DOCUMENTS_DIR        = PROJECT_ROOT / "documents"
MITIGATION_DOCS_DIR  = DOCUMENTS_DIR / "mitigation_knowledge"
ADAPTATION_DOCS_DIR  = DOCUMENTS_DIR / "adaptation knowledge"

# ─── Assets ──────────────────────────────────────────────────────────────────
ASSETS_DIR           = PROJECT_ROOT / "assets"
LOGO_PATH            = ASSETS_DIR / "union_bank_logo.png"
BG_IMAGE_PATH        = ASSETS_DIR / "bg.jpg"

# ─── Reference Data Files ────────────────────────────────────────────────────
RBI_SECTOR_MAPPING   = DATA_DIR / "rbi_sector_mapping.xlsx"
DISTRICTS_FILE       = ADAPTATION_MAPS_DIR / "districts.xlsx"
CHVA_FILE            = ADAPTATION_MAPS_DIR / "all_district_chva.xlsx"
SECTOR_WEIGHTS_CSV   = FILTERED_DIR / "sector_weights.csv"
DISTRICT_VULN_CSV    = VULNERABILITIES_DIR / "district_vulnerabilities.csv"
CLASSIFICATIONS_CSV  = CLASSIFIED_DIR / "classifications.csv"

# ─── Feedback / Retraining ───────────────────────────────────────────────────
FEEDBACK_LOG         = PROJECT_ROOT / "data" / "labeled" / "user_feedback_log.csv"
CORRECTION_LOG       = PROJECT_ROOT / "data" / "labeled" / "corrections_for_finetuning.csv"

# ─── Classification Thresholds ───────────────────────────────────────────────
SIMILARITY_THRESHOLD_RAG        = 0.25
CLIMATE_KEYWORD_THRESHOLD       = 0.1
KEYWORD_ACTION_THRESHOLD        = 0.3
FINAL_CLASSIFICATION_THRESHOLD  = 1.4
FUZZY_MATCH_THRESHOLD           = 0.7

# ─── Poppler (Windows) ───────────────────────────────────────────────────────
import glob as _glob
import shutil as _shutil
import os as _os

def find_poppler_path():
    """Auto-detect poppler bin path on Windows. Returns None if on PATH."""
    if _shutil.which("pdftoppm"):
        return None
    candidates = (
        _glob.glob(r"C:\Poppler\*\Library\bin") +
        _glob.glob(r"C:\poppler*\Library\bin") +
        _glob.glob(r"C:\Program Files\poppler*\Library\bin") +
        [r"C:\Poppler\Library\bin"]
    )
    for path in candidates:
        if _os.path.isfile(_os.path.join(path, "pdftoppm.exe")):
            return path
    return None

POPPLER_PATH = find_poppler_path()

# ─── Offline Mode ────────────────────────────────────────────────────────────
import os as _os2
_os2.environ["HF_HUB_OFFLINE"] = "True"
