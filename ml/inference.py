import os
import json
import torch
import numpy as np
from typing import Dict, Any, Optional
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification

class IntentClassifier:
    """
    Production Deep Learning Intent Classifier powered by fine-tuned DistilBERT.
    Provides intent probability distribution, confidence scoring, low-confidence thresholding,
    and automatic intent-to-RAG routing.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IntentClassifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_dir: Optional[str] = None, confidence_threshold: float = 0.15):
        if getattr(self, "_initialized", False):
            return

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = model_dir or os.environ.get("DISTILBERT_MODEL_PATH") or os.path.join(base_dir, "models", "distilbert_intent_model")
        self.confidence_threshold = confidence_threshold
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.tokenizer = None
        self.id2label = {}
        self.label2id = {}
        self._load_model()
        self._initialized = True

    def _load_model(self):
        mapping_path = os.path.join(self.model_dir, "label_mapping.json")
        if not os.path.exists(self.model_dir) or not os.path.exists(mapping_path):
            # Model not yet trained
            self.model = None
            return

        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
                self.label2id = mapping["label2id"]
                self.id2label = {int(k): v for k, v in mapping["id2label"].items()}

            self.tokenizer = DistilBertTokenizer.from_pretrained(self.model_dir)
            self.model = DistilBertForSequenceClassification.from_pretrained(self.model_dir)
            self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            print(f"Warning: Failed to load DistilBERT model: {e}")
            self.model = None

    def predict(self, text: str, threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Classify text query into domain intents with confidence estimation.
        """
        thresh = threshold or self.confidence_threshold
        clean_text = text.strip()

        if not clean_text:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "is_low_confidence": True,
                "probabilities": {},
                "routing_decision": "RAG_SEARCH",
                "suggested_knowledge_base": "BCCL_Rules"
            }

        # If model is loaded, run actual Deep Learning inference
        if self.model is not None and self.tokenizer is not None:
            encoding = self.tokenizer(
                clean_text,
                truncation=True,
                max_length=64,
                padding="max_length",
                return_tensors="pt"
            )
            input_ids = encoding["input_ids"].to(self.device)
            attention_mask = encoding["attention_mask"].to(self.device)

            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

            top_idx = int(np.argmax(probs))
            top_intent = self.id2label.get(top_idx, "clarification_general")
            confidence = float(probs[top_idx])

            prob_dict = {self.id2label[i]: round(float(probs[i]), 4) for i in range(len(probs))}
            is_low_conf = confidence < thresh

            # Determine routing decision
            if is_low_conf:
                routing = "RAG_SEARCH"  # fallback to general RAG without forcing wrong intent
            elif top_intent == "greeting":
                routing = "GREETING"
            elif top_intent == "goodbye":
                routing = "GOODBYE"
            elif top_intent == "out_of_scope":
                routing = "OUT_OF_SCOPE"
            else:
                routing = "RAG_SEARCH"

            return {
                "intent": top_intent,
                "confidence": round(confidence, 4),
                "is_low_confidence": is_low_conf,
                "probabilities": prob_dict,
                "routing_decision": routing,
                "suggested_knowledge_base": "BCCL_Rules"
            }

        # Fallback heuristic if model is not yet loaded
        return {
            "intent": "clarification_general",
            "confidence": 0.50,
            "is_low_confidence": True,
            "probabilities": {},
            "routing_decision": "RAG_SEARCH",
            "suggested_knowledge_base": "BCCL_Rules"
        }
