# Climate Taxonomy Engine

AI-powered climate finance classification tool for Union Bank of India.
Classifies loan/investment documents as **Mitigation**, **Adaptation**, **Both**, or **Not Climate Finance** using ClimateBERT, RAG (FAISS), and district-level vulnerability mapping.

---

## 📁 Project Structure

```
climate-taxonomy-engine/
│
├── app/                          # Streamlit frontend (UI only)
│   └── main.py                   # Entry point — run this
│
├── backend/
│   ├── services/                 # Business logic
│   │   ├── document_processor.py # PDF/DOCX/TXT extraction + OCR
│   │   ├── sector_filter.py      # BSR code extraction + RBI sector mapping
│   │   ├── adaptation_checker.py # District vulnerability mapping (CHVA)
│   │   └── classifier.py         # ClimateBERT + RAG + keyword scoring
│   ├── ml/                       # ML utilities
│   │   ├── rag_engine.py         # Build/update FAISS vector store
│   │   ├── cache_model.py        # Pre-download embedding model
│   │   └── train_climatebert.py  # Fine-tune model on corrections
│   └── feedback/
│       └── feedback_manager.py   # Log user feedback, trigger retraining
│
├── config/
│   └── settings.py               # All paths, thresholds, constants (single source of truth)
│
├── models/
│   ├── distilroberta-base-climate-f/   # Primary classifier (tracked via Git LFS)
│   └── climatebert-finetuned/          # Fine-tuned model (populated after training)
│
├── data/
│   ├── raw/                      # Uploaded files
│   ├── processed/                # Extracted text
│   ├── filtered/                 # Sector-filtered docs + sector_weights.csv
│   ├── vulnerabilities/          # District risk profiles + district_vulnerabilities.csv
│   ├── classified/               # Final classifications.csv
│   ├── labeled/                  # Feedback + correction logs
│   ├── adaptation_maps/          # districts.xlsx, all_district_chva.xlsx
│   └── ocr_pdfs/                 # OCR intermediate files
│
├── documents/                    # Knowledge base for RAG
│   ├── mitigation_knowledge/
│   └── adaptation knowledge/
│
├── vector_db/                    # FAISS index (built by backend/ml/rag_engine.py)
├── assets/                       # Logos, background images
│
├── .gitattributes                # Git LFS tracking for *.safetensors
├── .gitignore
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Cache embedding model (first time only)
```bash
python -m backend.ml.cache_model
```

### 3. Build the vector store (first time or after adding knowledge docs)
```bash
python -m backend.ml.rag_engine
```

### 4. Run the app
```bash
streamlit run app/main.py
```

---

## 🔧 Key Configuration

All paths and thresholds are in **`config/settings.py`**. Edit that file to change:
- Model directories
- Data directory locations
- Classification thresholds (`FINAL_CLASSIFICATION_THRESHOLD`, etc.)
- Poppler path (auto-detected on Windows)

---

## 🤖 Fine-tuning

1. Use the app and submit feedback corrections via the UI.
2. Corrections are saved to `data/labeled/corrections_for_finetuning.csv`.
3. Once enough corrections are collected, run:
```bash
python -m backend.ml.train_climatebert
```

---

## 📌 Notes

- `models/distilroberta-base-climate-f/model.safetensors` is tracked via **Git LFS**.
- The project venv was originally created on a different machine. Create a fresh one:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
