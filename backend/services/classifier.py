"""
backend/services/classifier.py
================================
Climate finance classification service.
Combines keyword scoring, RAG similarity, and ClimateBERT inference
to classify a document as Mitigation / Adaptation / Both / Not CF.
"""

import re
import pickle
import logging
import numpy as np
from difflib import SequenceMatcher
from pathlib import Path

import torch
import pandas as pd
from transformers import pipeline, AutoTokenizer
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from config.settings import (
    DISTILROBERTA_MODEL_DIR, VECTOR_DB_DIR, VULNERABILITIES_DIR,
    CLASSIFIED_DIR, FILTERED_DIR, EMBEDDING_MODEL_NAME, EMBEDDING_CACHE_DIR,
    SIMILARITY_THRESHOLD_RAG, CLIMATE_KEYWORD_THRESHOLD,
    FINAL_CLASSIFICATION_THRESHOLD, FUZZY_MATCH_THRESHOLD,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ─── Keyword Lists (imported from original classify.py — unchanged) ───────────
MITIGATION_KEYWORDS = [
    "renewable", "solar", "solar pv", "solar rooftop", "wind", "hydropower",
    "geothermal", "bioenergy", "bio-gas", "biomass", "biogas", "tidal-energy",
    "wave-energy", "clean-energy", "low-carbon", "smart-grid", "battery-storage",
    "grid-integration", "advanced-metering", "green-buildings", "energy-efficient",
    "insulation-upgrade", "green-roof", "cool-roofing", "zero-carbon", "sustainable",
    "heat-pump", "emission-reduction", "carbon-capture",
    "carbon-capture-and-storage", "carbon-sequestration", "decarbonization",
    "clean-fuel", "sustainable-material", "biodegradable", "public-transport",
    "green-vehicles", "electric-vehicle", "hybrid-vehicle", "electric bus",
    "electric car", "electric two-wheeler", "EV charging station",
    "non-motorized transport", "bicycle sharing", "fleet electrification",
    "rail electrification", "clean shipping", "biofuel",
    "charging infrastructure for ev", "sustainable agriculture", "organic farming",
    "precision agriculture", "conservation tillage", "no-till farming",
    "afforestation", "reforestation", "forest management", "agroforestry",
    "soil carbon enhancement", "fertilizer efficiency",
    "methane capture in livestock", "cover cropping", "waste minimization",
    "waste recycling", "industrial recycling", "metal recycling",
    "plastic recycling", "composting", "methane capture from landfills",
    "resource efficiency", "circular economy project",
    "energy efficient water pumping", "low energy desalination",
    "water treatment plant with energy recovery", "green bonds",
    "low-carbon investment", "climate change mitigation finance", "green loans",
    "green technology", "clean technology", "green hydrogen", "carbon offset",
    "carbon credit project", "energy audit", "low emissions supply chain",
    "sustainable procurement", "renewable energy certificate", "fuel cell",
    "hydrogen vehicle",
]

ADAPTATION_KEYWORDS = [
    "climate resilience", "climate adaptation", "adaptation measures",
    "vulnerability assessment", "climate proofing", "disaster risk reduction",
    "flood protection", "flood management", "flood forecasting", "urban drainage",
    "stormwater management", "wetland restoration", "levee construction",
    "rainwater harvesting", "groundwater recharge", "aquifer management",
    "drought management", "water conservation", "drought contingency",
    "watershed development", "micro-irrigation", "drip irrigation",
    "sprinkler irrigation", "water recycling", "desalination for adaptation",
    "agricultural resilience", "climate resilient crops", "drought-resistant crops",
    "heat tolerant crop varieties", "livestock shelter",
    "agroforestry for adaptation", "mulching for soil moisture",
    "integrated pest management", "livelihood diversification",
    "community-based adaptation", "social safety nets for climate",
    "educational campaigns for adaptation", "public awareness for climate risks",
    "heatwave preparedness", "heat action plan", "urban heat management",
    "cooling centers", "coldwave shelter", "early warning systems",
    "cyclone shelter construction", "coastal protection", "storm surge barriers",
    "coastal ecosystem restoration", "landslide mitigation",
    "slope stabilization", "slope vegetation", "weather forecasting system",
    "early warning technology", "infrastructure resilience",
    "resilient construction", "retrofitting for climate resilience",
    "emergency response planning", "critical infrastructure protection",
    "water resilient housing", "telecom network climate adaptation",
    "energy grid climate adaptation", "watershed management",
    "ecosystem-based adaptation", "biodiversity corridor",
    "reforestation for adaptation", "nature based solutions",
    "climate resilient sanitation", "wastewater management for adaptation",
    "flood-proof sewage system", "climate resilient storage",
    "heat/flood-resilient warehouse", "crop storage adaptation",
]

ACTIONS_TO_RISK = {
    "groundwater recharge": {"risk": "groundwater", "score": 0.85},
    "rainwater harvesting": {"risk": "groundwater", "score": 0.80},
    "aquifer storage and recovery": {"risk": "groundwater", "score": 0.85},
    "restrictions on groundwater abstraction": {"risk": "groundwater", "score": 0.75},
    "advanced water metering": {"risk": "groundwater", "score": 0.70},
    "groundwater quality monitoring": {"risk": "groundwater", "score": 0.75},
    "sustainable irrigation abstraction": {"risk": "groundwater", "score": 0.75},
    "building insulation upgrade": {"risk": "coldwave", "score": 0.80},
    "heating system modernization": {"risk": "coldwave", "score": 0.75},
    "distribution of cold-weather shelters": {"risk": "coldwave", "score": 0.75},
    "outreach for coldwave preparedness": {"risk": "coldwave", "score": 0.70},
    "winterization of transport vehicles": {"risk": "coldwave", "score": 0.65},
    "cool roofing installation": {"risk": "heatwave", "score": 0.80},
    "urban greening (tree plantation, parks)": {"risk": "heatwave", "score": 0.85},
    "shaded bus stations and waiting areas": {"risk": "heatwave", "score": 0.70},
    "community cooling centers": {"risk": "heatwave", "score": 0.75},
    "passive building cooling": {"risk": "heatwave", "score": 0.80},
    "workplace heat action plans": {"risk": "heatwave", "score": 0.75},
    "telecom/data network cooling resilience": {"risk": "heatwave", "score": 0.70},
    "micro-irrigation (drip, sprinkler)": {"risk": "drought", "score": 0.80},
    "cultivation of drought-resistant crops": {"risk": "drought", "score": 0.85},
    "critical infrastructure water buffers": {"risk": "drought", "score": 0.75},
    "expansion of farm ponds/tanks": {"risk": "drought", "score": 0.75},
    "urban drought contingency water plans": {"risk": "drought", "score": 0.70},
    "retrofit roads/bridges for flooding": {"risk": "flood", "score": 0.75},
    "city flood early warning systems": {"risk": "flood", "score": 0.90},
    "elevated warehouses and godowns": {"risk": "flood", "score": 0.80},
    "expansion of stormwater drainage": {"risk": "flood", "score": 0.85},
    "evacuation planning for coastal ports": {"risk": "flood", "score": 0.80},
    "wetland/riverbank restoration": {"risk": "flood", "score": 0.85},
    "flood-proofing telecommunication assets": {"risk": "flood", "score": 0.75},
    "cyclone shelters construction": {"risk": "cyclone", "score": 0.85},
    "coastal mangrove plantation": {"risk": "cyclone", "score": 0.80},
    "strengthening port structures": {"risk": "cyclone", "score": 0.80},
    "port contingency plans for cyclone": {"risk": "cyclone", "score": 0.75},
    "resilient power/telecom towers": {"risk": "cyclone", "score": 0.85},
    "infrastructure seismic retrofitting": {"risk": "earthquake", "score": 0.90},
    "earthquake-resistant building codes": {"risk": "earthquake", "score": 0.90},
    "secure data center design": {"risk": "earthquake", "score": 0.80},
    "public transport seismic shutdown protocols": {"risk": "earthquake", "score": 0.75},
    "slope stabilization": {"risk": "landslide", "score": 0.85},
    "vegetation/afforestation on slopes": {"risk": "landslide", "score": 0.80},
    "landslide warning systems for highways/rail": {"risk": "landslide", "score": 0.75},
    "terrain risk mapping for transport routes": {"risk": "landslide", "score": 0.70},
    "stormwater control in hilly settlements": {"risk": "landslide", "score": 0.75},
    "smart highway lighting for fog": {"risk": "fog", "score": 0.65},
    "fog warning systems at airports": {"risk": "fog", "score": 0.75},
    "port fog navigation aids": {"risk": "fog", "score": 0.70},
    "windbreak tree planting on roads/crops": {"risk": "windhazard", "score": 0.75},
    "retrofit of transmission and distribution lines": {"risk": "windhazard", "score": 0.85},
    "wind-resilient signages/telecom towers": {"risk": "windhazard", "score": 0.80},
    "crop staking/bracing": {"risk": "windhazard", "score": 0.70},
    "shelterbelts for dust mitigation": {"risk": "duststorm", "score": 0.80},
    "air filtration in transport/warehousing": {"risk": "duststorm", "score": 0.75},
    "early warning for dust events": {"risk": "duststorm", "score": 0.70},
    "snow-resilient warehousing": {"risk": "snowfall", "score": 0.75},
    "road snow clearance machinery": {"risk": "snowfall", "score": 0.80},
    "heating/insulation upgrades for public buildings": {"risk": "snowfall", "score": 0.75},
    "rail network snow management protocols": {"risk": "snowfall", "score": 0.75},
    "hail netting for crops/orchards": {"risk": "hailstorm", "score": 0.85},
    "hail-resistant windows/roofing": {"risk": "hailstorm", "score": 0.80},
    "weather monitoring for hail alert": {"risk": "hailstorm", "score": 0.75},
    "lightning rods for key infrastructure": {"risk": "lightning", "score": 0.85},
    "lightning warning systems on industrial sites": {"risk": "lightning", "score": 0.80},
    "training/community warnings for lightning": {"risk": "lightning", "score": 0.75},
    "storm shelters for vulnerable communities": {"risk": "thunderstorm", "score": 0.80},
    "resilient design of telecom/power infrastructure": {"risk": "thunderstorm", "score": 0.80},
    "early warning and public response campaigns": {"risk": "thunderstorm", "score": 0.75},
    "multi-hazard early warning system": {"risk": "all", "score": 0.90},
    "adaptive supply chain planning": {"risk": "extreme weather", "score": 0.75},
    "digital weather integration in logistics": {"risk": "all", "score": 0.70},
    "resilient healthcare infrastructure": {"risk": "extreme weather", "score": 0.85},
    "satellite/agro-data for disaster planning": {"risk": "all", "score": 0.80},
    "climate adaptation R&D investment": {"risk": "all", "score": 0.75},
}


# ─── Utility Functions ───────────────────────────────────────────────────────

def _cosine_sim(a, b) -> float:
    a, b = np.array(a), np.array(b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / norm) if norm else 0.0


def _fuzzy_match(keyword: str, segment: str) -> bool:
    kw_clean  = re.sub(r"[^\w\s]", "", keyword.lower()).strip()
    seg_clean = re.sub(r"[^\w\s]", "", segment.lower()).strip()
    return SequenceMatcher(None, seg_clean, kw_clean).ratio() >= FUZZY_MATCH_THRESHOLD


def _extract_keyword_scores(text: str, risks: list) -> tuple:
    mit_score = adapt_score = 0.0
    matched, actions = [], []
    for kw in MITIGATION_KEYWORDS:
        if kw in text or _fuzzy_match(kw, text):
            mit_score += 0.2
            matched.append(f"[MIT] {kw}")
    for kw in ADAPTATION_KEYWORDS:
        if kw in text or _fuzzy_match(kw, text):
            adapt_score += 0.2
            matched.append(f"[ADAPT] {kw}")
    action_score = 0.0
    for action, meta in ACTIONS_TO_RISK.items():
        if meta["risk"] in risks or meta["risk"] in ("all", "extreme weather"):
            if action in text or _fuzzy_match(action, text):
                action_score += meta["score"]
                matched.append(f"[ACTION-{meta['risk']}] {action} ({meta['score']})")
                actions.append(action)
    return mit_score, adapt_score + action_score, matched, actions


def _tokenize(text: str, tokenizer, max_tokens: int = 512, overlap: int = 10) -> list[str]:
    tokens = tokenizer.encode(text, add_special_tokens=False)
    segments = []
    for i in range(0, len(tokens), max_tokens - overlap):
        decoded = tokenizer.decode(tokens[i: i + max_tokens])
        if decoded.strip():
            segments.append(decoded)
    return segments or [text[:512]]


def _parse_classifier_output(output) -> float:
    if isinstance(output, list):
        items = output[0] if isinstance(output[0], list) else output
        return next((x["score"] for x in items if x.get("label") == "LABEL_1"), 0.0)
    if isinstance(output, dict):
        return output["score"] if output.get("label") == "LABEL_1" else 0.0
    return 0.0


# ─── Model / Vector Store Loading ────────────────────────────────────────────

def _load_resources():
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": DEVICE},
        cache_folder=EMBEDDING_CACHE_DIR,
    )
    vector_store = FAISS.load_local(
        str(VECTOR_DB_DIR / "index.faiss"),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    return vector_store, embeddings


# ─── Public API ──────────────────────────────────────────────────────────────

def classify_single_file(input_filename: str) -> dict | None:
    """
    Classify a single file (by name inside VULNERABILITIES_DIR).
    Returns a result dict with classification, scores, and matched keywords.
    """
    clf        = pipeline("text-classification", model=DISTILROBERTA_MODEL_DIR,
                           tokenizer=DISTILROBERTA_MODEL_DIR,
                           device=0 if DEVICE == "cuda" else -1)
    tokenizer  = AutoTokenizer.from_pretrained(DISTILROBERTA_MODEL_DIR)
    vector_store, embeddings = _load_resources()

    text_path = VULNERABILITIES_DIR / input_filename
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Load district vulnerability risks
    risks = []
    if VULNERABILITIES_DIR.parent.joinpath("vulnerabilities", "district_vulnerabilities.csv").exists():
        vul_df = pd.read_csv(VULNERABILITIES_DIR / "district_vulnerabilities.csv")
        vul_df.columns = [c.strip().lower() for c in vul_df.columns]
        row = vul_df[vul_df["filename"] == input_filename]
        if not row.empty:
            try:
                for v in eval(row.iloc[0]["vulnerabilities"]):
                    risks.extend(v.get("risks", {}).keys())
            except Exception:
                pass

    # Load sector weights
    mit_weight = adapt_weight = 2.0
    if FILTERED_DIR.joinpath("sector_weights.csv").exists():
        w_df = pd.read_csv(FILTERED_DIR / "sector_weights.csv")
        w_df.columns = [c.strip().lower() for c in w_df.columns]
        w_row = w_df[w_df["filename"] == input_filename]
        if not w_row.empty:
            weights = eval(w_row.iloc[0]["weights"])
            mit_weight    = weights.get("mitigation", 2.0)
            adapt_weight  = weights.get("adaptation", 2.0)

    segments = _tokenize(text, tokenizer)
    scores   = {"mit_kw": [], "mit_sim": [], "adapt_kw": [], "adapt_sim": [], "adapt_action": []}
    all_keywords: list[str] = []

    for idx, segment in enumerate(segments):
        seg_mit, seg_adapt, matched, actions = _extract_keyword_scores(segment, risks)
        all_keywords.extend(matched)
        if seg_mit + seg_adapt < CLIMATE_KEYWORD_THRESHOLD:
            continue
        emb       = embeddings.embed_query(segment)
        mit_docs  = vector_store.similarity_search(segment, k=7)
        adapt_docs = vector_store.similarity_search(segment, k=7)
        mit_sims  = [_cosine_sim(emb, embeddings.embed_query(d.page_content)) for d in mit_docs]
        adp_sims  = [_cosine_sim(emb, embeddings.embed_query(d.page_content)) for d in adapt_docs]
        mit_sim   = max((s for s in mit_sims  if s > SIMILARITY_THRESHOLD_RAG), default=0.0) if seg_mit > 0 else 0.0
        adp_sim   = max((s for s in adp_sims  if s > SIMILARITY_THRESHOLD_RAG), default=0.0)
        clf_score = _parse_classifier_output(clf(segment, truncation=True, max_length=512))
        action_total = sum(ACTIONS_TO_RISK.get(a, {"score": 0})["score"] for a in actions)
        adapt_base   = seg_adapt - action_total

        scores["mit_kw"].append(clf_score if seg_mit > 0 else 0.0)
        scores["mit_sim"].append(mit_sim)
        scores["adapt_kw"].append(adapt_base)
        scores["adapt_sim"].append(adp_sim)
        scores["adapt_action"].append(action_total)

    def _avg(lst): return float(np.mean(lst)) if lst else 0.0

    final_mit   = mit_weight   * (_avg(scores["mit_kw"])   + _avg(scores["mit_sim"]))
    final_adapt = adapt_weight * (_avg(scores["adapt_kw"]) + _avg(scores["adapt_sim"]) + _avg(scores["adapt_action"]))

    label = "Not Climate Finance"
    if final_mit > FINAL_CLASSIFICATION_THRESHOLD and final_adapt > FINAL_CLASSIFICATION_THRESHOLD:
        label = "Both Mitigation and Adaptation"
    elif final_mit > FINAL_CLASSIFICATION_THRESHOLD:
        label = "Mitigation"
    elif final_adapt > FINAL_CLASSIFICATION_THRESHOLD:
        label = "Adaptation"

    result = {
        "filename":                       input_filename,
        "classification":                 label,
        "mitigation_score":               final_mit,
        "adaptation_score":               final_adapt,
        "sector_mit_weight":              mit_weight,
        "sector_adapt_weight":            adapt_weight,
        "kw_avg_mitigation_score":        _avg(scores["mit_kw"]),
        "kw_avg_adaptation_score":        _avg(scores["adapt_kw"]),
        "avg_mitigation_similarity_score": _avg(scores["mit_sim"]),
        "avg_adaptation_similarity_score": _avg(scores["adapt_sim"]),
        "avg_adaptation_action_score":    _avg(scores["adapt_action"]),
        "matched_keywords":               all_keywords,
    }

    # Persist to CSV
    CLASSIFIED_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = CLASSIFIED_DIR / "classifications.csv"
    prev = pd.read_csv(out_csv) if out_csv.exists() else pd.DataFrame()
    if not prev.empty:
        prev = prev[prev["filename"] != input_filename]
    pd.concat([prev, pd.DataFrame([result])], ignore_index=True).to_csv(out_csv, index=False)
    return result


def classify_all() -> list[dict]:
    """Classify every .txt file in VULNERABILITIES_DIR."""
    return [
        r for fp in VULNERABILITIES_DIR.glob("*.txt")
        if (r := classify_single_file(fp.name))
    ]
