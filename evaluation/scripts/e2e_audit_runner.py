import os
import sys
import io
import time
import json
from fastapi.testclient import TestClient

# Ensure project root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.core.rate_limiter import RateLimiterMiddleware
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.audit import AuditLog
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message

def run_e2e_audit():
    print("=" * 80)
    print("RUNNING 20-STEP FORENSIC END-TO-END AUDIT")
    print("=" * 80)

    limiter = RateLimiterMiddleware.get_instance()
    if limiter:
        limiter.reset()

    client = TestClient(app)
    e2e_evidence = {}

    # Step 1: Healthcheck
    t0 = time.time()
    res_health = client.get("/health")
    e2e_evidence["step1_health"] = {
        "status_code": res_health.status_code,
        "body": res_health.json(),
        "latency_ms": round((time.time() - t0) * 1000, 2)
    }
    print(f"[Step 1] Backend Health: {res_health.status_code} {res_health.json()} ({e2e_evidence['step1_health']['latency_ms']}ms)")

    # Step 2: Login as USER
    t0 = time.time()
    res_user_login = client.post("/api/auth/login", json={"username": "user", "password": "user123"})
    user_token = res_user_login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    e2e_evidence["step2_user_login"] = {
        "status_code": res_user_login.status_code,
        "role": res_user_login.json()["role"],
        "latency_ms": round((time.time() - t0) * 1000, 2)
    }
    print(f"[Step 2] User Login: Role={e2e_evidence['step2_user_login']['role']} ({e2e_evidence['step2_user_login']['latency_ms']}ms)")

    # Step 3: Login as ADMIN
    t0 = time.time()
    res_admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    admin_token = res_admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    e2e_evidence["step3_admin_login"] = {
        "status_code": res_admin_login.status_code,
        "role": res_admin_login.json()["role"],
        "latency_ms": round((time.time() - t0) * 1000, 2)
    }
    print(f"[Step 3] Admin Login: Role={e2e_evidence['step3_admin_login']['role']} ({e2e_evidence['step3_admin_login']['latency_ms']}ms)")

    # Step 4: Admin uploads PDF
    t0 = time.time()
    pdf_path = os.path.join("data", "raw", "BCCL_CDA_Rules_1978.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    res_upload = client.post(
        "/api/admin/documents/upload",
        files={"file": ("BCCL_CDA_Rules_Audit_Test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=admin_headers
    )
    doc_id = res_upload.json()["document_id"]
    e2e_evidence["step4_upload"] = {
        "status_code": res_upload.status_code,
        "document_id": doc_id,
        "job_id": res_upload.json()["job_id"],
        "latency_ms": round((time.time() - t0) * 1000, 2)
    }
    print(f"[Step 4] Admin Upload PDF: Doc ID={doc_id}, Job ID={res_upload.json()['job_id']} ({e2e_evidence['step4_upload']['latency_ms']}ms)")

    # Step 5 & 6: Process Document Ingestion synchronously for audit
    db = SessionLocal()
    from backend.app.ingestion.pipeline import IngestionPipeline
    t0 = time.time()
    pipeline = IngestionPipeline(db)
    doc = pipeline.process_document(document_id=doc_id, job_id=res_upload.json()["job_id"])
    ingestion_latency = (time.time() - t0) * 1000
    e2e_evidence["step5_ingestion"] = {
        "doc_status": doc.status,
        "total_pages": doc.total_pages,
        "is_scanned": doc.is_scanned,
        "ingestion_latency_ms": round(ingestion_latency, 2)
    }
    print(f"[Step 5 & 6] Ingestion Pipeline Finished: Status={doc.status}, Pages={doc.total_pages} ({round(ingestion_latency, 2)}ms)")

    # Step 7, 8, 9, 10: Verify Database Chunks, Embeddings, BM25
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
    has_embeddings = all(c.embedding_json is not None for c in chunks)
    has_rules = any(c.rule_number is not None for c in chunks)
    e2e_evidence["step7_chunks"] = {
        "chunk_count": len(chunks),
        "has_dense_embeddings": has_embeddings,
        "has_rule_numbers": has_rules
    }
    print(f"[Step 7-10] Document Verification: {len(chunks)} chunks, Embeddings={has_embeddings}, Rule Numbers Tagged={has_rules}")

    # Step 11 & 12: Ask known BCCL question as USER
    t0 = time.time()
    res_chat1 = client.post(
        "/api/chat",
        json={"message": "What are the rules for suspension?"},
        headers=user_headers
    )
    chat1_data = res_chat1.json()
    conv_id = chat1_data["conversation_id"]
    e2e_evidence["step11_chat_suspension"] = {
        "status_code": res_chat1.status_code,
        "conversation_id": conv_id,
        "is_abstention": chat1_data["is_abstention"],
        "citations_count": len(chat1_data["citations"]),
        "first_citation": chat1_data["citations"][0] if chat1_data["citations"] else None,
        "latency_ms": chat1_data["latency_ms"]
    }
    print(f"[Step 11-14] Chat Query 'Suspension': Abstain={chat1_data['is_abstention']}, Citations={len(chat1_data['citations'])}, Latency={chat1_data['latency_ms']}ms")

    # Step 15 & 16: Follow-up conversational question
    t0 = time.time()
    res_chat2 = client.post(
        "/api/chat",
        json={"message": "What about major penalties?", "conversation_id": conv_id},
        headers=user_headers
    )
    chat2_data = res_chat2.json()
    e2e_evidence["step15_follow_up"] = {
        "status_code": res_chat2.status_code,
        "is_abstention": chat2_data["is_abstention"],
        "citations_count": len(chat2_data["citations"]),
        "latency_ms": chat2_data["latency_ms"]
    }
    print(f"[Step 15-16] Follow-up Chat 'Major Penalties': Abstain={chat2_data['is_abstention']}, Citations={len(chat2_data['citations'])}, Latency={chat2_data['latency_ms']}ms")

    # Step 17 & 18: Ask unsupported question (Abstention check)
    t0 = time.time()
    res_chat3 = client.post(
        "/api/chat",
        json={"message": "What is BCCL's astronaut training policy?"},
        headers=user_headers
    )
    chat3_data = res_chat3.json()
    e2e_evidence["step17_abstention"] = {
        "status_code": res_chat3.status_code,
        "is_abstention": chat3_data["is_abstention"],
        "citations_count": len(chat3_data["citations"]),
        "answer": chat3_data["answer"],
        "latency_ms": chat3_data["latency_ms"]
    }
    print(f"[Step 17-18] Unsupported Query: Abstain={chat3_data['is_abstention']}, Citations={len(chat3_data['citations'])}, Answer='{chat3_data['answer']}'")

    # Step 19 & 20: RBAC violation test (USER attempting admin action)
    t0 = time.time()
    res_unauth = client.get("/api/admin/analytics", headers=user_headers)
    e2e_evidence["step19_rbac_unauth"] = {
        "status_code": res_unauth.status_code,
        "detail": res_unauth.json().get("detail", "")
    }
    print(f"[Step 19-20] RBAC Unauthorized Check: Code={res_unauth.status_code} (Expected 403 Forbidden)")

    # Step 21: Rate Limiting Enforcement
    if limiter:
        limiter.reset()
    hit_429 = False
    for _ in range(130):
        r = client.get("/api/documents")
        if r.status_code == 429:
            hit_429 = True
            break
    e2e_evidence["step21_rate_limit"] = {"hit_429": hit_429}
    print(f"[Step 21] Rate Limiting Throttling: Hit 429={hit_429}")
    if limiter:
        limiter.reset()

    # Step 22 & 23: Audit logs and database consistency
    audit_count = db.query(AuditLog).count()
    conv_count = db.query(Conversation).count()
    msg_count = db.query(Message).count()
    e2e_evidence["step22_db_consistency"] = {
        "total_audit_logs": audit_count,
        "total_conversations": conv_count,
        "total_messages": msg_count
    }
    print(f"[Step 22-23] DB Consistency: Audit Logs={audit_count}, Conversations={conv_count}, Messages={msg_count}")

    db.close()

    # Save e2e evidence report
    evidence_path = os.path.join("evaluation", "results", "e2e_audit_evidence.json")
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(e2e_evidence, f, indent=2)

    print("=" * 80)
    print(f"E2E AUDIT COMPLETE! Evidence saved to {evidence_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_e2e_audit()
