# BCCL Enterprise AI Knowledge Retrieval System (RAG)
### Voice-Enabled Multimodal AI Knowledge Platform with Deep Learning Intent Classification

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14.2+-black.svg)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.14+-EE4C2C.svg)](https://pytorch.org/)
[![Transformers](https://img.shields.io/badge/Transformers-DistilBERT-FFD21E.svg)](https://huggingface.co/)
[![Whisper](https://img.shields.io/badge/Whisper-Local%20STT-00A67E.svg)](https://openai.com/)
[![Tests](https://img.shields.io/badge/Tests-29%2F29%20Passing%20(100%25)-brightgreen.svg)]()
[![Benchmark Pass Rate](https://img.shields.io/badge/RAG%20Benchmark-100%25-brightgreen.svg)]()

> **Notice:** This is an authentic, production-grade enterprise RAG and Voice-Enabled AI platform designed for Bharat Coking Coal Limited (a subsidiary of Coal India Limited). It transforms static governance manuals into an interactive, voice- and text-enabled, document-grounded decision support system with zero Botpress dependency.
>
> ⚠️ **DEPLOYMENT NOTICE**: In accordance with the current local development phase, **ALL ONLINE DEPLOYMENT (Render, Vercel, AWS, Hugging Face Spaces) IS DEFERRED**. The system operates locally and self-contained on the host workstation.

---

## Table of Contents
1. [What the System Is](#1-what-the-system-is)
2. [Problem Being Solved](#2-problem-being-solved)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Voice Pipeline & Speech Recognition](#4-voice-pipeline--speech-recognition)
5. [Deep Learning Intent Classifier](#5-deep-learning-intent-classifier)
6. [BCCL_Rules Knowledge Base & Dual KB Architecture](#6-bccl_rules-knowledge-base--dual-kb-architecture)
7. [Knowledge Base Selector](#7-knowledge-base-selector)
8. [Hybrid Retrieval & Grounded RAG Pipeline](#8-hybrid-retrieval--grounded-rag-pipeline)
9. [Abstention & Anti-Hallucination Policy](#9-abstention--anti-hallucination-policy)
10. [Authentication & RBAC](#10-authentication--rbac)
11. [Evaluation & Model Benchmark Results](#11-evaluation--model-benchmark-results)
12. [Local Setup & Startup Instructions](#12-local-setup--startup-instructions)
13. [Running Automated Tests](#13-running-automated-tests)
14. [Example Voice Queries](#14-example-voice-queries)

---

## 1. What the System Is
The **BCCL Enterprise AI Knowledge Retrieval System** is an end-to-end, document-grounded AI knowledge platform built for Bharat Coking Coal Limited. It enables executives and employees to query official BCCL governance documents—including the **CDA Rules 1978** and the newly ingested **BCCL_Rules (amended up to July 2006, 55 pages)**—using both conversational natural language text and hands-free microphone voice input.

Responses are strictly synthesized from verified legal text chunks and accompanied by interactive citations indicating the source document, Rule number, and page number.

---

## 2. Problem Being Solved
* **Dense Policy Manuals**: Disciplinary regulations span 50–200+ pages of dense legal text.
* **Exact Terminology Mismatches**: Keyword searches (`Ctrl+F`) fail when users phrase questions colloquially.
* **Hands-Free Mining Operations**: Personnel in colliery offices and on-site operations need voice-enabled voice query capabilities.
* **Model Hallucinations**: Standard public LLMs hallucinate internal disciplinary codes, leading to severe legal and HR risks.

---

## 3. High-Level Architecture

```
                                  [ User Microphone / Text Input ]
                                                │
                          ┌─────────────────────┴─────────────────────┐
                          ▼                                           ▼
             [ Voice Audio (.wav) ]                         [ Text Query ]
                          │                                           │
                          ▼                                           │
         ┌─────────────────────────────────┐                          │
         │   OpenAI Whisper Engine (STT)   │                          │
         │   (Local, SoundFile 16kHz PCM)  │                          │
         └────────────────┬────────────────┘                          │
                          ▼                                           │
               [ Recognized Speech Text ]                             │
                          │                                           │
                          ├───────────────────────────────────────────┘
                          ▼
         ┌──────────────────────────────────────────────┐
         │   DistilBERT Sequence Classifier (PyTorch)   │
         │   (11-Class Domain Intent Classification)    │
         └────────────────┬─────────────────────────────┘
                          │
                          ▼
            [ Predicted Intent & Confidence ]
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
   [ Conversational / Out ]   [ Legal Query / Low Confidence ]
             │                         │
             ▼                         ▼
    [ Fast Direct Response ]   ┌──────────────────────────────────────────┐
    (Greeting/Bye/Abstain)     │  Knowledge Base Routing Filter           │
                               │  (BCCL_Rules / CDA_Rules / all)          │
                               └──────────────────┬───────────────────────┘
                                                  ▼
                               ┌──────────────────────────────────────────┐
                               │  Hybrid Retrieval Engine                 │
                               │  - Okapi BM25 Lexical Search             │
                               │  - Dense Semantic Vector Search          │
                               │  - Reciprocal Rank Fusion (RRF)          │
                               └──────────────────┬───────────────────────┘
                                                  ▼
                               ┌──────────────────────────────────────────┐
                               │  Cross-Score Legal Rule Reranker         │
                               └──────────────────┬───────────────────────┘
                                                  ▼
                               ┌──────────────────────────────────────────┐
                               │  Abstention & Grounding Evaluator        │
                               └──────────────────┬───────────────────────┘
                                                  ▼
                               ┌──────────────────────────────────────────┐
                               │  Grounded Response Synthesizer           │
                               │  + Interactive Citations Generator       │
                               └──────────────────┬───────────────────────┘
                                                  ▼
                         [ Frontend Response with Verified Sources ]
```

---

## 4. Voice Pipeline & Speech Recognition
* **Microphone Capture**: The Next.js frontend uses `WavRecorder` (`frontend/src/lib/wavRecorder.ts`) via the browser Web Audio API to capture raw microphone audio downsampled directly to 16,000 Hz 16-bit mono PCM WAV.
* **Zero FFMPEG Requirement**: Because audio is encoded directly to RIFF WAV in the browser, backend decoding via Python `soundfile` works out-of-the-box on Windows without needing external `ffmpeg.exe` installed on PATH.
* **On-Device Whisper Engine**: OpenAI Whisper (`base` model, ~74M parameters, configurable via `WHISPER_MODEL` in `.env`) is hosted locally via `backend/app/providers/speech_provider.py`. Whisper runs entirely offline on CPU/GPU with high accuracy on English speech and Indian accents.
* **Voice UI Elements**:
  * Microphone toggle button `[🎙️]` in chat input bar.
  * Real-time audio capture state: `🔴 Listening... (00:0X)` with Stop & Cancel options.
  * Message bubble headers: `🎙️ Voice Input • Recognized Speech: "..."`.
  * Detected intent indicator: `🎯 Detected Intent: Suspension (Confidence: 87.4%)`.

---

## 5. Deep Learning Intent Classifier
* **Architecture**: Fine-tuned `distilbert-base-uncased` with custom linear classification head (66.95M parameters).
* **Taxonomy (11 Classes)**:
  1. `greeting`: Conversational openings
  2. `goodbye`: Sign-offs and closings
  3. `suspension`: Rule 20, deemed suspension, subsistence allowance
  4. `misconduct`: Rule 5, 29 sub-clauses of misconduct
  5. `major_penalty`: Dismissal, removal, compulsory retirement, demotion
  6. `minor_penalty`: Censure, withholding increment, recovery
  7. `disciplinary_procedure`: Rule 29, charge sheets, inquiry officer
  8. `appeal_procedure`: Rule 34, appellate authority, 45-day limitation
  9. `general_conduct`: Integrity, devotion to duty, conflict of interest
  10. `clarification_general`: Document lookup, circulars, rule numbers
  11. `out_of_scope`: Non-pertinent general knowledge queries
* **Dataset**: 330 expert-curated utterances in `ml/data/intents.csv` split into Train (231), Validation (49), and Hold-out Test (50).
* **Calibrated Threshold & Fallback**: Calibrated threshold ($\tau = 0.15$). Any query with confidence $< 0.15$ automatically falls back to full hybrid RAG retrieval.

---

## 6. BCCL_Rules Knowledge Base & Dual KB Architecture
* **Source Document**: `new_data/CDA_Rules_1978_amended_upto_July_2006_10052018-ocr.pdf` (55 pages).
* **Ingestion Script**: `backend/scripts/ingest_bccl_rules.py`.
* **Logical Isolation**: Database schema (`data/bccl_rag.db`) extended with `knowledge_base VARCHAR(64) DEFAULT 'CDA_Rules'` on `documents` and `document_chunks`.
* **Ingested Chunks**:
  * `BCCL_Rules`: **295 chunks** across 55 pages.
  * `CDA_Rules`: **51 chunks** (baseline).
  * Strict database filtering ensures zero cross-contamination unless the user explicitly requests "All Sources".

---

## 7. Knowledge Base Selector
The Assistant interface features a knowledge-base selector control:
* `BCCL Rules`: Queries the newly ingested 55-page amended rules (295 chunks).
* `CDA Rules`: Queries baseline CDA documentation (51 chunks).
* `All Sources`: Unified search across all indexed corporate rules.

---

## 8. Hybrid Retrieval & Grounded RAG Pipeline
* **Dense Semantic Search**: Cosine similarity over normalized sentence embeddings.
* **Lexical Search**: Okapi BM25 ($k_1=1.5, b=0.75$) with IDF scoring.
* **Reciprocal Rank Fusion (RRF)**:
  $$RRF(d) = \frac{0.65}{60 + \text{rank}_{\text{dense}}(d)} + \frac{0.35}{60 + \text{rank}_{\text{sparse}}(d)}$$
* **Legal Reranker**: Exact Rule number match and phrase density scoring.
* **Candidate Pool**: Dynamically expanded (`pool_size = max(k * 4, 30)`) ensuring high recall across multi-corpus boundaries.

---

## 9. Abstention & Anti-Hallucination Policy
When questions fall outside the scope of BCCL/CDA rules:
* The intent classifier routes `out_of_scope` queries directly to abstention.
* The `AbstentionEvaluator` checks retrieval evidence scores.
* If evidence is below the confidence threshold ($\tau = 0.25$), the system returns:
  > *"I could not find sufficient information about this in the available BCCL documents."*

---

## 10. Authentication & RBAC
* Stateless JWT authentication with salted Bcrypt password hashing.
* Pre-seeded Accounts:
  * **Administrator**: `admin` / `admin123` (Access to Upload, Delete, Re-index, Analytics, Audit Logs)
  * **Executive User**: `user` / `user123` (Access to Assistant, Voice Chat, Conversations, Explorer)

---

## 11. Evaluation & Model Benchmark Results

### Intent Classifier Performance (Hold-out Test Set, 50 samples)
* **Accuracy**: **68.00%**
* **Weighted Precision**: **72.34%**
* **Macro Precision**: **72.24%**
* **Macro Recall**: **69.09%**
* **Macro F1-Score**: **65.09%**
* **High-Stakes Legal Class F1**:
  * `misconduct`: **90.9%** (100% recall)
  * `out_of_scope`: **88.9%** (100% recall)
  * `goodbye`: **83.3%** (100% recall)
  * `disciplinary_procedure`: **75.0%**
  * `general_conduct`: **75.0%**
  * `suspension`: **72.7%** (100% recall)

### RAG System Retrieval Benchmark
* **Pass Rate**: **100.0%** (10/10 test cases)
* **Recall@5**: **100.0%**
* **Abstention Accuracy**: **100.0%**
* **Citation Faithfulness**: **100.0%**

---

## 12. Local Setup & Startup Instructions

### Step 1: Start Backend (Terminal 1)
```powershell
cd "C:\Users\adity\OneDrive\Desktop\BCCL RAG"

# Run FastAPI backend on port 8000
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
* Backend starts at `http://127.0.0.1:8000`
* Interactive API Documentation: `http://127.0.0.1:8000/docs`
* Automatic auto-seeding ensures `BCCL_Rules` (295 chunks) is verified and loaded.

### Step 2: Start Frontend (Terminal 2)
```powershell
cd "C:\Users\adity\OneDrive\Desktop\BCCL RAG\frontend"

# Start Next.js frontend
npm run dev
```
* Open browser at `http://localhost:3000`
* Sign in with `user` / `user123` or `admin` / `admin123`.

---

## 13. Running Automated Tests

Run all 29 automated tests across 13 test suites:
```powershell
cd "C:\Users\adity\OneDrive\Desktop\BCCL RAG"
python -m pytest backend/tests/ -v
```

### Test Suite Summary:
* `test_voice_and_intent.py` (12 tests): Ingestion, KB isolation, DistilBERT classification, Whisper STT, voice chat endpoint, abstention
* `test_auth.py` (2 tests): Password hashing & JWT authentication
* `test_chunker.py` (3 tests): Structure-aware chunking & legal headers
* `test_ocr.py` (2 tests): Scanned PDF detection & OCR text extraction
* `test_retrieval.py` (3 tests): BM25, Semantic dense vector search, and Hybrid RRF
* `test_rag_grounding.py` (4 tests): Grounded question answering & citations
* `test_abstention.py` (1 test): Out-of-scope question refusal
* `test_prompt_injection.py` (1 test): Prompt injection defense
* `test_api.py` (1 test): End-to-end FastAPI endpoint integration flows

---

## 14. Example Voice Queries

| Category | Voice Utterance | Predicted Intent | Retrieval Result |
|---|---|---|---|
| **Suspension** | *"What are the rules regarding suspension?"* | `suspension` | BCCL Rule 20, deemed suspension, subsistence allowance |
| **Penalties** | *"What is the difference between major and minor penalties?"* | `major_penalty` | BCCL Rule 9, penalty schedules |
| **Misconduct** | *"What acts constitute misconduct under BCCL rules?"* | `misconduct` | BCCL Rule 5, 29 specific misconduct clauses |
| **Appeals** | *"What is the procedure and time limit for filing an appeal?"* | `appeal_procedure` | BCCL Rule 34, 45-day limitation period |
| **Out-of-Scope** | *"What is the weather in Dhanbad today?"* | `out_of_scope` | Explicit abstention triggered |

For in-depth architectural specifications and training documentation, see [docs/VOICE_AND_INTENT_SYSTEM.md](file:///C:/Users/adity/OneDrive/Desktop/BCCL%20RAG/docs/VOICE_AND_INTENT_SYSTEM.md).
