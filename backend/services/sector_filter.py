"""
backend/services/sector_filter.py
==================================
Classifies a loan document's BSR sector code against the RBI mapping
to determine if the document falls under Climate Finance scope.
"""

import re
import pandas as pd
from pathlib import Path

from config.settings import (
    RBI_SECTOR_MAPPING, FILTERED_DIR, PROCESSED_DIR, SECTOR_WEIGHTS_CSV
)

# ─── Load mapping once at import time ────────────────────────────────────────
try:
    _mapping_df = pd.read_excel(RBI_SECTOR_MAPPING, dtype={"Code": str})
    _mapping_df["Code"] = _mapping_df["Code"].str.zfill(5).str.strip()
    VALID_CODES = set(_mapping_df["Code"])
except FileNotFoundError:
    raise FileNotFoundError(f"RBI sector mapping file not found: {RBI_SECTOR_MAPPING}")
except Exception as e:
    raise RuntimeError(f"Failed to load RBI sector mapping: {e}") from e


# ─── BSR Code Extraction ─────────────────────────────────────────────────────

def extract_bsr_code(text: str) -> str | None:
    """Extract 5-digit BSR sector code from document text."""
    lines = text.splitlines()
    for line in lines:
        match = re.search(
            r"BSR\s+Code(?:\s*\(Sector\))?\s*[:\-]?\s*(\d{5})",
            line, re.IGNORECASE
        )
        if match:
            return match.group(1).zfill(5)
    # Lookahead fallback
    for i, line in enumerate(lines):
        if re.search(r"BSR\s+Code(?:\s*\(Sector\))?", line, re.IGNORECASE):
            for lookahead in lines[i + 1: i + 21]:
                m = re.search(r"\b(\d{5})\b", lookahead)
                if m and m.group(1).zfill(5) in VALID_CODES:
                    return m.group(1).zfill(5)
            break
    return None


# ─── Sector Classification ───────────────────────────────────────────────────

def classify_sector(code: str | None) -> dict:
    """
    Returns a dict with Mitigation, Adaptation, Decision, and Weights
    for a given BSR code.
    """
    _default_weights = {"mitigation": 2, "adaptation": 2, "not_cf": 2}

    if not code:
        return {
            "Mitigation": "maybe", "Adaptation": "maybe", "Not_CF": "maybe",
            "Decision": "unknown", "Weights": _default_weights
        }

    row = _mapping_df[_mapping_df["Code"] == code]
    if row.empty:
        return {
            "Mitigation": "maybe", "Adaptation": "maybe", "Not_CF": "maybe",
            "Decision": "not found", "Weights": _default_weights
        }

    row = row.iloc[0]
    mitigation = str(row["Mitigation"]).strip().lower()
    adaptation  = str(row["Adaptation"]).strip().lower()
    not_cf       = str(row["Not_CF"]).strip().lower()

    weights = {
        "mitigation": 3 if mitigation == "yes" else 2 if mitigation == "maybe" else 0,
        "adaptation":  3 if adaptation  == "yes" else 2 if adaptation  == "maybe" else 0,
        "not_cf":      3 if not_cf      == "yes" else 2 if not_cf      == "maybe" else 0,
    }
    decision = (
        "Not under Climate Finance"
        if mitigation == "no" and adaptation == "no" and not_cf == "yes"
        else "Needs Further Analysis"
    )
    return {
        "Mitigation": mitigation,
        "Adaptation": adaptation,
        "Not_CF": not_cf,
        "Decision": decision,
        "Weights": weights,
    }


# ─── Persist Sector Weights ──────────────────────────────────────────────────

def save_sector_weights(filename_stem: str, bsr_code: str, sector_result: dict) -> None:
    """Append/update sector weights CSV with the result for this file."""
    import pandas as pd
    FILTERED_DIR.mkdir(parents=True, exist_ok=True)
    entry = pd.DataFrame([{
        "filename": f"{filename_stem}.txt",
        "bsr_code": bsr_code,
        "decision": sector_result["Decision"],
        "label": "Proceed",
        "weights": sector_result["Weights"],
    }])
    if SECTOR_WEIGHTS_CSV.exists():
        existing = pd.read_csv(SECTOR_WEIGHTS_CSV)
        existing = existing[existing["filename"] != f"{filename_stem}.txt"]
        entry = pd.concat([existing, entry], ignore_index=True)
    entry.to_csv(SECTOR_WEIGHTS_CSV, index=False)


# ─── Batch Analysis ──────────────────────────────────────────────────────────

def analyze_all() -> list[dict]:
    """Run sector filter over all processed .txt files."""
    results = []
    for fp in PROCESSED_DIR.glob("*.txt"):
        with open(fp, "r", encoding="utf-8") as f:
            text = f.read()
        code   = extract_bsr_code(text)
        result = classify_sector(code)
        save_sector_weights(fp.stem, code, result)
        results.append({"filename": fp.name, "bsr_code": code, **result})
        print(f"📄 {fp.name}: {result['Decision']}")
    return results
