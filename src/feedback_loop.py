import csv
import os
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
from datasets import Dataset
import pandas as pd
from src.classify import classify_document
from src.adaptation_checker import main as main_adaptation

# Paths
FEEDBACK_LOG = Path("user_feedback_log.csv")
CORRECTION_LOG = Path("corrections_for_finetuning.csv")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "climatebert-finetuned"
TOKENIZER_PATH = PROJECT_ROOT / "models" / "tokenizer"

def initialize_feedback_log():
    if not FEEDBACK_LOG.exists():
        with open(FEEDBACK_LOG, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["file", "text", "districts", "vulnerabilities", "label", "confidence", "reason", "user_feedback", "feedback_reason"])

def log_feedback(file, text, districts, vulnerabilities, result, user_feedback, feedback_reason):
    with open(FEEDBACK_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            str(file), text[:1000], ",".join(districts), ";".join(vulnerabilities),
            result["label"], result["confidence"], result["reason"], user_feedback, feedback_reason
        ])

def log_correction(text, label):
    with open(CORRECTION_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([text, label])

def retrain_model():
    if not CORRECTION_LOG.exists():
        print("No corrections found. Skipping retraining.")
        return

    df_feedback = pd.read_csv(CORRECTION_LOG, names=["text", "label"])
    label_map = {"climate change mitigation": 0, "climate change adaptation": 1, "not climate finance": 2}
    df_feedback["label"] = df_feedback["label"].map(label_map)

    dataset = Dataset.from_pandas(df_feedback)
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=3)

    def preprocess(examples):
        return tokenizer(examples["text"], truncation=True, padding=True, max_length=512)

    dataset = dataset.map(preprocess, batched=True)
    dataset = dataset.train_test_split(test_size=0.2)

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir="../models/climatebert-retrained",
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            num_train_epochs=3,
            learning_rate=2e-5,
            weight_decay=0.01,
            save_strategy="epoch"
        ),
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        tokenizer=tokenizer
    )
    trainer.train()
    trainer.save_model(MODEL_PATH)
    print("Model retrained and saved.")

def main():
    initialize_feedback_log()
    for file in (PROJECT_ROOT / "data" / "processed").glob("*.txt"):
        print(f"\nProcessing: {file}")
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()
        districts, vulnerabilities = main_adaptation(file)
        result = classify_document(file, districts, vulnerabilities)
        
        print(f"\nFile: {file.name}")
        print(f"Districts: {', '.join(districts) if districts else 'None'}")
        print("Vulnerabilities:")
        for vuln in vulnerabilities:
            print(vuln)
        print(f"Classification: {result['label']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Reason: {result['reason']}")

        user_feedback = input("\nWould you like to [Accept], [Reject], or [Modify] the classification? ").strip().lower()
        feedback_reason = input("Please explain why (optional): ").strip()

        log_feedback(file, text, districts, vulnerabilities, result, user_feedback, feedback_reason)

        if user_feedback == "accept":
            print(f"\nFinal Output: {result['label']}")
        elif user_feedback == "reject":
            print("\nOutput rejected.")
            log_correction(text[:512], "not climate finance")  # Default to not climate finance for rejection
            retrain_model()
        elif user_feedback == "modify":
            modified_label = input("Enter the correct label (mitigation, adaptation, not climate finance): ").strip().lower()
            modified_label = f"climate change {modified_label}" if modified_label in ["mitigation", "adaptation"] else "not climate finance"
            print(f"\nFinal Output (Modified): {modified_label}")
            log_correction(text[:512], modified_label)
            retrain_model()
        else:
            print("Invalid input. Skipping feedback.")

if __name__ == "__main__":
    main()