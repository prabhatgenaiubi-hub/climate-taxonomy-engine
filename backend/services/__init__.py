# backend.services package
from backend.services.document_processor import extract_text, process_uploaded_file
from backend.services.sector_filter import extract_bsr_code, classify_sector, save_sector_weights
from backend.services.adaptation_checker import check_districts
from backend.services.classifier import classify_single_file
