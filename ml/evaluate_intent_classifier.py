import os
import sys
import json
import torch
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.train_intent_classifier import IntentDataset

def evaluate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_dir, "models", "distilbert_intent_model")
    test_path = os.path.join(base_dir, "data", "test.csv")
    mapping_path = os.path.join(models_dir, "label_mapping.json")

    if not os.path.exists(models_dir) or not os.path.exists(mapping_path):
        raise FileNotFoundError(f"Model or label mapping not found in {models_dir}. Run ml/train_intent_classifier.py first.")

    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)
        label2id = mapping["label2id"]
        id2label = {int(k): v for k, v in mapping["id2label"].items()}

    test_df = pd.read_csv(test_path)
    print(f"Loaded {len(test_df)} test samples from {test_path}.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    tokenizer = DistilBertTokenizer.from_pretrained(models_dir)
    model = DistilBertForSequenceClassification.from_pretrained(models_dir)
    model.to(device)
    model.eval()

    test_texts = test_df["text"].tolist()
    test_labels = [label2id[l] for l in test_df["intent"]]

    test_dataset = IntentDataset(test_texts, test_labels, tokenizer)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

    all_preds = []
    all_targets = []
    all_probs = []

    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            preds = np.argmax(probs, axis=-1)

            all_preds.extend(preds)
            all_targets.extend(labels.cpu().numpy())
            all_probs.extend(probs)

    accuracy = float(accuracy_score(all_targets, all_preds))
    prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(all_targets, all_preds, average="macro", zero_division=0)
    prec_weighted, rec_weighted, f1_weighted, _ = precision_recall_fscore_support(all_targets, all_preds, average="weighted", zero_division=0)

    target_names = [id2label[i] for i in range(len(id2label))]
    report_dict = classification_report(all_targets, all_preds, target_names=target_names, output_dict=True, zero_division=0)
    report_text = classification_report(all_targets, all_preds, target_names=target_names, zero_division=0)
    conf_mat = confusion_matrix(all_targets, all_preds).tolist()

    print("\n" + "=" * 60)
    print("      DEEP LEARNING INTENT CLASSIFIER EVALUATION REPORT")
    print("=" * 60)
    print(f"Accuracy:           {accuracy * 100:.2f}%")
    print(f"Macro Precision:    {prec_macro * 100:.2f}%")
    print(f"Macro Recall:       {rec_macro * 100:.2f}%")
    print(f"Macro F1-Score:     {f1_macro * 100:.2f}%")
    print(f"Weighted Precision: {prec_weighted * 100:.2f}%")
    print(f"Weighted Recall:    {rec_weighted * 100:.2f}%")
    print(f"Weighted F1-Score:  {f1_weighted * 100:.2f}%")
    print("\nDetailed Per-Class Classification Report:")
    print(report_text)
    print("Confusion Matrix:")
    print(np.array(conf_mat))
    print("=" * 60)

    results = {
        "model_architecture": "DistilBertForSequenceClassification",
        "base_model": "distilbert-base-uncased",
        "num_classes": len(id2label),
        "total_test_samples": len(test_df),
        "metrics": {
            "accuracy": round(accuracy, 4),
            "macro_precision": round(float(prec_macro), 4),
            "macro_recall": round(float(rec_macro), 4),
            "macro_f1": round(float(f1_macro), 4),
            "weighted_precision": round(float(prec_weighted), 4),
            "weighted_recall": round(float(rec_weighted), 4),
            "weighted_f1": round(float(f1_weighted), 4)
        },
        "per_class_report": report_dict,
        "classes": target_names
    }

    eval_results_path = os.path.join(base_dir, "models", "evaluation_results.json")
    with open(eval_results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    conf_mat_path = os.path.join(base_dir, "models", "confusion_matrix.json")
    with open(conf_mat_path, "w", encoding="utf-8") as f:
        json.dump({
            "classes": target_names,
            "matrix": conf_mat
        }, f, indent=2)

    print(f"Saved evaluation metrics to: {eval_results_path}")
    print(f"Saved confusion matrix to:   {conf_mat_path}")
    return results

if __name__ == "__main__":
    evaluate()
