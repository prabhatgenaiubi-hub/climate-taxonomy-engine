"""
backend/api/main.py
====================
FastAPI REST API — exposes the climate finance classification pipeline.

Run with:
    uvicorn backend.api.main:app --reload --port 8000
(from project root D:\\Prabhat\\climate-taxonomy-engine)
"""

import sys
import time
import logging
import traceback
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from config.settings import (
    FILTERED_DIR, VULNERABILITIES_DIR, CLASSIFIED_DIR,
)
from backend.services.document_processor import process_uploaded_file_bytes
from backend.services.sector_filter import (
    extract_bsr_code, classify_sector, save_sector_weights,
)
from backend.services.adaptation_checker import check_districts
from backend.services.classifier import classify_single_file
from backend.services.doc_vector_store import build_doc_index, query_doc_index, get_latest_doc_stem
from backend.db.database import init_db
from backend.api.auth import router as auth_router, get_current_user
from pydantic import BaseModel

# ─── App setup ───────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Climate Taxonomy Engine API",
    description="Classifies uploaded documents for climate finance eligibility.",
    version="1.0.0",
)

# Allow React dev server (port 5173) and any localhost origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    init_db()   # Create SQLite tables if not exist

# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(auth_router)

# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Simple liveness check."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/classify")
async def classify_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a PDF, DOCX, or TXT document and receive full climate
    finance classification results.
    """
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    if file.content_type not in allowed_types:
        # also accept by extension
        ext = Path(file.filename).suffix.lower()
        if ext not in {".pdf", ".docx", ".txt"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. "
                       "Please upload PDF, DOCX, or TXT.",
            )

    stem = Path(file.filename).stem
    file_bytes = await file.read()

    logger.info(f"Received file: {file.filename} ({len(file_bytes)} bytes)")

    try:
        # 1. Extract text
        text = process_uploaded_file_bytes(file_bytes, file.filename)
        if not text or not text.strip():
            raise HTTPException(status_code=422, detail="Could not extract text from the file.")

        # 1b. Build per-document vector index for RAG queries
        try:
            build_doc_index(stem, text)
        except Exception as idx_exc:
            logger.warning(f"Doc index build failed (non-fatal): {idx_exc}")

        # 2. Sector filter
        bsr_code      = extract_bsr_code(text)
        sector_result = classify_sector(bsr_code)

        if sector_result["Decision"] == "Not under Climate Finance":
            return {
                "filename":         file.filename,
                "classification":   "Not under Climate Finance",
                "bsr_code":         bsr_code,
                "mitigation_score": 0,
                "adaptation_score": 0,
                "matched_keywords": [],
                "sector_mit_weight":   None,
                "sector_adapt_weight": None,
            }

        # Save filtered copy + sector weights
        FILTERED_DIR.mkdir(parents=True, exist_ok=True)
        (FILTERED_DIR / f"{stem}.txt").write_text(text, encoding="utf-8")
        save_sector_weights(stem, bsr_code, sector_result)

        # 3. Adaptation checker
        check_districts()
        time.sleep(2)

        vuln_txt = VULNERABILITIES_DIR / f"{stem}.txt"
        vuln_csv = VULNERABILITIES_DIR / "district_vulnerabilities.csv"
        if not vuln_txt.exists() or not vuln_csv.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Adaptation check failed for {file.filename}",
            )

        # 4. Classification
        result = classify_single_file(f"{stem}.txt")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))

    if not result:
        raise HTTPException(status_code=500, detail="Classification returned no result.")

    result["filename"] = file.filename
    result["bsr_code"] = bsr_code

    # Attach sector weights
    weights_csv = FILTERED_DIR / "sector_weights.csv"
    if weights_csv.exists():
        try:
            wdf  = pd.read_csv(weights_csv)
            wrow = wdf[wdf["filename"] == f"{stem}.txt"]
            if not wrow.empty:
                result["sector_weights_raw"] = wrow["weights"].iloc[0]
        except Exception:
            pass

    # Attach district vulnerabilities
    if vuln_csv.exists():
        try:
            vdf  = pd.read_csv(vuln_csv)
            vrow = vdf[vdf["filename"] == f"{stem}.txt"]
            if not vrow.empty and "vulnerabilities" in vrow.columns:
                result["district_vulnerabilities"] = vrow["vulnerabilities"].iloc[0]
        except Exception:
            pass

    logger.info(f"Classification complete for {file.filename}: {result.get('classification')}")
    return result


@app.get("/results")
def get_all_results():
    """Return all previously classified results from the CSV store."""
    csv_path = CLASSIFIED_DIR / "classifications.csv"
    if not csv_path.exists():
        return {"results": []}
    try:
        df = pd.read_csv(csv_path)
        return {"results": df.to_dict(orient="records")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/results/download")
def download_results():
    """Download the full classifications CSV."""
    csv_path = CLASSIFIED_DIR / "classifications.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="No results file found.")
    return FileResponse(
        path=str(csv_path),
        filename="classifications.csv",
        media_type="text/csv",
    )


# ─── RAG Query ───────────────────────────────────────────────────────────────

class RagQueryRequest(BaseModel):
    query: str
    report_context: str | None = None


# Ollama generative LLM settings
OLLAMA_MODEL = "llama3.2:3b"

def _generate_answer(question: str, context: str, report_context: str | None = None) -> str:
    """Generate a grounded answer using Ollama (local LLM)."""
    import ollama as _ollama
    report_section = (
        f"\n\nClassification Report Data (use this for score/classification questions):\n{report_context}"
        if report_context else ""
    )
    prompt = (
        "You are a climate finance expert assistant. "
        "Answer the question based ONLY on the provided context and report data. "
        "Be concise, clear, and professional. "
        "If the answer is not in the context, say: "
        "'I could not find this information in the document.'\n\n"
        f"Document Context:\n{context}"
        f"{report_section}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )
    try:
        client = _ollama.Client(host="http://127.0.0.1:11434")
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 400},
        )
        return response["message"]["content"].strip()
    except Exception as exc:
        logger.warning(f"Ollama generation failed: {exc}")
        return f"[LLM unavailable — raw context]: {context[:600]}"


@app.post("/rag/query")
def rag_query(
    request: RagQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Query the document-specific FAISS index (built at upload time).
    Falls back to the general knowledge base if no document has been uploaded.
    Uses extractive QA to produce a direct grounded answer.
    """
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS as FaissStore
    from config.settings import VECTOR_DB_DIR, EMBEDDING_MODEL_NAME

    try:
        # ── 1. Try document-specific index first ──────────────────────────
        doc_stem = get_latest_doc_stem()
        passages = []
        source_label = "general knowledge base"

        if doc_stem:
            passages = query_doc_index(doc_stem, request.query, k=5)
            if passages:
                source_label = f"uploaded document: {doc_stem}"
                logger.info(f"RAG: using doc index '{doc_stem}' ({len(passages)} passages)")

        # ── 2. Fall back to general knowledge base ────────────────────────
        if not passages:
            logger.info("RAG: falling back to general knowledge base index")
            index_path = VECTOR_DB_DIR / "index.faiss"
            if not index_path.exists():
                return {"answer": "No document has been uploaded yet and no general knowledge base index found. Please classify a document first."}

            embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_NAME,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            store = FaissStore.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            docs = store.similarity_search(request.query, k=5)
            passages = [d.page_content for d in docs]
            source_label = "general knowledge base"

        if not passages:
            return {"answer": "No relevant passages found. Please upload and classify a document first."}

        # ── 3. Generate answer using Ollama LLM ──────────────────────────
        combined_context = "\n\n".join(passages)[:4000]
        direct_answer = _generate_answer(request.query, combined_context, request.report_context)

        answer = (
            f"**Answer:** {direct_answer}\n\n"
            f"*(Source: {source_label})*\n\n"
            f"---\n\n"
            f"**Supporting context:**\n{combined_context[:800]}{'...' if len(combined_context) > 800 else ''}"
        )
        return {"answer": answer, "num_passages": len(passages), "source": source_label}

    except Exception as exc:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/rag/docs")
def rag_list_docs(current_user: dict = Depends(get_current_user)):
    """List all documents that have a per-document vector index built."""
    from backend.services.doc_vector_store import list_doc_stems, get_latest_doc_stem
    return {
        "docs": list_doc_stems(),
        "latest": get_latest_doc_stem(),
    }
