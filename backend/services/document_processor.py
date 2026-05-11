"""
backend/services/document_processor.py
=======================================
Handles all document ingestion: text extraction from PDF (native + OCR),
DOCX, and TXT. Consolidates extract_text.py + ocr_and_extract.py +
extract_and_save_all.py into a single clean service.
"""

import os
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from docx import Document
from pathlib import Path

from config.settings import (
    RAW_DIR, PROCESSED_DIR, POPPLER_PATH
)


# ─── Low-level extractors ────────────────────────────────────────────────────

def extract_from_docx(path: str) -> str:
    try:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        raise RuntimeError(f"DOCX extraction failed: {e}") from e


def extract_from_pdf_native(path: str) -> str:
    try:
        doc = fitz.open(path)
        return "".join(page.get_text("text") for page in doc)
    except Exception as e:
        raise RuntimeError(f"Native PDF extraction failed: {e}") from e


def extract_from_pdf_ocr(path: str) -> str:
    try:
        pages = convert_from_path(path, dpi=300, poppler_path=POPPLER_PATH)
        return "".join(
            pytesseract.image_to_string(page, lang="eng")
            for page in pages
        )
    except Exception as e:
        raise RuntimeError(f"OCR extraction failed: {e}") from e


def extract_from_pdf(path: str) -> str:
    """Try native extraction first; fall back to OCR for scanned PDFs."""
    text = extract_from_pdf_native(path)
    if len(text.strip()) < 100:
        return extract_from_pdf_ocr(path)
    return text


# ─── Public API ──────────────────────────────────────────────────────────────

def extract_text(filepath: str) -> str:
    """
    Extract text from a supported file (PDF, DOCX, TXT).
    Raises RuntimeError for unsupported formats.
    """
    ext = os.path.splitext(filepath)[-1].lower()
    if ext == ".docx":
        return extract_from_docx(filepath)
    elif ext == ".pdf":
        return extract_from_pdf(filepath)
    elif ext == ".txt":
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise RuntimeError(f"Unsupported file type: {ext}")


def save_uploaded_file(uploaded_file) -> Path:
    """Save a Streamlit UploadedFile to RAW_DIR. Returns path."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DIR / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def process_uploaded_file(uploaded_file) -> str:
    """
    Save upload → extract text → persist to PROCESSED_DIR.
    Returns extracted text string.
    """
    file_path = save_uploaded_file(uploaded_file)
    text = extract_text(str(file_path))
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(uploaded_file.name).stem
    processed_path = PROCESSED_DIR / f"{stem}.txt"
    with open(processed_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def process_uploaded_file_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Accept raw bytes (from FastAPI UploadFile.read()) + filename,
    save to RAW_DIR, extract text, persist to PROCESSED_DIR.
    Returns extracted text string.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DIR / filename
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    text = extract_text(str(file_path))
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(filename).stem
    processed_path = PROCESSED_DIR / f"{stem}.txt"
    with open(processed_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def process_all(source_dir: Path = None, output_dir: Path = None) -> None:
    """Batch-process all files in source_dir and save to output_dir."""
    source_dir = source_dir or RAW_DIR
    output_dir = output_dir or PROCESSED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    for fp in source_dir.iterdir():
        if fp.suffix.lower() in {".pdf", ".docx", ".txt"}:
            try:
                text = extract_text(str(fp))
                out = output_dir / f"{fp.stem}.txt"
                with open(out, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"✅ Processed: {fp.name}")
            except Exception as e:
                print(f"❌ Failed {fp.name}: {e}")
