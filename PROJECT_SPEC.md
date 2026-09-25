# PROJECT SPECIFICATION: BCCL ENTERPRISE AI KNOWLEDGE RETRIEVAL SYSTEM

## 1. Executive Summary & Context

* **Project Title**: Design and Development of an Enterprise AI-Powered Knowledge Retrieval System for Bharat Coking Coal Limited (BCCL) using Retrieval-Augmented Generation (RAG)
* **Organization**: Bharat Coking Coal Limited (BCCL), a subsidiary of Coal India Limited (Maharatna PSU), Ministry of Coal, Govt. of India.
* **Original Project Base**: Systems Department, BCCL, Koyla Bhawan, Dhanbad.
* **Goal**: Transform the initial prototype (which was configured on low-code Botpress) into an authentic, standalone, production-ready Enterprise AI Knowledge Retrieval System with full code ownership, zero Botpress dependency, and enterprise-grade architecture.

---

## 2. Problem Statement & Motivation

BCCL employees and administrative officers frequently need to consult comprehensive governance documents—chief among them the **Conduct, Discipline and Appeal (CDA) Rules 1978** and associated circulars, SOPs, and manuals. 

### Limitations of the Legacy / Manual Approach:
1. **Time-Consuming Navigation**: Manual browsing of 50–200+ page policy manuals delays decision-making.
2. **Lexical Keyword Rigidity**: Standard PDF search (`Ctrl+F`) fails when users use conversational vocabulary or synonyms not matching legal phrasing verbatim (e.g., asking *"What happens if an employee is suspended?"* vs. document heading *"Rule 26: Subsistence Allowance and Suspension"*).
3. **Scanned / Image PDFs Inaccessibility**: Historical circulars and office orders scanned as images cannot be searched without OCR.
4. **Cognitive Overhead & Misinterpretation**: Parsing dense legal clauses without context summaries causes errors.

---

## 3. Translation of Botpress Components to Standalone Architecture

| Botpress Prototype Component | Replacement Standalone Enterprise Implementation |
| :--- | :--- |
| **Botpress Cloud Webchat** | Next.js 14+ / React / Tailwind CSS Enterprise Dark-Theme UI with citations drawer, search explorer, streaming support, and audit tracking |
| **Botpress Knowledge Base** | Custom Document Ingestion Engine with Structure-Aware PDF Extraction, OCR fallback, PostgreSQL / SQLite + pgvector / dense vector index & Lexical BM25 / FTS index |
| **Botpress Autonomous Node** | Modular RAG Orchestration Layer (`QueryProcessor`, `ContextBuilder`, `Generator`, `CitationEngine`, `AbstentionEvaluator`) |
| **Botpress Workflow Engine** | FastAPI Async Pipeline + Background Task Ingestion Queue with comprehensive state machine |
| **Botpress LLM Integration** | Pluggable Provider Abstraction (`LLMProvider`, `EmbeddingProvider`, `OCRProvider`, `RerankerProvider`) supporting OpenAI, Google Gemini, Ollama, HuggingFace, and Local Mock/Deterministic fallback |
| **Botpress User Management** | JWT / Session-based Role-Based Access Control (`User`, `Admin`, `Auditor`, `DeptManager`) |

---

## 4. Functional Requirements

### 4.1 Document Ingestion & Storage Pipeline
- **FR-01**: Admin upload of organizational PDFs (e.g. Conduct, Discipline & Appeal Rules).
- **FR-02**: File validation (MIME-type check, magic bytes verification, file size limits, malware/bomb safety).
- **FR-03**: Dual text extraction: Native PyMuPDF text extraction for digital PDFs; PyTesseract / PyMuPDF OCR page rendering for scanned/image PDFs.
- **FR-04**: Structure-aware semantic chunking preserving Rule numbers (e.g. Rule 5, Rule 26, Rule 27), sections, sub-clauses, headings, and page boundaries.
- **FR-05**: Rich metadata tagging on every chunk: `document_id`, `document_name`, `page_number`, `rule_number`, `section_title`, `chunk_index`, `token_count`.
- **FR-06**: Dual indexing: Dense vector embedding generation + Sparse full-text lexical indexing (BM25 / FTS).
- **FR-07**: Ingestion lifecycle tracking with states: `UPLOADED`, `PROCESSING`, `OCR_REQUIRED`, `CHUNKING`, `EMBEDDING`, `INDEXING`, `READY`, `FAILED`.

### 4.2 Query Processing & Hybrid Retrieval
- **FR-08**: Natural language conversational query understanding with query rewriting and contextual coreference resolution based on conversation history.
- **FR-09**: Hybrid Retrieval combining Semantic Dense Vector search + Lexical Sparse BM25 search via Reciprocal Rank Fusion (RRF) and Weighted Score Fusion.
- **FR-10**: Optional Cross-Encoder Reranking for high-precision top-$k$ candidate scoring.
- **FR-11**: Strict document-filtering and metadata filtering (by document, section, or rule).

### 4.3 Grounded Generation & Anti-Hallucination
- **FR-12**: Grounded generation prompt forcing LLM to answer **strictly** using retrieved document chunks.
- **FR-13**: Abstention Mechanism: If top retrieval similarity scores fall below the configurable confidence threshold ($\tau$) or evidence is insufficient, the system returns a safe, explicit abstention response: *"I could not find sufficient information about this in the available BCCL documents."*
- **FR-14**: Structured response formatting: Key summary, detailed points/sub-clauses, relevant Rule numbers, and explicit source references.
- **FR-15**: Citation verification: Every citation is tied to a real chunk ID, document name, page number, and text snippet.

### 4.4 Enterprise Chat & Knowledge Explorer
- **FR-16**: Interactive chat sessions with multi-turn conversation memory.
- **FR-17**: Real-time streaming response generation.
- **FR-18**: Knowledge Base Explorer allowing direct search, document browsing, rule inspection, and source snippet verification.
- **FR-19**: User feedback system (thumbs up / thumbs down + comments) linked to query-response logs.
- **FR-20**: Admin dashboard for ingestion metrics, document lifecycle management, re-indexing, user audits, and retrieval analytics.

---

## 5. Non-Functional Requirements

- **NFR-01 (Security)**: Password hashing with Argon2/Bcrypt, JWT access tokens with short TTL, role-based authorization guards, input sanitation, strict Prompt Injection boundary tags (`<untrusted_document_context>`).
- **NFR-02 (Performance & Latency)**: Sub-second hybrid retrieval latency; async background document ingestion without blocking user threads.
- **NFR-03 (Observability)**: Structured JSON logging, request tracing IDs, audit trail for document uploads and admin operations.
- **NFR-04 (Portability & Extensibility)**: Clean provider interfaces (`LLMProvider`, `EmbeddingProvider`, `OCRProvider`) allowing zero code modifications when switching between OpenAI, Gemini, HuggingFace, or Ollama.
- **NFR-05 (Deterministic Testability)**: Comprehensive test suite covering chunking, OCR, hybrid search, RAG grounding, abstention, prompt injection safety, and API endpoints.

---

## 6. Baseline Test Cases (from BCCL Report)

1. **TC-01 (Suspension Rules)**: Query: *"What are the rules for suspension?"* -> Expected: Retrieval of Rule 26/Suspension provisions, subsistence allowance details, non-penalty clarification.
2. **TC-02 (Major Penalties)**: Query: *"Explain major penalties."* -> Expected: Retrieval of Rule 27/Major Penalties (reduction in rank/pay, compulsory retirement, removal, dismissal).
3. **TC-03 (Misconduct Provisions)**: Query: *"What constitutes misconduct?"* -> Expected: Retrieval of Rule 5 misconduct clauses (theft, fraud, insubordination, bribery, etc.).
4. **TC-04 (Appeal Procedure)**: Query: *"Can an employee appeal a penalty?"* -> Expected: Retrieval of Appeal rules, 45-day limitation period, Appellate Authority process.
5. **TC-05 (Abstention on Unavailable Info)**: Query: *"What is the policy for leave encashment in overseas branches?"* -> Expected: Clear abstention statement without hallucination.
