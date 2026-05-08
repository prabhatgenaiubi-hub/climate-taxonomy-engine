"""
app/main.py
============
Streamlit frontend — UI only.
All business logic lives in backend/services/*.
"""

import base64
import logging
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from config.settings import (
    ASSETS_DIR, LOGO_PATH, BG_IMAGE_PATH,
    FILTERED_DIR, VULNERABILITIES_DIR, CLASSIFIED_DIR,
)
from backend.services.document_processor import process_uploaded_file, save_uploaded_file
from backend.services.sector_filter import (
    extract_bsr_code, classify_sector, save_sector_weights,
)
from backend.services.adaptation_checker import check_districts
from backend.services.classifier import classify_single_file

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_FILE = Path(__file__).parent / "app.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ─── CSS / Theme ─────────────────────────────────────────────────────────────

def _build_css() -> str:
    bg_b64 = ""
    if BG_IMAGE_PATH.exists():
        bg_b64 = base64.b64encode(BG_IMAGE_PATH.read_bytes()).decode()

    return f"""
    <style>
    .stApp {{
        background-image: url('data:image/jpeg;base64,{bg_b64}');
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        position: fixed; top: 0; left: 0;
        width: 100%; height: 100%; z-index: -1;
    }}
    .main {{ position: relative; z-index: 1; padding: 20px; border-radius: 10px; }}
    .stButton>button {{
        background-color: #003087 !important; color: white !important;
        border-radius: 8px; padding: 10px 20px; font-weight: bold;
        border: none; transition: background-color 0.3s;
    }}
    .stButton>button:hover {{ background-color: #0053a0 !important; }}
    .stFileUploader {{ border: 2px dashed #003087 !important; border-radius: 10px; padding: 10px; }}
    .result-card {{
        background-color: rgba(255,255,255,0.9) !important;
        padding: 15px; border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 10px;
    }}
    h1 {{ color: #003087 !important; font-family: Arial, sans-serif !important; }}
    h3 {{ color: #333   !important; font-family: Arial, sans-serif !important; }}
    .stProgress .st-bo {{ background-color: #003087 !important; }}
    </style>
    """


# ─── Pipeline ────────────────────────────────────────────────────────────────

def run_pipeline(uploaded_file) -> dict | None:
    """
    Full classification pipeline for a single uploaded file.
    Returns result dict or None on failure.
    """
    stem = Path(uploaded_file.name).stem

    # 1. Extract text and save to processed/
    text = process_uploaded_file(uploaded_file)

    # 2. Sector filter
    bsr_code      = extract_bsr_code(text)
    sector_result = classify_sector(bsr_code)

    if sector_result["Decision"] == "Not under Climate Finance":
        return {
            "filename":          uploaded_file.name,
            "classification":    "Not under Climate Finance",
            "bsr_code":          bsr_code,
            "mitigation_score":  0,
            "adaptation_score":  0,
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
        st.error(f"Adaptation check failed for {uploaded_file.name}")
        return None

    # 4. Classification
    try:
        result = classify_single_file(f"{stem}.txt")
    except Exception as e:
        st.error(f"Classification failed: {e}")
        import traceback; st.text(traceback.format_exc())
        return None

    if result:
        result["filename"] = uploaded_file.name
        result["bsr_code"] = bsr_code
    return result


# ─── UI Components ───────────────────────────────────────────────────────────

def render_sidebar() -> None:
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), width=100, use_container_width=False)
    else:
        st.sidebar.warning("Logo 'union_bank_logo.png' not found in assets/.")
    st.sidebar.title("Climate Finance Classifier")
    st.sidebar.markdown("Upload documents to classify climate finance projects.")
    st.sidebar.markdown("**Supported formats:** PDF, DOCX, TXT")


def render_header() -> None:
    if LOGO_PATH.exists():
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(str(LOGO_PATH), width=100, use_container_width=False)
        with col2:
            st.markdown("<h1>Union Bank of India<br>Climate Finance Classifier</h1>",
                        unsafe_allow_html=True)
            st.markdown("<p>Classify documents for climate finance eligibility.</p>",
                        unsafe_allow_html=True)
    else:
        st.markdown("<h1>Union Bank of India — Climate Finance Classifier</h1>",
                    unsafe_allow_html=True)


def render_results(result: dict) -> None:
    st.subheader("📊 Classification Results")
    st.markdown(f"""
        <div class="result-card">
            <strong>File:</strong> {result['filename']}<br>
            <strong>Classification:</strong> {result['classification']}<br>
            <strong>BSR Code:</strong> {result.get('bsr_code', 'N/A')}<br>
            <strong>Mitigation Score:</strong> {result['mitigation_score']:.2f}<br>
            <strong>Adaptation Score:</strong> {result['adaptation_score']:.2f}<br>
            <strong>Mitigation Sector Weight:</strong> {result.get('sector_mit_weight', 'N/A')}<br>
            <strong>Adaptation Sector Weight:</strong> {result.get('sector_adapt_weight', 'N/A')}<br>
        </div>
    """, unsafe_allow_html=True)

    with st.expander("Detailed Scores"):
        for key, label in [
            ("kw_avg_mitigation_score",         "KW Mitigation Score"),
            ("kw_avg_adaptation_score",          "KW Adaptation Score"),
            ("avg_mitigation_similarity_score",  "Mitigation RAG Similarity"),
            ("avg_adaptation_similarity_score",  "Adaptation RAG Similarity"),
            ("avg_adaptation_action_score",      "Adaptation Action-to-Risk"),
        ]:
            if key in result:
                st.markdown(f"**{label}:** {float(result[key]):.2f}")

    # Sector weights
    weights_csv = FILTERED_DIR / "sector_weights.csv"
    if weights_csv.exists():
        wdf = pd.read_csv(weights_csv)
        wrow = wdf[wdf["filename"] == f"{Path(result['filename']).stem}.txt"]
        if not wrow.empty:
            st.markdown(f"""
                <div class="result-card">
                    <strong>Sector Weights:</strong> {wrow['weights'].iloc[0]}
                </div>""", unsafe_allow_html=True)

    # District vulnerabilities
    vuln_csv = VULNERABILITIES_DIR / "district_vulnerabilities.csv"
    if vuln_csv.exists():
        vdf  = pd.read_csv(vuln_csv)
        vrow = vdf[vdf["filename"] == f"{Path(result['filename']).stem}.txt"]
        if not vrow.empty and "vulnerabilities" in vrow.columns:
            st.markdown(f"""
                <div class="result-card">
                    <strong>Districts &amp; Vulnerabilities:</strong>
                    {vrow['vulnerabilities'].iloc[0]}
                </div>""", unsafe_allow_html=True)

    # Download
    csv_data = pd.DataFrame([result]).to_csv(index=False)
    st.download_button(
        label="⬇ Download Results as CSV",
        data=csv_data,
        file_name=f"{Path(result['filename']).stem}_classification.csv",
        mime="text/csv",
    )

    # Matched keywords
    if result.get("matched_keywords"):
        st.markdown(f"""
            <div class="result-card">
                <strong>Matched Keywords:</strong><br>
                {", ".join(result['matched_keywords'])}
            </div>""", unsafe_allow_html=True)


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(_build_css(), unsafe_allow_html=True)
    render_sidebar()
    render_header()

    with st.container():
        st.subheader("Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a PDF, Word, or Text document",
            type=["pdf", "docx", "txt"],
            help="Upload a document to analyse its climate finance classification.",
        )

    if uploaded_file:
        progress  = st.progress(0)
        status    = st.empty()
        status.text("Processing document...")

        result = run_pipeline(uploaded_file)
        progress.progress(100)
        status.text("Processing complete!")

        if result:
            with st.container():
                render_results(result)


if __name__ == "__main__":
    main()
