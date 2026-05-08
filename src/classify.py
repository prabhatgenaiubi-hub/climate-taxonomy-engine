import torch
from transformers import pipeline, AutoTokenizer
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from pathlib import Path
import pandas as pd
import pickle
import logging
import os
import re
import numpy as np
import json
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD_RAG = 0.25
CLIMATE_KEYWORD_THRESHOLD = 0.1
KEYWORD_ACTION_THRESHOLD = 0.3
FINAL_CLASSIFICATION_THRESHOLD = 1.4
FUZZY_MATCH_THRESHOLD = 0.7

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = str(PROJECT_ROOT / "models" / "distilroberta-base-climate-f")
VECTOR_DB_DIR = PROJECT_ROOT / "vector_db"
VULNERABILITIES_DIR = PROJECT_ROOT / "data" / "vulnerabilities"
OUTPUT_DIR = PROJECT_ROOT / "data" / "classified"

device = "cuda" if torch.cuda.is_available() else "cpu"
os.environ["HF_HUB_OFFLINE"] = "True"

MITIGATION_KEYWORDS = [
    "renewable", "solar", "solar pv", "solar rooftop", "wind", "hydropower", "geothermal", "bioenergy",
    "bio-gas", "biomass", "biogas", "tidal-energy", "wave-energy", "clean-energy", "low-carbon", "smart-grid", "battery-storage", "grid-integration", "advanced-metering",
    "green-buildings", "energy-efficient", "insulation-upgrade",
    "green-roof", "cool-roofing", "zero-carbon", "sustainable", "heat-pump",
    "emission-reduction", "carbon-capture", "carbon-capture-and-storage", "carbon-sequestration",
    "low-carbon", "decarbonization", "clean-fuel",
    "sustainable-material", "biodegradable",
    "public-transport", "green-vehicles", "electric-vehicle", "hybrid-vehicle", "electric bus", "electric car", "electric two-wheeler", "EV charging station",
    "non-motorized transport", "bicycle sharing", "fleet electrification", "rail electrification", "clean shipping", "biofuel", "charging infrastructure for ev",
    "sustainable agriculture", "organic farming", "precision agriculture", "conservation tillage", "no-till farming",
    "afforestation", "reforestation", "forest management", "agroforestry", "soil carbon enhancement",
    "fertilizer efficiency", "methane capture in livestock", "cover cropping",
    "waste minimization", "waste recycling", "industrial recycling", "metal recycling", "plastic recycling", "composting", "methane capture from landfills",
    "resource efficiency", "circular economy project",
    "energy efficient water pumping", "low energy desalination", "water treatment plant with energy recovery",
    "green bonds", "low-carbon investment", "climate change mitigation finance", "green loans",
    "green technology", "clean technology", "green hydrogen", "carbon offset", "carbon credit project", "energy audit", "low emissions supply chain", "sustainable procurement",
    "renewable energy certificate", "fuel cell", "hydrogen vehicle",
]
ADAPTATION_KEYWORDS = [
    "climate resilience", "climate adaptation", "adaptation measures", "vulnerability assessment",
    "climate proofing", "disaster risk reduction", "flood protection", "flood management", "flood forecasting", "urban drainage", "stormwater management", "wetland restoration", "levee construction",
    "rainwater harvesting", "groundwater recharge", "aquifer management", "drought management", "water conservation", "drought contingency",
    "watershed development", "micro-irrigation", "drip irrigation", "sprinkler irrigation", "water recycling", "desalination for adaptation",
    "agricultural resilience", "climate resilient crops", "drought-resistant crops", "heat tolerant crop varieties",
    "livestock shelter", "agroforestry for adaptation", "mulching for soil moisture", "integrated pest management",
    "livelihood diversification", "community-based adaptation", "social safety nets for climate",
    "educational campaigns for adaptation", "public awareness for climate risks",
    "heatwave preparedness", "heat action plan", "urban heat management", "cooling centers", "coldwave shelter", "early warning systems", "cyclone shelter construction",
    "coastal protection", "storm surge barriers", "coastal ecosystem restoration",
    "landslide mitigation", "slope stabilization", "slope vegetation",
    "weather forecasting system", "early warning technology",
    "infrastructure resilience", "resilient construction", "retrofitting for climate resilience", "emergency response planning", "critical infrastructure protection",
    "water resilient housing", "telecom network climate adaptation", "energy grid climate adaptation",
    "watershed management", "ecosystem-based adaptation", "biodiversity corridor", "reforestation for adaptation", "nature based solutions",
    "climate resilient sanitation", "wastewater management for adaptation", "flood-proof sewage system",
    "climate resilient storage", "heat/flood-resilient warehouse", "crop storage adaptation"
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

def cosine_sim(a, b):
    a, b = np.array(a), np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def load_vector_store_and_embeddings():
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": device},
            cache_folder=str(Path.home() / ".cache" / "huggingface" / "hub")
        )
        vector_store = FAISS.load_local(
            str(VECTOR_DB_DIR / "index.faiss"),
            embeddings,
            allow_dangerous_deserialization=True
        )
        with open(VECTOR_DB_DIR / "store.pkl", "rb") as f:
            documents = pickle.load(f)
        return vector_store, embeddings, documents
    except Exception as e:
        logger.error(f"Failed to load vector store: {e}")
        raise

def fuzzy_match(kw, segment):
    kw_clean = re.sub(r"[^\w\s]", "", kw.lower()).strip()
    segment_clean = re.sub(r"[^\w\s]", "", segment.lower()).strip()
    similarity = SequenceMatcher(None, segment_clean, kw_clean).ratio()
    if similarity >= FUZZY_MATCH_THRESHOLD:
        logger.info(f"Fuzzy match: '{kw}' ~ '{segment_clean[:80]}...' (similarity: {similarity:.2f})")
        return True
    return False

def extract_keyword_scores(text, risks):
    mitigation_score = 0.0
    adaptation_score_base = 0.0
    matched_keywords = []
    matched_actions = []

    for kw in MITIGATION_KEYWORDS:
        if kw in text or fuzzy_match(kw, text):
            mitigation_score += 0.2
            matched_keywords.append(f"[MIT] {kw}")

    for kw in ADAPTATION_KEYWORDS:
        if kw in text or fuzzy_match(kw, text):
            adaptation_score_base += 0.2
            matched_keywords.append(f"[ADAPT] {kw}")

    action_score = 0.0
    for action, details in ACTIONS_TO_RISK.items():
        if details["risk"] in risks or details["risk"] in ["all", "extreme weather"]:
            if action in text or fuzzy_match(action, text):
                score = details["score"]
                action_score += score
                matched_keywords.append(f"[ACTION-{details['risk']}] {action} ({score})")
                matched_actions.append(action)

    return mitigation_score, adaptation_score_base + action_score, matched_keywords, matched_actions

def tokenize(text, tokenizer, max_tokens=512, overlap=10):
    tokens = tokenizer.encode(text, add_special_tokens=False)
    segments = []
    for i in range(0, len(tokens), max_tokens - overlap):
        chunk = tokens[i:i + max_tokens]
        decoded = tokenizer.decode(chunk)
        if decoded.strip():
            segments.append(decoded)
    return segments or [text[:512]]

def parse_classifier_output(output):
    if isinstance(output, list):
        if all(isinstance(item, dict) for item in output):
            return next((x["score"] for x in output if x.get("label") == "LABEL_1"), 0.0)
        elif all(isinstance(item, list) for item in output):
            return next((x["score"] for x in output[0] if x.get("label") == "LABEL_1"), 0.0)
    elif isinstance(output, dict) and "label" in output:
        return output["score"] if output["label"] == "LABEL_1" else 0.0
    return 0.0

def classify_single_file(input_filename):
    classifier = pipeline("text-classification", model=MODEL_DIR, tokenizer=MODEL_DIR, device=0 if device == "cuda" else -1)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    vector_store, embeddings, _ = load_vector_store_and_embeddings()
    if vector_store is None:
        raise RuntimeError(f"Failed to load vector store from '{VECTOR_DB_DIR}'. Check that 'index.faiss' and 'store.pkl' exist in that directory.")
    with open(VULNERABILITIES_DIR / input_filename, "r", encoding="utf-8") as f:
        text = f.read()
    vul_df = pd.read_csv(VULNERABILITIES_DIR / "district_vulnerabilities.csv")
    if "filename" not in vul_df.columns:
        vul_df.columns = [c.strip().lower() for c in vul_df.columns]
    risks = []
    row = vul_df[vul_df["filename"] == input_filename]
    if not row.empty:
        try:
            data = eval(row.iloc[0]["vulnerabilities"])
            for v in data:
                if "risks" in v:
                    risks.extend(v["risks"].keys())
        except:
            pass
    segments = tokenize(text, tokenizer)

    weights_df = pd.read_csv(VULNERABILITIES_DIR.parent / "filtered" / "sector_weights.csv")
    if "filename" not in weights_df.columns:
        weights_df.columns = [c.strip().lower() for c in weights_df.columns]
    row = weights_df[weights_df["filename"] == input_filename]
    weights = eval(row.iloc[0]["weights"]) if not row.empty else {}
    mit_weight = weights.get("mitigation", 2.0)
    adapt_weight = weights.get("adaptation", 2.0)

    scores = {"mit_kw": [], "mit_sim": [], "adapt_kw": [], "adapt_sim": [], "adapt_action": []}
    matched_keywords_list = []  # To store matched keywords per segment
    print("\n===== Segment Analysis =====\n")
    for idx, segment in enumerate(segments):
        seg_mit, seg_adapt, matched_keywords, matched_actions = extract_keyword_scores(segment, risks)
        matched_keywords_list.append(matched_keywords)  # Store per segment
        seg_adapt_base = seg_adapt - sum(ACTIONS_TO_RISK.get(a, {"score":0})["score"] for a in matched_actions)
        total_score = seg_mit + seg_adapt
        if total_score < CLIMATE_KEYWORD_THRESHOLD:
            continue
        emb = embeddings.embed_query(segment)
        mitigation_docs = vector_store.similarity_search(segment, k=7)
        mitigation_scores = [cosine_sim(emb, embeddings.embed_query(doc.page_content)) for doc in mitigation_docs]
        mit_sim = max([s for s in mitigation_scores if s > SIMILARITY_THRESHOLD_RAG] or [0]) if seg_mit > 0 else 0.0
        adaptation_docs = vector_store.similarity_search(segment, k=7)
        adaptation_scores = [cosine_sim(emb, embeddings.embed_query(doc.page_content)) for doc in adaptation_docs]
        adapt_sim = max([s for s in adaptation_scores if s > SIMILARITY_THRESHOLD_RAG] or [0])
        clf_raw = classifier(segment, truncation=True, max_length=512)
        clf_score = parse_classifier_output(clf_raw)
        scores["mit_kw"].append(clf_score if seg_mit > 0 else 0)
        scores["mit_sim"].append(mit_sim)
        scores["adapt_kw"].append(seg_adapt_base)
        scores["adapt_sim"].append(adapt_sim)
        scores["adapt_action"].append(sum(ACTIONS_TO_RISK.get(a, {"score": 0})["score"] for a in matched_actions))
        print(f"Segment {idx+1}:")
        print(f"Text: {segment.strip()[:300]}...")
        print(f"Matched Keywords: {matched_keywords}")
        print(f"Mitigation Clf Score: {clf_score:.3f}, Similarity: {mit_sim:.3f}")
        print(f"Adaptation Score: {seg_adapt:.3f}, Similarity: {adapt_sim:.3f}, Actions: {matched_actions}")
        print("---------------------------")

    final_mit_score = mit_weight * (np.mean(scores["mit_kw"]) + np.mean(scores["mit_sim"])) if scores["mit_kw"] else 0.0
    final_adapt_score = adapt_weight * (np.mean(scores["adapt_kw"]) + np.mean(scores["adapt_sim"]) + np.mean(scores["adapt_action"])) if scores["adapt_kw"] else 0.0
    all_matched_keywords = []
    for segment_keywords in matched_keywords_list:
        all_matched_keywords.extend(segment_keywords)
    result = {
        "filename": input_filename,
        "classification": "Not Climate Finance",
        "mitigation_score": final_mit_score,
        "adaptation_score": final_adapt_score,
        "sector_mit_weight": mit_weight,
        "sector_adapt_weight": adapt_weight,
        "kw_avg_mitigation_score": np.mean(scores["mit_kw"]) if scores["mit_kw"] else 0,
        "kw_avg_adaptation_score": np.mean(scores["adapt_kw"]) if scores["adapt_kw"] else 0,
        "avg_mitigation_similarity_score": np.mean(scores["mit_sim"]) if scores["mit_sim"] else 0,
        "avg_adaptation_similarity_score": np.mean(scores["adapt_sim"]) if scores["adapt_sim"] else 0,
        "avg_adaptation_action_score": np.mean(scores["adapt_action"]) if scores["adapt_action"] else 0,
        "matched_keywords": all_matched_keywords
    }
    mit_flag = final_mit_score > FINAL_CLASSIFICATION_THRESHOLD
    adapt_flag = final_adapt_score > FINAL_CLASSIFICATION_THRESHOLD
    if mit_flag and adapt_flag:
        result["classification"] = "Both Mitigation and Adaptation"
    elif mit_flag:
        result["classification"] = "Mitigation"
    elif adapt_flag:
        result["classification"] = "Adaptation"
    print("\n===== Final Classification =====")
    print(f"Mitigation Score: {final_mit_score:.3f} (weight: {mit_weight})")
    print(f"Adaptation Score: {final_adapt_score:.3f} (weight: {adapt_weight})")
    print(f"→ Classification: {result['classification']}")
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_csv = OUTPUT_DIR / "classifications.csv"
    if out_csv.exists():
        try:
            prev = pd.read_csv(out_csv)
            if "filename" not in [col.lower() for col in prev.columns]:
                prev.columns = [c.strip().lower() for c in prev.columns]
            prev = prev[prev["filename"] != input_filename]
        except Exception as e:
            logger.warning(f"Error reading existing classification CSV: {e}")
            prev = pd.DataFrame()
    else:
        prev = pd.DataFrame()
    try:
        final_df = pd.concat([prev, pd.DataFrame([result])], ignore_index=True)
        final_df.to_csv(out_csv, index=False)
        logger.info(f"Saved classification result to {out_csv}")
    except Exception as e:
        logger.error(f"Error writing classification CSV: {e}")
    return result

def classify_loan():
    results = []
    for fname in VULNERABILITIES_DIR.glob("*.txt"):
        res = classify_single_file(fname.name)
        if res:
            results.append(res)
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(classify_single_file(sys.argv[1]))
    else:
        for r in classify_loan():
            print(r)