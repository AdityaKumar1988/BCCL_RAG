# SYSTEM ARCHITECTURE: BCCL ENTERPRISE AI KNOWLEDGE RETRIEVAL SYSTEM

## 1. System Architecture Diagram

```
+---------------------------------------------------------------------------------------------------+
|                                         USER LAYER                                                |
|  +---------------------------------------------------------------------------------------------+  |
|  |                 Next.js 14+ / React Enterprise UI (Tailwind CSS, Dark Mode)                 |  |
|  |   [ Chat Interface ]   [ Knowledge Explorer ]   [ Admin Dashboard ]   [ Citations Drawer ]   |  |
|  +---------------------------------------------------------------------------------------------+  |
+--------------------------------------------------+------------------------------------------------+
                                                   | HTTP / REST / SSE Stream
                                                   v
+---------------------------------------------------------------------------------------------------+
|                                      APPLICATION / API GATEWAY                                    |
|  +---------------------------------------------------------------------------------------------+  |
|  |                                  FastAPI Asynchronous Gateway                               |  |
|  |   - Auth & RBAC (JWT/Argon2)                 - Rate Limiter & Sanitizer                     |  |
|  |   - Chat & Streaming SSE Controller          - Document Ingestion Controller                |  |
|  |   - Document Explorer Controller             - Admin & Analytics Controller                 |  |
|  +---------------------------------------------------------------------------------------------+  |
+-------------------+----------------------------------------------+--------------------------------+
                    |                                              |
                    v                                              v
+----------------------------------------+   +------------------------------------------------------+
|       DOCUMENT INGESTION PIPELINE      |   |             RAG RETRIEVAL & GENERATION CORE          |
|  +----------------------------------+  |   |  +------------------------------------------------+  |
|  | 1. Upload & File Validation      |  |   |  | 1. Query Processing & Expansion / Rewriter     |  |
|  +----------------------------------+  |   |  +------------------------------------------------+  |
|  | 2. Text Extraction / OCR Router  |  |   |  | 2. Hybrid Retrieval Engine                     |  |
|  |    - PyMuPDF Native Parser       |  |   |  |    - Dense Semantic Vector Search (pgvector)   |  |
|  |    - Tesseract OCR Fallback      |  |   |  |    - Sparse Lexical BM25 Search (FTS5 / FTS)   |  |
|  +----------------------------------+  |   |  |    - Reciprocal Rank Fusion (RRF)              |  |
|  | 3. Text Cleaner & Normalizer     |  |   |  +------------------------------------------------+  |
|  +----------------------------------+  |   |  | 3. Cross-Encoder / Heuristic Reranker          |  |
|  | 4. Structure-Aware Chunker       |  |   |  +------------------------------------------------+  |
|  |    - Rule / Section Preservation |  |   |  | 4. Evidence Quality & Abstention Evaluator     |  |
|  |    - Metadata Extraction         |  |   |  +------------------------------------------------+  |
|  +----------------------------------+  |   |  | 5. Grounded Prompt Synthesizer                 |  |
|  | 5. Vector & Sparse Indexing      |  |   |  |    - Untrusted Context Isolation               |  |
|  +----------------------------------+  |   |  +------------------------------------------------+  |
|                                        |   |  | 6. LLM Generation (OpenAI / Gemini / Ollama)   |  |
|                                        |   |  +------------------------------------------------+  |
|                                        |   |  | 7. Citation Verifier & Response Formatter      |  |
|                                        |   |  +------------------------------------------------+  |
+-------------------+--------------------+   +---------------------+--------------------------------+
                    |                                              |
                    +----------------------+-----------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------------------+
|                                       PERSISTENCE LAYER                                           |
|  +---------------------------------------------------------------------------------------------+  |
|  |  PostgreSQL with pgvector (and SQLite3 + Dense Vector + FTS5 for zero-friction local mode)  |  |
|  |   - Tables: users, roles, documents, document_chunks, conversations, messages, feedback,   |  |
|  |             ingestion_jobs, audit_logs                                                      |  |
|  |   - Indices: HNSW / IVFFlat vector index, BM25/trigram GIN / FTS5 index                     |  |
|  +---------------------------------------------------------------------------------------------+  |
|  |  File Storage Subsystem (Local File System / S3 Object Storage Abstraction)                 |  |
|  |   - Raw Document Store: data/raw/                                                           |  |
|  |   - Extracted Text Store: data/processed/                                                   |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Component Breakdown

### 2.1 Ingestion Subsystem
1. **`FileValidator`**: Enforces MIME validation, magic-byte checks, and size boundaries (default max 50MB per document).
2. **`TextExtractorRouter`**: Inspects PDF font dictionaries and extractable text volume per page. If character count per page < threshold (e.g. 40 chars), automatically dispatches page rendering (300 DPI) to `OCRProvider` (PyTesseract).
3. **`StructureAwareChunker`**: Detects regex patterns for legal and organizational clauses:
   - Rule patterns: `(?:Rule\s+\d+|Regulation\s+\d+|Clause\s+\d+)`
   - Heading patterns: `(?:CHAPTER\s+[IVXLCDM\d]+|[A-Z\s]{4,}:)`
   - Sub-clauses: `(?:\([a-z\d]+\)|\d+\.\d+)`
   Applies overlapping sliding windows (default 512 tokens with 64 token overlap) without splitting cohesive rule definitions across chunk boundaries.
4. **`MetadataEnricher`**: Extracts and attaches hierarchical breadcrumbs (`document_title`, `rule_number`, `section_name`, `page_number`, `chunk_id`) to every chunk.

### 2.2 Retrieval Subsystem
1. **`DenseVectorRetriever`**: Computes query embeddings via `EmbeddingProvider` and executes cosine similarity over chunk embeddings.
2. **`LexicalBM25Retriever`**: Executes tokenized BM25 or full-text query matching, prioritizing exact matches of legal terms and Rule IDs.
3. **`HybridFusionEngine`**: Merges candidate lists using Reciprocal Rank Fusion:
   $$RRF(d) = \sum_{m \in M} \frac{w_m}{k + \text{rank}_m(d)}$$
   where $k=60$ and $w_{\text{dense}}=0.6, w_{\text{sparse}}=0.4$ (configurable).
4. **`Reranker`**: Re-evaluates top-$N$ candidates using cross-entropy or lexical-semantic cross-scoring.

### 2.3 RAG Generation & Anti-Hallucination Subsystem
1. **`QueryProcessor`**: Normalizes queries, extracts acronyms (e.g. *CDA*, *CIL*, *BCCL*, *DA*), and resolves conversational history coreferences.
2. **`AbstentionEvaluator`**: Calculates maximum chunk relevance $\max(S)$. If $\max(S) < \theta_{\text{abstain}}$, triggers an explicit refusal message without LLM token wastage.
3. **`PromptIsolationEngine`**: Encloses retrieved chunks within XML-style strict boundaries (`<evidence_context id="...">...</evidence_context>`) and commands the LLM to ignore any meta-instructions inside document text.
4. **`CitationEngine`**: Parses and matches claims against source chunk identifiers and generates verified citations with document name, page number, rule number, and excerpt.

---

## 3. Database Schema Design

* **`users`**: `(id, username, email, hashed_password, role, is_active, created_at)`
* **`documents`**: `(id, title, filename, file_path, file_size, mime_type, total_pages, status, is_scanned, created_at, updated_at)`
* **`document_chunks`**: `(id, document_id, chunk_index, page_number, rule_number, section_title, content, token_count, embedding, created_at)`
* **`conversations`**: `(id, user_id, title, created_at, updated_at)`
* **`messages`**: `(id, conversation_id, sender, content, citations_json, latency_ms, token_usage_json, created_at)`
* **`feedback`**: `(id, message_id, user_id, rating, comment, created_at)`
* **`ingestion_jobs`**: `(id, document_id, status, error_message, started_at, completed_at)`
* **`audit_logs`**: `(id, user_id, action, resource, details_json, ip_address, timestamp)`
