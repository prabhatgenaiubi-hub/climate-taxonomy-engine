import pandas as pd
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DISTRICTS_FILE = PROJECT_ROOT / "data" / "adaptation_maps" / "districts.xlsx"
CHVA_FILE = PROJECT_ROOT / "data" / "adaptation_maps" / "all_district_chva.xlsx"
FILTERED_DIR = PROJECT_ROOT / "data" / "filtered"
OUTPUT_DIR = PROJECT_ROOT / "data" / "vulnerabilities"

def load_districts():
    try:
        df = pd.read_excel(DISTRICTS_FILE)
        if "district" not in df.columns:
            raise KeyError("Column 'district' not found in districts.xlsx")
        districts = []
        for d in df["district"].str.lower().str.strip():
            districts.extend([name.strip() for name in d.split("/")])
        return list(set(districts))
    except Exception as e:
        print(f"❌ Failed to load districts: {e}")
        return []

def load_vulnerabilities():
    try:
        df = pd.read_excel(CHVA_FILE)
        if "district" not in df.columns:
            raise KeyError("Column 'district' not found in all_district_chva.xlsx")
        return df
    except Exception as e:
        print(f"❌ Failed to load vulnerabilities: {e}")
        return None

def map_risk_value(value):
    if pd.isna(value):
        return None
    try:
        value = int(value)
        return {3: "moderate", 4: "high", 5: "very high"}.get(value)
    except (ValueError, TypeError):
        return None

def check_districts():
    OUTPUT_DIR.mkdir(exist_ok=True)
    districts = load_districts()
    chva_df = load_vulnerabilities()
    if not districts or chva_df is None:
        print("No districts or vulnerabilities loaded. Exiting.")
        return
    
    results = []
    for filename in FILTERED_DIR.glob("*.txt"):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                text = f.read().lower()
            
            found_districts = []
            for district in districts:
                if re.search(r'\b' + re.escape(district) + r'\b', text):
                    found_districts.append(district)
            
            vulnerabilities = []
            for district in found_districts:
                # Try exact match first
                exact_match = chva_df[chva_df["district"].str.lower().str.strip() == district]
                if not exact_match.empty:
                    row = exact_match.iloc[0]
                    chva_district = row["district"]
                    risks = {}
                    for col in chva_df.columns:
                        if col.startswith("risk_"):
                            risk_value = map_risk_value(row[col])
                            if risk_value:
                                risks[col.replace("risk_", "")] = risk_value
                    if risks:
                        vulnerabilities.append({"district": chva_district, "risks": risks})
                        print(f"🔍 {district}: Found risks {risks}")
                    continue
                
                # Fallback to partial match with '/' handling
                for chva_district in chva_df["district"].str.lower().str.strip():
                    chva_names = [name.strip() for name in chva_district.split("/")]
                    if district in chva_names:
                        row = chva_df[chva_df["district"].str.lower().str.strip() == chva_district]
                        if row.empty:
                            print(f"⚠️ No vulnerabilities found for district: {district}")
                            continue
                        risks = {}
                        for col in chva_df.columns:
                            if col.startswith("risk_"):
                                risk_value = map_risk_value(row[col].iloc[0])
                                if risk_value:
                                    risks[col.replace("risk_", "")] = risk_value
                        if risks:
                            vulnerabilities.append({"district": chva_district, "risks": risks})
                            print(f"🔍 {district}: Found risks {risks} (partial match)")
            
            results.append({"filename": filename.name, "districts": found_districts, "vulnerabilities": vulnerabilities})
            print(f"📄 {filename.name}: Districts {found_districts}, Vulnerabilities {vulnerabilities}")
            
            output_path = OUTPUT_DIR / filename.name
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
        
        except Exception as e:
            print(f"❌ Failed to process {filename.name}: {e}")
    
    output_csv = OUTPUT_DIR / "district_vulnerabilities.csv"
    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Saved vulnerabilities to: {output_csv}")

if __name__ == "__main__":
    check_districts()