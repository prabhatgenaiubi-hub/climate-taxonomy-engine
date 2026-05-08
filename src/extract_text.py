import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from docx import Document
import os
import glob

def _find_poppler_path():
    """Auto-detect poppler bin path on Windows under C:\\Poppler."""
    # Check if already on PATH
    import shutil
    if shutil.which("pdftoppm"):
        return None  # already available system-wide

    # Common install locations (version-agnostic glob)
    candidates = glob.glob(r"C:\Poppler\*\Library\bin") + \
                 glob.glob(r"C:\poppler*\Library\bin") + \
                 glob.glob(r"C:\Program Files\poppler*\Library\bin") + \
                 [r"C:\Poppler\Library\bin"]  # legacy flat install

    for path in candidates:
        if os.path.isfile(os.path.join(path, "pdftoppm.exe")):
            return path
    return None  # will let pdf2image raise its own informative error

POPPLER_PATH = _find_poppler_path()

def extract_text_from_docx(path):
    try:
        doc = Document(path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX: {e}")

def extract_text_from_pdf(path):
    try:
        doc = fitz.open(path)
        text = ""
        for page in doc:
            page_text = page.get_text("text")
            text += page_text
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {e}")

def extract_text_from_scanned_pdf(path):
    try:
        print("Converting PDF to images...")
        pages = convert_from_path(path, dpi=300, poppler_path=POPPLER_PATH)
        text = ""
        for idx, page in enumerate(pages):
            print(f"Running OCR on page {idx + 1}")
            text += pytesseract.image_to_string(page, lang="eng")
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from scanned PDF: {e}")

def extract_text(filepath):
    ext = os.path.splitext(filepath)[-1].lower()
    if ext == ".docx":
        return extract_text_from_docx(filepath)
    elif ext == ".pdf":
        text = extract_text_from_pdf(filepath)
        if len(text.strip()) < 100:
            print("Detected scanned PDF. Running OCR...")
            return extract_text_from_scanned_pdf(filepath)
        return text
    else:
        raise Exception(f"Unsupported file type: {ext}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(extract_text(sys.argv[1]))
    else:
        print(extract_text("../data/raw/EV_vehicle_loan.pdf"))