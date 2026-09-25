import pytest
from backend.app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

def test_password_hashing_and_verification():
    raw_pw = "BCCL@SecPass2026"
    hashed = get_password_hash(raw_pw)
    assert hashed != raw_pw
    assert verify_password(raw_pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_generation_and_decoding():
    payload = {"sub": "admin", "role": "admin", "id": 1}
    token = create_access_token(payload)
    assert isinstance(token, str)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "admin"
    assert decoded["role"] == "admin"
    assert decoded["id"] == 1
