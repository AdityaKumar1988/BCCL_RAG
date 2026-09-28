# BCCL ENTERPRISE RAG REST API SPECIFICATION

Base URL: `http://localhost:8000`  
OpenAPI Interactive Documentation: `http://localhost:8000/docs`

---

## 1. Authentication Endpoints

### `POST /api/auth/register`
Creates a new user account.
- **Request Body:**
  ```json
  {
    "username": "aditya_jha",
    "email": "aditya@bccl.gov.in",
    "password": "SecurePassword123",
    "full_name": "Aditya Kumar Jha",
    "department": "Systems Department",
    "role": "user"
  }
  ```
- **Response:** `201 Created` with `UserResponse` object.

### `POST /api/auth/login`
Authenticates credentials and returns a signed JWT bearer token.
- **Request Body:**
  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "role": "admin",
    "username": "admin",
    "full_name": "System Administrator (BCCL Systems Dept)"
  }
  ```

### `GET /api/auth/me`
Returns current authenticated user profile. Requires `Authorization: Bearer <token>`.

---

## 2. RAG & Chat Endpoints

### `POST /api/chat`
Submits a natural language query through the RAG pipeline.
- **Request Body:**
  ```json
  {
    "message": "What are the rules for suspension?",
    "conversation_id": null,
    "document_id": null,
    "knowledge_base": "BCCL_Rules"
  }
  ```
- **Knowledge Base Values:** `"BCCL_Rules"` (55-page amended rules, 295 chunks), `"CDA_Rules"` (baseline rules, 51 chunks), `"all"` (unified search across all sources).
- **Response:** `200 OK`
  ```json
  {
    "conversation_id": 1,
    "message_id": 2,
    "answer": "### BCCL Suspension Rules\n\n- Authority to Suspend...\n\n### Relevant Rule\nRule 26: Suspension",
    "citations": [
      {
        "chunk_id": 7,
        "document_id": 1,
        "document_name": "BCCL Conduct, Discipline and Appeal (CDA) Rules, 1978",
        "page_number": 3,
        "rule_number": "Rule 26",
        "section_title": "CHAPTER III: DISCIPLINE AND SUSPENSION",
        "excerpt": "Rule 26: Suspension (1) The Appointing Authority or Disciplinary Authority...",
        "score": 0.6893
      }
    ],
    "is_abstention": false,
    "latency_ms": 28.45,
    "retrieval_count": 5
  }
  ```

### `POST /api/chat/stream`
Server-Sent Events (SSE) streaming endpoint for token-by-token streaming responses.

### `GET /api/conversations`
Lists all active conversation sessions for the authenticated user.

### `GET /api/conversations/{id}`
Fetches full message history and citations for a specific conversation.

### `DELETE /api/conversations/{id}`
Deletes a conversation history.

---

## 3. Documents & Knowledge Explorer

### `GET /api/documents`
Lists all ingested documents with metadata, scan type, total pages, and chunk counts.

### `GET /api/documents/{id}`
Fetches complete document details including all indexed chunks.

### `GET /api/documents/{id}/chunks?rule=Rule+26&page=1&limit=20`
Paginated browse of chunks for a specific document with optional rule filter.

### `POST /api/documents/search`
Direct hybrid semantic + BM25 search over knowledge chunks.

---

## 4. Admin Operations

### `POST /api/admin/documents/upload`
Uploads and queues a PDF document for asynchronous ingestion. Requires `admin` role.

### `POST /api/admin/documents/{id}/reindex`
Re-runs parsing, chunking, and embedding generation for an existing document.

### `DELETE /api/admin/documents/{id}`
Deletes a document and cascades deletion of all its chunks.

### `GET /api/admin/ingestion/{job_id}`
Returns current ingestion job stage, status, and progress percentage.

### `GET /api/admin/analytics`
Returns system KPI metrics: total documents, chunks, queries, users, latency, and feedback counts.

### `GET /api/admin/audit-logs`
Returns timestamped administrative audit trail.

---

## 5. Feedback

### `POST /api/feedback`
Submits user rating (`1` for positive, `-1` for negative) and comments for a generated answer.

---

## 6. Voice & Deep Learning Intent Endpoints

### `POST /api/voice/transcribe`
Transcribes audio file or buffer to text using OpenAI Whisper.
- **Content-Type:** `multipart/form-data`
- **Form Fields:**
  - `file`: Audio file (`.wav`, `.mp3`, `.ogg`, `.flac`)
  - `language`: Optional language code (`"en"`, default)
- **Response:** `200 OK`
  ```json
  {
    "text": "What are the rules regarding suspension?",
    "language": "en",
    "duration_seconds": 2.45
  }
  ```

### `POST /api/voice/classify`
Classifies input query intent using fine-tuned DistilBERT model.
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "text": "What are the rules regarding suspension?"
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "intent": "suspension",
    "confidence": 0.8742,
    "all_probabilities": {
      "suspension": 0.8742,
      "disciplinary_procedure": 0.0512,
      "misconduct": 0.0315
    }
  }
  ```

### `POST /api/voice/chat`
Full multimodal voice RAG endpoint: Audio $\to$ Whisper STT $\to$ DistilBERT Intent $\to$ Hybrid RAG $\to$ Grounded Answer + Citations.
- **Content-Type:** `multipart/form-data`
- **Form Fields:**
  - `file`: WAV/Audio recording file
  - `conversation_id`: Optional conversation ID for multi-turn history
  - `knowledge_base`: Target knowledge base (`"BCCL_Rules"`, `"CDA_Rules"`, or `"all"`)
- **Response:** `200 OK`
  ```json
  {
    "transcribed_text": "What are the rules regarding suspension?",
    "intent": "suspension",
    "confidence": 0.8742,
    "conversation_id": 1,
    "message_id": 15,
    "answer": "Under BCCL / CDA Rule 20, an employee may be placed under suspension by the Appointing Authority or Disciplinary Authority...",
    "citations": [
      {
        "chunk_id": 112,
        "document_id": 2,
        "document_name": "CDA_Rules_1978_amended_upto_July_2006_10052018-ocr.pdf",
        "page_number": 21,
        "rule_number": "Rule 20",
        "section_title": "SUSPENSION",
        "excerpt": "Rule 20.1: The Appointing Authority or any authority to which it is subordinate or the Disciplinary Authority may place an employee under suspension...",
        "score": 0.8421
      }
    ],
    "is_abstention": false,
    "latency_ms": 320.5,
    "retrieval_count": 5
  }
  ```

