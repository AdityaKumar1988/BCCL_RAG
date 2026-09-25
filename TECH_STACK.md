# TECHNOLOGY STACK & DECISION MATRIX

## 1. Core Stack Summary

| Component | Selected Technology | Rationale & Alternatives Considered |
| :--- | :--- | :--- |
| **Frontend Framework** | Next.js 14+ (App Router) / React 18 / TypeScript | Modern, high performance, enterprise SSR/CSR capabilities, type-safe API consumption. Replaces Botpress Webchat. |
| **Styling & UI Kit** | Tailwind CSS + Lucide Icons + Custom BCCL Industrial Dark Theme | Responsive, polished enterprise dashboard aesthetics, zero heavy UI framework overhead. |
| **Backend Framework** | FastAPI (Python 3.11–3.14) + Uvicorn | High-throughput async ASGI, native Pydantic v2 validation, automated OpenAPI docs, seamless AI/ML ecosystem integration. |
| **Database & Vector Store** | PostgreSQL 16 + `pgvector` (with zero-config SQLite + dense vector & FTS5 fallback) | Standardized ACID storage for transactional data (users, chats, audit) + native cosine/inner product vector search in one database. |
| **PDF & OCR Processing** | PyMuPDF (MuPDF C-bindings) + PyTesseract / Tesseract OCR | PyMuPDF is 10-20x faster than PyPDF/pdfminer with superior font/layout extraction; Tesseract handles scanned historical notices. |
| **Lexical Search** | BM25 / PostgreSQL Full-Text Search (tsvector + GIN) / SQLite FTS5 | True hybrid retrieval combining keyword precision (crucial for exact rule/clause numbers) with semantic embeddings. |
| **Embedding Abstraction** | Pluggable: HuggingFace BGE / MiniLM / OpenAI `text-embedding-3-small` / Gemini Embedding / FastEmbed | Modular embedding provider allowing offline CPU-based inference and cloud APIs. |
| **LLM Orchestration** | Pluggable: Google Gemini / OpenAI GPT-4o / Ollama / Deterministic Grounded Fallback | Provider pattern ensures zero vendor lock-in and offline development reliability. |
| **Security & Auth** | JWT (`python-jose` / `pyjwt`) + Argon2/Bcrypt (`passlib` / `pwdlib`) | Industry-standard stateless auth with RBAC (`admin`, `user`, `auditor`). |
| **Testing Framework** | `pytest` + `httpx` + `pytest-asyncio` | Full unit, integration, RAG grounding, and API test coverage. |
| **Containerization** | Docker + Docker Compose | Multi-container reproducible deployment across developer machines and on-prem enterprise servers. |

---

## 2. Environment Configuration (`.env`)

The system relies on structured environment variables with sensible defaults for local development:

```env
# Server
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
SECRET_KEY=bccl-enterprise-secret-key-change-in-production-2026

# Database
DATABASE_URL=sqlite:///./data/bccl_rag.db
# DATABASE_URL=postgresql://bccl_user:bccl_pass@localhost:5432/bccl_rag

# AI Providers
LLM_PROVIDER=gemini # or openai, ollama, mock
EMBEDDING_PROVIDER=local # or openai, gemini, huggingface

# Keys (Optional if using local providers)
GEMINI_API_KEY=
OPENAI_API_KEY=

# Ingestion & Retrieval Hyperparameters
CHUNK_SIZE=512
CHUNK_OVERLAP=64
DENSE_SEARCH_WEIGHT=0.6
SPARSE_SEARCH_WEIGHT=0.4
RETRIEVAL_TOP_K=5
ABSTENTION_THRESHOLD=0.35
```
