import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import logging
import glob
import os
import time
import base64

# PATH SETUP
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
ASSETS_DIR = PROJECT_ROOT / "assets"  # Folder for assets

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FILTERED_DIR = PROJECT_ROOT / "data" / "filtered"
VULNERABILITIES_DIR = PROJECT_ROOT / "data" / "vulnerabilities"
OUTPUT_DIR = PROJECT_ROOT / "data" / "classified"

# LOGGING
LOG_FILE = SCRIPT_DIR / "ap.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# SRC CHECKS
if not SRC_DIR.exists():
    st.error(f"Cannot find src folder at {SRC_DIR}.")
    st.stop()
for file in ["extract_text.py", "sector_filter.py", "adaptation_checker.py", "classify.py"]:
    if not (SRC_DIR / file).exists():
        st.error(f"Missing {file} in {SRC_DIR}")
        st.stop()
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    import extract_text
    import sector_filter
    import adaptation_checker
    import classify
except Exception as import_err:
    st.error(f"Failed to import internal modules: {import_err}")
    st.stop()

# Convert bg.jpg to base64 for CSS background
bg_path = ASSETS_DIR / "bg.jpg"
bg_base64 = None
if bg_path.exists():
    with open(bg_path, "rb") as bg_file:
        bg_base64 = base64.b64encode(bg_file.read()).decode()

# Custom CSS for enhanced styling with full-page background
css = """
    <style>
    .stApp {
        background-image: url('data:image/jpeg;base64,"""
if bg_base64:
    css += f"{bg_base64}"
else:
    css += "''"
css += """');
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
    }
    .main {
        position: relative;
        z-index: 1;
        padding: 20px;
        border-radius: 10px;
    }
    .stButton>button {
        background-color: #003087 !important;
        color: white !important;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        transition: background-color 0.3s;
    }
    .stButton>button:hover { background-color: #0053a0 !important; }
    .stFileUploader { border: 2px dashed #003087 !important; border-radius: 10px; padding: 10px; }
    .result-card {
        background-color: rgba(255, 255, 255, 0.9) !important;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    h1 { color: #003087 !important; font-family: 'Arial', sans-serif !important; }
    h3 { color: #333 !important; font-family: 'Arial', sans-serif !important; }
    .stProgress .st-bo { background-color: #003087 !important; }
    .title-container { display: flex; align-items: center; }
    .title-logo { height: 100px; margin-right: 15px; }
    </style>
"""
st.markdown(css, unsafe_allow_html=True)

def process_file(uploaded_file):
    RAW_DIR.mkdir(exist_ok=True, parents=True)
    file_path = RAW_DIR / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    # Text Extraction
    PROCESSED_DIR.mkdir(exist_ok=True)
    if uploaded_file.name.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = extract_text.extract_text(str(file_path))
    processed_path = PROCESSED_DIR / f"{uploaded_file.name.rsplit('.', 1)[0]}.txt"
    with open(processed_path, "w", encoding="utf-8") as f:
        f.write(text)
    # Sector Filter
    bsr_code = sector_filter.extract_bsr_code(text)
    sector_result = sector_filter.classify_sector(bsr_code)
    if sector_result["Decision"] == "Not under Climate Finance":
        return {
            "filename": uploaded_file.name,
            "classification": "Not under Climate Finance",
            "bsr_code": bsr_code,
            "mitigation_score": 0,
            "adaptation_score": 0,
        }
    FILTERED_DIR.mkdir(exist_ok=True)
    filtered_path = FILTERED_DIR / f"{uploaded_file.name.rsplit('.', 1)[0]}.txt"
    with open(filtered_path, "w", encoding="utf-8") as f:
        f.write(text)
    weights_entry = {
        "filename": f"{uploaded_file.name.rsplit('.', 1)[0]}.txt",
        "bsr_code": bsr_code,
        "decision": sector_result["Decision"],
        "label": "Proceed",
        "weights": sector_result["Weights"]
    }
    weights_df = pd.DataFrame([weights_entry])
    weights_csv = FILTERED_DIR / "sector_weights.csv"
    if weights_csv.exists():
        existing_df = pd.read_csv(weights_csv)
        existing_df = existing_df[existing_df["filename"] != f"{uploaded_file.name.rsplit('.', 1)[0]}.txt"]
        weights_df = pd.concat([existing_df, weights_df], ignore_index=True)
    weights_df.to_csv(weights_csv, index=False)
    # Adaptation Checker
    VULNERABILITIES_DIR.mkdir(exist_ok=True)
    adaptation_checker.check_districts()
    time.sleep(2)
    vulnerabilities_txt = VULNERABILITIES_DIR / f"{uploaded_file.name.rsplit('.', 1)[0]}.txt"
    vulnerabilities_csv = VULNERABILITIES_DIR / "district_vulnerabilities.csv"
    if not vulnerabilities_txt.exists() or not vulnerabilities_csv.exists():
        st.error(f"Adaptation check failed for {uploaded_file.name}")
        return None
    # Classification (per file only)
    try:
        result = classify.classify_single_file(f"{uploaded_file.name.rsplit('.', 1)[0]}.txt")
    except Exception as e:
        st.error(f"Classification failed with error: {e}")
        import traceback
        st.text(traceback.format_exc())
        return None
    if result is not None:
        # Capture matched keywords from classify_single_file output
        matched_keywords = result.get("matched_keywords", [])  # Assuming classify.py returns this
        result["filename"] = uploaded_file.name
        result["bsr_code"] = bsr_code
        result["matched_keywords"] = matched_keywords  # Add matched keywords to result
        return result
    else:
        st.error("Classification failed for uploaded file")
        return None

def main():
    # Sidebar for branding and navigation
    logo_path = ASSETS_DIR / "union_bank_logo.png"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=100, use_container_width=False)  # Smaller sidebar logo
    else:
        st.sidebar.warning("Logo file 'union_bank_logo.png' not found in assets folder.")
    st.sidebar.title("Climate Finance Classifier")
    st.sidebar.markdown("Upload documents to classify climate finance projects.")
    st.sidebar.markdown("Supported formats: PDF, DOCX, TXT")

    # Main content with logo and title
    logo_path_main = ASSETS_DIR / "union_bank_logo.png"
    if logo_path_main.exists():
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(str(logo_path_main), width=100, use_container_width=False)  # Larger main page logo
        with col2:
            st.markdown("<h1>Union Bank of India \n Climate Finance Classifier</h1>", unsafe_allow_html=True)
            st.markdown("<p>Classify your documents for climate finance eligibility with ease.</p>", unsafe_allow_html=True)
    else:
        st.markdown("""
            <h1>Union Bank of India \n Climate Finance Classifier</h1>
            <p>Logo file 'union_bank_logo.png' not found. Classify your documents for climate finance eligibility with ease.</p>
        """, unsafe_allow_html=True)

    # File uploader
    with st.container():
        st.subheader("Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a PDF, Word, or Text document",
            type=["pdf", "docx", "txt"],
            help="Upload a document to analyze its climate finance classification."
        )

    if uploaded_file:
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Processing document...")

        result = process_file(uploaded_file)
        progress_bar.progress(100)
        status_text.text("Processing complete!")

        if result:
            # Display results in a card-like format
            with st.container():
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

                # Additional scores in an expander
                with st.expander("Detailed Scores"):
                    if "kw_avg_mitigation_score" in result:
                        st.markdown(f"**KW Mitigation Score (keywords):** {float(result['kw_avg_mitigation_score']):.2f}")
                    if "kw_avg_adaptation_score" in result:
                        st.markdown(f"**KW Adaptation Score (keywords):** {float(result['kw_avg_adaptation_score']):.2f}")
                    if "avg_mitigation_similarity_score" in result:
                        st.markdown(f"**Mitigation RAG Similarity Score:** {float(result['avg_mitigation_similarity_score']):.2f}")
                    if "avg_adaptation_similarity_score" in result:
                        st.markdown(f"**Adaptation RAG Similarity Score:** {float(result['avg_adaptation_similarity_score']):.2f}")
                    if "avg_adaptation_action_score" in result:
                        st.markdown(f"**Adaptation Action-to-Risk Score:** {float(result['avg_adaptation_action_score']):.2f}")

                # Sector weights and vulnerabilities
                weights_csv = FILTERED_DIR / "sector_weights.csv"
                if weights_csv.exists():
                    weights_df = pd.read_csv(weights_csv)
                    weights_row = weights_df[weights_df["filename"] == f"{result['filename'].rsplit('.', 1)[0]}.txt"]
                    if not weights_row.empty:
                        st.markdown(f"""
                            <div class="result-card">
                                <strong>Sector Weights:</strong> {weights_row['weights'].iloc[0]}
                            </div>
                        """, unsafe_allow_html=True)

                vulnerabilities_csv = VULNERABILITIES_DIR / "district_vulnerabilities.csv"
                if vulnerabilities_csv.exists():
                    vulnerabilities_df = pd.read_csv(vulnerabilities_csv)
                    vulnerabilities_row = vulnerabilities_df[vulnerabilities_df["filename"] == f"{result['filename'].rsplit('.', 1)[0]}.txt"]
                    if not vulnerabilities_row.empty and "vulnerabilities" in vulnerabilities_row:
                        st.markdown(f"""
                            <div class="result-card">
                                <strong>Districts and Vulnerabilities:</strong> {vulnerabilities_row['vulnerabilities'].iloc[0]}
                            </div>
                        """, unsafe_allow_html=True)

                # Download button for results
                result_df = pd.DataFrame([result])
                csv = result_df.to_csv(index=False)
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name=f"{result['filename'].rsplit('.', 1)[0]}_classification.csv",
                    mime="text/csv"
                )

                # Display matched keywords
                if "matched_keywords" in result and result["matched_keywords"]:
                    st.markdown(f"""
                        <div class="result-card">
                            <strong>Matched Keywords:</strong><br>
                            {", ".join(result['matched_keywords'])}
                        </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()




##Hello! This is the main Streamlit app for the Climate Finance Classifier. It allows users to upload documents, processes them through text extraction, sector filtering, adaptation checking, and classification, and then displays the results in a user-friendly format. The app also includes progress indicators and error handling to ensure a smooth user experience.