import pandas as pd
import re
from pathlib import Path

# Set project root dynamically relative to this file's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAPPING_FILE = PROJECT_ROOT / "data" / "rbi_sector_mapping.xlsx"

# Load Excel and normalize the 'Code' column
try:
    mapping_df = pd.read_excel(MAPPING_FILE, dtype={"Code": str})
    mapping_df["Code"] = mapping_df["Code"].str.zfill(5).str.strip()
except FileNotFoundError:
    print(f"❌ Mapping file not found at {MAPPING_FILE}")
    raise
except Exception as e:
    print(f"❌ Failed to load mapping file: {e}")
    raise

VALID_CODES = set(mapping_df["Code"])

def extract_bsr_code(text):
    lines = text.splitlines()
    # Direct match on same line
    for line in lines:
        match = re.search(r"BSR\s+Code(?:\s*\(Sector\))?\s*[:\-]?\s*(\d{5})", line, re.IGNORECASE)
        if match:
            return match.group(1).zfill(5)
    # Fallback: look for 5-digit code within 20 lines after 'BSR Code'
    for i, line in enumerate(lines):
        if re.search(r"BSR\s+Code(?:\s*\(Sector\))?", line, re.IGNORECASE):
            lookahead_lines = lines[i + 1 : i + 21]
            for l in lookahead_lines:
                match = re.search(r"\b(\d{5})\b", l)
                if match:
                    code_candidate = match.group(1).zfill(5)
                    if code_candidate in VALID_CODES:
                        return code_candidate
            break
    return None

def classify_sector(code):
    if not code:
        return {
            "Mitigation": "maybe",
            "Adaptation": "maybe",
            "Not_CF": "maybe",
            "Decision": "unknown",
            "Weights": {"mitigation": 2, "adaptation": 2, "not_cf": 2}
        }

    row = mapping_df[mapping_df["Code"] == code]
    if row.empty:
        return {
            "Mitigation": "maybe",
            "Adaptation": "maybe",
            "Not_CF": "maybe",
            "Decision": "not found",
            "Weights": {"mitigation": 2, "adaptation": 2, "not_cf": 2}
        }

    row = row.iloc[0]
    mitigation = str(row["Mitigation"]).strip().lower()
    adaptation = str(row["Adaptation"]).strip().lower()
    not_cf = str(row["Not_CF"]).strip().lower()
    
    weights = {
        "mitigation": 3 if mitigation == "yes" else 2 if mitigation == "maybe" else 0,
        "adaptation": 3 if adaptation == "yes" else 2 if adaptation == "maybe" else 0,
        "not_cf": 3 if not_cf == "yes" else 2 if not_cf == "maybe" else 0
    }
    
    decision = "Not under Climate Finance" if mitigation == "no" and adaptation == "no" and not_cf == "yes" else "Needs Further Analysis"
    
    return {
        "Mitigation": mitigation,
        "Adaptation": adaptation,
        "Not_CF": not_cf,
        "Decision": decision,
        "Weights": weights
    }

def analyze_file():
    OUTPUT_DIR = PROJECT_ROOT / "data" / "filtered"
    OUTPUT_DIR.mkdir(exist_ok=True)
    results = []
    for file_path in (PROJECT_ROOT / "data" / "processed").glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            bsr_code = extract_bsr_code(text)
            result = classify_sector(bsr_code)
            
            if result["Decision"] == "Not under Climate Finance":
                print(f"📄 {file_path.name}: Not Climate Finance (Mitigation: {result['Mitigation']}, Adaptation: {result['Adaptation']}, Not_CF: {result['Not_CF']})")
                results.append({
                    "filename": file_path.name,
                    "bsr_code": bsr_code,
                    "decision": result["Decision"],
                    "label": "Unrelated",
                    "weights": result["Weights"]
                })
                continue
            
            output_path = OUTPUT_DIR / file_path.name
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            results.append({
                "filename": file_path.name,
                "bsr_code": bsr_code,
                "decision": result["Decision"],
                "label": "Proceed",
                "weights": result["Weights"]
            })
            print(f"📄 {file_path.name}: Proceed for further analysis (Weights: {result['Weights']})")
        
        except Exception as e:
            print(f"❌ Failed to process {file_path.name}: {e}")
    
    output_csv = OUTPUT_DIR / "sector_weights.csv"
    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Saved weights to: {output_csv}")

if __name__ == "__main__":
    analyze_file()