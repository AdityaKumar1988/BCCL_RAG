# DEPLOYMENT GUIDE: BCCL ENTERPRISE AI KNOWLEDGE SYSTEM

This document outlines deployment options for running the BCCL Knowledge Retrieval Platform in Local Development, On-Premises Enterprise Infrastructure, and Dockerized Environments.

---

## 1. Local Development Quickstart

### Prerequisites
- Python 3.11–3.14
- Node.js v18+ & NPM
- Tesseract-OCR (optional for scanned image PDFs)

### Backend Setup
```bash
# 1. Navigate to project root
cd "C:\Users\adity\OneDrive\Desktop\BCCL RAG"

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Start FastAPI ASGI Server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start Next.js Development Server
npm run dev
```

The web portal will be accessible at: `http://localhost:3000`  
FastAPI Swagger API docs: `http://localhost:8000/docs`

---

## 2. Docker & Containerized Deployment

Run the complete multi-container stack with a single command:

```bash
docker-compose up --build -d
```

Services spawned:
1. `bccl-rag-backend` (Port 8000): FastAPI REST API with Tesseract OCR pre-installed in Linux Alpine/Debian slim image.
2. `bccl-rag-frontend` (Port 3000): Next.js production SSR container.

---

## 3. Production PostgreSQL + pgvector Configuration

To switch from SQLite to PostgreSQL with `pgvector`:

1. Deploy PostgreSQL 16 with pgvector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
2. Update `.env`:
   ```env
   DATABASE_URL=postgresql://bccl_user:YourSecurePassword@localhost:5432/bccl_rag
   ```
3. Restart the backend service. SQLAlchemy will automatically create all tables and relationships.
