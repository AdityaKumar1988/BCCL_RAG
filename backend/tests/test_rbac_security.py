import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token

client = TestClient(app)

def test_rbac_user_cannot_access_admin_endpoints():
    # 1. Login as standard user
    user_login = client.post("/api/auth/login", json={"username": "user", "password": "user123"})
    assert user_login.status_code == 200
    user_token = user_login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Attempt admin endpoints as USER -> MUST return 403 Forbidden
    analytics_resp = client.get("/api/admin/analytics", headers=user_headers)
    assert analytics_resp.status_code == 403
    assert "Administrator access required" in analytics_resp.json()["detail"]

    audit_resp = client.get("/api/admin/audit-logs", headers=user_headers)
    assert audit_resp.status_code == 403

    ingest_resp = client.get("/api/admin/ingestion/1", headers=user_headers)
    assert ingest_resp.status_code == 403

    reindex_resp = client.post("/api/admin/documents/1/reindex", headers=user_headers)
    assert reindex_resp.status_code == 403

    delete_resp = client.delete("/api/admin/documents/999", headers=user_headers)
    assert delete_resp.status_code == 403

def test_rbac_admin_can_access_admin_endpoints():
    # 2. Login as admin
    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin access -> MUST return 200 OK
    analytics_resp = client.get("/api/admin/analytics", headers=admin_headers)
    assert analytics_resp.status_code == 200
    assert "total_documents" in analytics_resp.json()

    audit_resp = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    assert isinstance(audit_resp.json(), list)

def test_jwt_tampering_and_expiration():
    # 3. Missing token -> 401
    resp_no_token = client.get("/api/auth/me")
    assert resp_no_token.status_code == 401

    # 4. Malformed token -> 401
    resp_malformed = client.get("/api/auth/me", headers={"Authorization": "Bearer malformed.invalid.token"})
    assert resp_malformed.status_code == 401

    # 5. Tampered signature -> 401
    valid_token = create_access_token({"sub": "admin", "role": "admin"})
    tampered_token = valid_token[:-5] + "XXXXX"
    resp_tampered = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp_tampered.status_code == 401

    # 6. Expired token -> 401
    expired_token = create_access_token({"sub": "admin", "role": "admin"}, expires_delta=timedelta(seconds=-10))
    resp_expired = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp_expired.status_code == 401
