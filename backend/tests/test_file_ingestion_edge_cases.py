import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_file_ingestion_validation():
    # Login as admin
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Attempt non-PDF upload (e.g. .exe file) -> 400 Bad Request
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00")
    res_exe = client.post(
        "/api/admin/documents/upload",
        files={"file": ("malware.exe", fake_exe, "application/x-msdownload")},
        headers=headers
    )
    assert res_exe.status_code == 400
    assert "Only PDF documents are supported" in res_exe.json()["detail"]

    # 2. Attempt empty text file disguised as PDF -> Ingestion handles error gracefully
    fake_txt = io.BytesIO(b"Plain text disguised")
    res_txt = client.post(
        "/api/admin/documents/upload",
        files={"file": ("notes.txt", fake_txt, "text/plain")},
        headers=headers
    )
    assert res_txt.status_code == 400
