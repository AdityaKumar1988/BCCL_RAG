import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_root_and_health():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "OPERATIONAL"
    assert "BCCL" in data["system"]

    h_resp = client.get("/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "HEALTHY"

def test_api_auth_flow():
    # Login as seeded admin
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["role"] == "admin"

    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access /api/auth/me
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin"

def test_api_documents_and_chat_flow():
    # Login as seeded user
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "user123"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List documents
    docs_resp = client.get("/api/documents", headers=headers)
    assert docs_resp.status_code == 200
    docs = docs_resp.json()
    assert len(docs) > 0
    doc_id = docs[0]["id"]

    # Send Chat Message
    chat_resp = client.post(
        "/api/chat",
        json={"message": "What are the rules for suspension?"},
        headers=headers
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "answer" in chat_data
    assert chat_data["conversation_id"] > 0
    assert chat_data["is_abstention"] is False
    assert len(chat_data["citations"]) > 0

    # Submit feedback
    fb_resp = client.post(
        "/api/feedback",
        json={"message_id": chat_data["message_id"], "rating": 1, "comment": "Accurate response with proper rule reference."},
        headers=headers
    )
    assert fb_resp.status_code == 201
    assert fb_resp.json()["rating"] == 1
