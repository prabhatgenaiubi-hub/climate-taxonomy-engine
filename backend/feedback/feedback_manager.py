"""
backend/feedback/feedback_manager.py
=====================================
Manages user feedback collection and triggers model retraining.
Consolidates feedback_loop.py + feedback_district.py.
"""

import csv
import logging
from pathlib import Path

import pandas as pd
from config.settings import FEEDBACK_LOG, CORRECTION_LOG, LABELED_DIR

logger = logging.getLogger(__name__)


# ─── Initialisation ──────────────────────────────────────────────────────────

def initialize_logs() -> None:
    """Create feedback/correction CSV files with headers if they don't exist."""
    LABELED_DIR.mkdir(parents=True, exist_ok=True)
    if not FEEDBACK_LOG.exists():
        with open(FEEDBACK_LOG, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "file", "text", "districts", "vulnerabilities",
                "label", "confidence", "reason",
                "user_feedback", "feedback_reason",
            ])
    if not CORRECTION_LOG.exists():
        with open(CORRECTION_LOG, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["text", "label"])


# ─── Logging ─────────────────────────────────────────────────────────────────

def log_feedback(
    file: str,
    text: str,
    districts: list[str],
    vulnerabilities: list[str],
    result: dict,
    user_feedback: str,
    feedback_reason: str,
) -> None:
    """Append a feedback row to FEEDBACK_LOG."""
    initialize_logs()
    with open(FEEDBACK_LOG, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            file, text[:1000],
            ",".join(districts),
            ";".join(vulnerabilities),
            result.get("classification", ""),
            result.get("mitigation_score", 0),
            result.get("adaptation_score", 0),
            user_feedback,
            feedback_reason,
        ])
    logger.info(f"Feedback logged for {file}: {user_feedback}")


def log_correction(text: str, correct_label: str) -> None:
    """Append a correction row to CORRECTION_LOG for future fine-tuning."""
    initialize_logs()
    with open(CORRECTION_LOG, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([text[:1000], correct_label])
    logger.info(f"Correction logged: label='{correct_label}'")


# ─── Retraining Trigger ──────────────────────────────────────────────────────

def retrain_if_ready(min_corrections: int = 10) -> bool:
    """
    Trigger retraining if enough corrections have been collected.
    Returns True if retraining was triggered, False otherwise.
    """
    if not CORRECTION_LOG.exists():
        logger.info("No correction log found. Skipping retraining.")
        return False
    df = pd.read_csv(CORRECTION_LOG)
    if len(df) < min_corrections:
        logger.info(f"Only {len(df)} corrections — need {min_corrections} to retrain.")
        return False
    from backend.ml.train_climatebert import train
    train()
    return True
