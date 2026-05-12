"""
backend/ml/train_climatebert.py
================================
Fine-tunes ClimateBERT on user-corrected feedback data.
Run: python -m backend.ml.train_climatebert
"""

from pathlib import Path
import pandas as pd
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)
from datasets import Dataset

from config.settings import (
    CORRECTION_LOG, CLIMATEBERT_FINETUNED_DIR, DISTILROBERTA_MODEL_DIR,
    PROJECT_ROOT,
)

LABEL_MAP = {
    "climate change mitigation": 0,
    "climate change adaptation": 1,
    "not climate finance": 2,
}
RETRAINED_MODEL_DIR = str(PROJECT_ROOT / "models" / "climatebert-retrained")


def train() -> None:
    if not CORRECTION_LOG.exists():
        print("No corrections found. Run the app and submit feedback first.")
        return

    df = pd.read_csv(CORRECTION_LOG, names=["text", "label"])
    df["label"] = df["label"].map(LABEL_MAP)
    df.dropna(subset=["label"], inplace=True)

    tokenizer = AutoTokenizer.from_pretrained(DISTILROBERTA_MODEL_DIR)
    model     = AutoModelForSequenceClassification.from_pretrained(
        DISTILROBERTA_MODEL_DIR, num_labels=3
    )

    def preprocess(examples):
        return tokenizer(examples["text"], truncation=True, padding=True, max_length=512)

    dataset = Dataset.from_pandas(df).map(preprocess, batched=True)
    split   = dataset.train_test_split(test_size=0.2)

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=RETRAINED_MODEL_DIR,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            num_train_epochs=3,
            learning_rate=2e-5,
            weight_decay=0.01,
            save_strategy="epoch",
            evaluation_strategy="epoch",
        ),
        train_dataset=split["train"],
        eval_dataset=split["test"],
        tokenizer=tokenizer,
    )
    trainer.train()
    trainer.save_model(CLIMATEBERT_FINETUNED_DIR)
    print(f"✅ Model retrained and saved to {CLIMATEBERT_FINETUNED_DIR}")


if __name__ == "__main__":
    train()
