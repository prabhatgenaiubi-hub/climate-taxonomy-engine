import os
import fitz  # PyMuPDF
import ocrmypdf

RAW_DIR = "../data/raw"
OCR_DIR = "../data/ocr_pdfs"
OUT_DIR = "../data/processed"

def ocr_pdf(input_path, output_path):
    print(f"🔍 OCR: {input_path} → {output_path}")
    ocrmypdf.ocr(input_path, output_path, deskew=True, force_ocr=True)

def extract_text_from_pdf(path):
    print(f"📄 Extracting text from: {path}")
    text = ""
    doc = fitz.open(path)
    for page in doc:
        text += page.get_text()
    return text

def process_all_documents():
    for filename in os.listdir(RAW_DIR):
        if not filename.lower().endswith(".pdf"):
            continue

        input_path = os.path.join(RAW_DIR, filename)
        clean_name = os.path.splitext(filename)[0]

        ocr_output_path = os.path.join(OCR_DIR, f"{clean_name}_ocr.pdf")
        txt_output_path = os.path.join(OUT_DIR, f"{clean_name}.txt")

        try:
            # Step 1: OCR the scanned PDF
            ocr_pdf(input_path, ocr_output_path)

            # Step 2: Extract text from OCR'd PDF
            text = extract_text_from_pdf(ocr_output_path)

            # Step 3: Save text to .txt
            with open(txt_output_path, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"✅ Saved extracted text to: {txt_output_path}\n")

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")

if __name__ == "__main__":
    process_all_documents()