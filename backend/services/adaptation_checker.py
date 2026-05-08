"""
backend/services/adaptation_checker.py
=======================================
Extracts district names from filtered documents and maps them to
climate vulnerability data (CHVA) to produce per-file risk profiles.
"""

import re
import pandas as pd
from pathlib import Path

from config.settings import (
    DISTRICTS_FILE, CHVA_FILE, FILTERED_DIR,
    VULNERABILITIES_DIR, DISTRICT_VULN_CSV
)


# ─── Loaders ─────────────────────────────────────────────────────────────────

def load_districts() -> list[str]:
    try:
        df = pd.read_excel(DISTRICTS_FILE)
        if "district" not in df.columns:
            raise KeyError("Column 'district' not found in districts.xlsx")
        result = []
        for d in df["district"].str.lower().str.strip():
            result.extend(name.strip() for name in d.split("/"))
        return list(set(result))
    except Exception as e:
        print(f"❌ Failed to load districts: {e}")
        return []


def load_chva() -> pd.DataFrame | None:
    try:
        df = pd.read_excel(CHVA_FILE)
        if "district" not in df.columns:
            raise KeyError("Column 'district' not found in all_district_chva.xlsx")
        return df
    except Exception as e:
        print(f"❌ Failed to load CHVA data: {e}")
        return None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _map_risk_value(value) -> str | None:
    if pd.isna(value):
        return None
    try:
        return {3: "moderate", 4: "high", 5: "very high"}.get(int(value))
    except (ValueError, TypeError):
        return None


def _extract_risks(row: pd.Series, chva_df: pd.DataFrame) -> dict:
    return {
        col.replace("risk_", ""): _map_risk_value(row[col])
        for col in chva_df.columns
        if col.startswith("risk_") and _map_risk_value(row[col])
    }


def _find_district_row(district: str, chva_df: pd.DataFrame) -> pd.Series | None:
    chva_lower = chva_df["district"].str.lower().str.strip()
    # Exact match
    exact = chva_df[chva_lower == district]
    if not exact.empty:
        return exact.iloc[0]
    # Partial "/" match
    for raw_name in chva_lower:
        if district in [n.strip() for n in raw_name.split("/")]:
            row = chva_df[chva_lower == raw_name]
            if not row.empty:
                return row.iloc[0]
    return None


# ─── Public API ──────────────────────────────────────────────────────────────

def get_vulnerabilities_for_text(text: str) -> list[dict]:
    """
    Given document text, return a list of dicts:
      [{"district": str, "risks": {risk_name: severity, ...}}, ...]
    """
    districts = load_districts()
    chva_df   = load_chva()
    if not districts or chva_df is None:
        return []

    found = [
        d for d in districts
        if re.search(r'\b' + re.escape(d) + r'\b', text.lower())
    ]
    results = []
    for district in found:
        row = _find_district_row(district, chva_df)
        if row is not None:
            risks = _extract_risks(row, chva_df)
            if risks:
                results.append({"district": row["district"], "risks": risks})
    return results


def check_districts() -> None:
    """
    Batch: scan all filtered .txt files, extract district vulnerabilities,
    write per-file .txt copies to VULNERABILITIES_DIR, and save CSV summary.
    """
    VULNERABILITIES_DIR.mkdir(parents=True, exist_ok=True)
    districts = load_districts()
    chva_df   = load_chva()
    if not districts or chva_df is None:
        print("No districts or CHVA data loaded. Exiting.")
        return

    records = []
    for filepath in FILTERED_DIR.glob("*.txt"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read().lower()

            found = [
                d for d in districts
                if re.search(r'\b' + re.escape(d) + r'\b', text)
            ]
            vulnerabilities = []
            for district in found:
                row = _find_district_row(district, chva_df)
                if row is not None:
                    risks = _extract_risks(row, chva_df)
                    if risks:
                        vulnerabilities.append({"district": row["district"], "risks": risks})

            records.append({
                "filename":        filepath.name,
                "districts":       found,
                "vulnerabilities": vulnerabilities,
            })
            # Mirror file to vulnerabilities dir
            (VULNERABILITIES_DIR / filepath.name).write_text(text, encoding="utf-8")
            print(f"📄 {filepath.name}: districts={found}")
        except Exception as e:
            print(f"❌ Failed to process {filepath.name}: {e}")

    pd.DataFrame(records).to_csv(DISTRICT_VULN_CSV, index=False)
    print(f"✅ Saved vulnerabilities to: {DISTRICT_VULN_CSV}")
