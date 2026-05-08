import torch
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from transformers import AutoTokenizer
import pandas as pd
import pickle
import shutil
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "documents"
VECTOR_DB_DIR = PROJECT_ROOT / "vector_db"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def clean_text(text):
    """Remove URLs and references."""
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    return text.strip()

def pre_chunk_text(text, chunk_size=2000):
    """Pre-chunk large texts to avoid tokenization errors."""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def tokenize_and_split_docs(text, tokenizer, file, max_tokens=400, overlap_tokens=80):
    """Split text into token-based segments."""
    segments = []
    for pre_chunk in pre_chunk_text(text):
        tokens = tokenizer.encode(pre_chunk, add_special_tokens=False, truncation=False)
        for i in range(0, len(tokens), max_tokens - overlap_tokens):
            segment_tokens = tokens[i:i + max_tokens]
            segment_text = tokenizer.decode(segment_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=True)
            if segment_text.strip():
                segments.append({"text": segment_text, "source": str(file)})
                logger.info(f"Segment from {file}: {len(segment_tokens)} tokens, ~{len(segment_text.split())} words")
    return segments

def process_excel_file(file_path):
    """Extract Mitigation and Adaptation columns from Excel file."""
    try:
        df = pd.read_excel(file_path, sheet_name="Sheet1")
        mitigation_text = " ".join(df["Mitigation"].dropna().astype(str).tolist())
        adaptation_text = " ".join(df["Adaptation"].dropna().astype(str).tolist())
        return clean_text(mitigation_text), clean_text(adaptation_text)
    except Exception as e:
        logger.error(f"Failed to process Excel file {file_path}: {e}")
        return "", ""

def build_vector_store():
    tokenizer = AutoTokenizer.from_pretrained("climatebert/distilroberta-base-climate-f")
    documents = []
    
    for subdir in ["mitigation_knowledge", "adaptation_knowledge"]:
        subdir_path = DOCS_DIR / subdir
        if not subdir_path.exists():
            logger.warning(f"Directory {subdir_path} does not exist. Skipping.")
            continue
        
        # Process .txt files
        for file in subdir_path.glob("*.txt"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    text = clean_text(f.read())
                    segments = tokenize_and_split_docs(text, tokenizer, file)
                    documents.extend(segments)
            except Exception as e:
                logger.error(f"Failed to process {file}: {e}")
        
        # Process .xlsx files
        for file in subdir_path.glob("*.xlsx"):
            try:
                mitigation_text, adaptation_text = process_excel_file(file)
                if subdir == "mitigation_knowledge" and mitigation_text:
                    segments = tokenize_and_split_docs(mitigation_text, tokenizer, file)
                    documents.extend(segments)
                elif subdir == "adaptation_knowledge" and adaptation_text:
                    segments = tokenize_and_split_docs(adaptation_text, tokenizer, file)
                    documents.extend(segments)
            except Exception as e:
                logger.error(f"Failed to process {file}: {e}")
        
        # Process .pdf files
        try:
            loader = PyPDFDirectoryLoader(str(subdir_path))
            pdf_docs = loader.load()
            for doc in pdf_docs:
                text = clean_text(doc.page_content)
                segments = tokenize_and_split_docs(text, tokenizer, doc.metadata.get("source", str(subdir_path)))
                documents.extend(segments)
        except Exception as e:
            logger.error(f"Failed to process PDFs in {subdir_path}: {e}")
    
    if not documents:
        logger.error("No documents found. Exiting.")
        return
    
    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
        cache_folder="C:/Users/Anand/.cache/huggingface/hub"
    )
    vector_store = FAISS.from_texts(
        texts=[doc["text"] for doc in documents],
        embedding=embeddings,
        metadatas=[{"source": doc["source"]} for doc in documents]
    )
    
    # Remove existing vector store directory
    if VECTOR_DB_DIR.exists():
        shutil.rmtree(VECTOR_DB_DIR)
        logger.info(f"Removed existing vector store directory: {VECTOR_DB_DIR}")
    
    # Create new directory and save vector store
    VECTOR_DB_DIR.mkdir(exist_ok=True)
    vector_store.save_local(str(VECTOR_DB_DIR / "index.faiss"))
    with open(VECTOR_DB_DIR / "store.pkl", "wb") as f:
        pickle.dump(documents, f)
    logger.info(f"Vector store built and saved to: {VECTOR_DB_DIR}")

if __name__ == "__main__":
    build_vector_store()