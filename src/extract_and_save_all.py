import os
from pathlib import Path
from extract_text import extract_text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

def process_all_documents():
    OUTPUT_DIR.mkdir(exist_ok=True)
    for filename in RAW_DIR.glob("*"):
        if not filename.is_file():
            continue
        print(f"\n📄 Processing: {filename.name}")
        try:
            text = extract_text(str(filename))
            clean_name = filename.stem
            output_path = OUTPUT_DIR / f"{clean_name}.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"✅ Saved extracted text to: {output_path}")
        except Exception as e:
            print(f"❌ Failed to process {filename.name}: {e}")

if __name__ == "__main__":
    process_all_documents()