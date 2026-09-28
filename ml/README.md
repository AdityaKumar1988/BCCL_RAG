# BCCL Domain Intent Classification Engine (Deep Learning)

This directory contains the dataset, deep learning architecture, training scripts, evaluation suite, and inference runtime for the domain intent classifier of the **BCCL Enterprise AI Knowledge Assistant**.

---

## 1. Objective

To provide high-accuracy, low-latency, and grounded domain intent understanding for user speech and text queries. The classifier routes queries through the appropriate BCCL knowledge bases and RAG retrieval pipelines while detecting conversational pleasantries, administrative intents, and out-of-scope queries.

---

## 2. Model Architecture

- **Base Model**: `DistilBERT` (`distilbert-base-uncased`, 66M parameters, 6 Transformer encoder layers, 768 hidden dimension, 12 attention heads).
- **Classification Head**:
  - Dropout layer ($p = 0.2$)
  - Linear projection layer ($768 \rightarrow 11$ classes)
  - Softmax probability distribution over domain intents
- **Framework**: PyTorch + Hugging Face Transformers

---

## 3. Dataset Specification

The domain-specific dataset is constructed directly from the official **BCCL Conduct, Discipline and Appeal (CDA) Rules, 1978 (Amended upto July 2006)**.

- **Location**: `ml/data/intents.csv`
- **Total Samples**: 330
- **Total Classes**: 11 (30 balanced samples per class)
- **Data Splits**:
  - **Train**: 231 samples (70%) (`ml/data/train.csv`)
  - **Validation**: 49 samples (15%) (`ml/data/val.csv`)
  - **Test**: 50 samples (15%) (`ml/data/test.csv`)
- **Random Seed**: 42 (stratified across all 11 classes)

### Intent Classes

| Intent Class | Description | BCCL Document Anchor |
|--------------|-------------|----------------------|
| `greeting` | User greetings and pleasantries | Conversational |
| `goodbye` | Conversation termination and thanks | Conversational |
| `suspension` | Suspension grounds, subsistence allowance, deemed suspension | Rule 26 / Rule 19 |
| `misconduct` | Prohibited acts, corruption, theft, insubordination, harassment | Rule 5 |
| `major_penalty` | Removal, dismissal, reduction in rank/pay scale, compulsory retirement | Rule 27 |
| `minor_penalty` | Censure, withholding increments, withholding promotion, recovery | Rule 27 |
| `disciplinary_procedure` | Charge sheet, Inquiry Officer, statement of defense, witness rights | Rule 29 |
| `appeal_procedure` | Right of appeal, 45-day limitation, Appellate Authority powers | Rule 34 |
| `general_conduct` | Integrity obligations, private trade, politics, property declarations | Rule 4 |
| `clarification_general` | Scope, definitions, executive applicability, statutory powers | Rules 1–3 |
| `out_of_scope` | External topics (weather, movies, coding, cooking, trivia) | External non-BCCL |

---

## 4. Training Pipeline

### Execution

```bash
python ml/train_intent_classifier.py
```

### Hyperparameters

- **Optimizer**: AdamW
- **Learning Rate**: $3 \times 10^{-5}$
- **Weight Decay**: 0.01
- **Warmup Steps**: 10% of total training steps
- **Batch Size**: 16
- **Max Sequence Length**: 64 tokens
- **Epochs**: 5
- **Gradient Clipping**: Max norm 1.0
- **Artifact Destination**: `ml/models/distilbert_intent_model/`

---

## 5. Evaluation Suite

### Execution

```bash
python ml/evaluate_intent_classifier.py
```

Outputs comprehensive metrics:
- Overall Accuracy
- Macro and Weighted Precision, Recall, and F1-Score
- Per-class precision, recall, and support
- Normalized Confusion Matrix (saved to `ml/models/confusion_matrix.json`)
- Metrics summary saved to `ml/models/evaluation_results.json`

---

## 6. Inference Runtime & Intent Routing

The inference runtime (`ml/inference.py`) provides:
1. **Confidence Thresholding**: Confidence scores below 0.50 are flagged as `is_low_confidence = True`.
2. **Safe Fallback**: Low-confidence queries gracefully fall back to the general RAG hybrid search without forcing an erroneous category.
3. **Conversational Routing**:
   - `GREETING` $\rightarrow$ direct friendly assistant welcome
   - `GOODBYE` $\rightarrow$ polite sign-off
   - `OUT_OF_SCOPE` $\rightarrow$ polite clarification that BCCL Assistant answers enterprise governance questions
   - `RAG_SEARCH` $\rightarrow$ hybrid dense + lexical retrieval against selected knowledge base (`BCCL_Rules` or `CDA_Rules`)
