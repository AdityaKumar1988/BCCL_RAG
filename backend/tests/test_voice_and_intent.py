import os
import io
import wave
import struct
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.rag.generator import RAGGenerator
from backend.app.providers.speech_provider import SpeechRecognitionProvider
from ml.inference import IntentClassifier

client = TestClient(app)

def get_auth_token(username: str = "user", password: str = "user123") -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]

def create_synthetic_wav(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a clean audio WAV file with real spoken speech, falling back to PCM tone."""
    try:
        import subprocess, tempfile
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        f.close()
        ps = f"""Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SetOutputToWaveFile('{f.name.replace(os.sep, "/")}')
$s.Speak('What are the rules regarding suspension?')
$s.Dispose()
"""
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True, capture_output=True)
        with open(f.name, "rb") as audio_file:
            data = audio_file.read()
        if os.path.exists(f.name):
            os.remove(f.name)
        if len(data) > 44:
            return data
    except Exception:
        pass

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        # Generate 440 Hz tone
        num_samples = int(duration_seconds * sample_rate)
        for i in range(num_samples):
            val = int(10000.0 * struct.unpack("f", struct.pack("f", float(i % 100) / 100.0))[0])
            wav_file.writeframesraw(struct.pack("<h", min(max(val, -32767), 32767)))
    return buf.getvalue()

# 1. BCCL_Rules Ingestion Test
def test_bccl_rules_ingestion():
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.knowledge_base == "BCCL_Rules").first()
        assert doc is not None, "BCCL_Rules document should exist in database"
        assert doc.status == "READY", f"Document status should be READY, got {doc.status}"
        
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        assert len(chunks) > 0, "BCCL_Rules document should contain chunks"
        assert all(c.knowledge_base == "BCCL_Rules" for c in chunks), "All chunks must have knowledge_base='BCCL_Rules'"
    finally:
        db.close()

# 2. BCCL_Rules Retrieval Test
def test_bccl_rules_retrieval():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        results = retriever.retrieve("What are the rules regarding suspension?", knowledge_base="BCCL_Rules")
        assert len(results) > 0, "Retrieval on BCCL_Rules should return results"
        for chunk, score in results:
            assert chunk.knowledge_base == "BCCL_Rules", f"Expected BCCL_Rules, got {chunk.knowledge_base}"
    finally:
        db.close()

# 3. Knowledge Base Isolation Test
def test_knowledge_base_isolation():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        bccl_results = retriever.retrieve("suspension rules", knowledge_base="BCCL_Rules")
        cda_results = retriever.retrieve("suspension rules", knowledge_base="CDA_Rules")

        assert len(bccl_results) > 0, "BCCL_Rules should return chunks"
        assert len(cda_results) > 0, "CDA_Rules should return chunks"

        for chunk, _ in bccl_results:
            assert chunk.knowledge_base == "BCCL_Rules", f"Found non-BCCL chunk: {chunk.knowledge_base}"

        for chunk, _ in cda_results:
            assert chunk.knowledge_base == "CDA_Rules", f"Found non-CDA chunk: {chunk.knowledge_base}"

        # Ensure chunk IDs do not overlap between isolated results
        bccl_ids = {c[0].id for c in bccl_results}
        cda_ids = {c[0].id for c in cda_results}
        assert bccl_ids.isdisjoint(cda_ids), "BCCL and CDA chunk pools must not overlap!"
    finally:
        db.close()

# 4. Intent Classification Deep Learning Model Test
def test_distilbert_intent_classification():
    clf = IntentClassifier()
    assert clf.model is not None, "DistilBERT model must be loaded"

    # Test domain intents
    res_susp = clf.predict("What are the rules regarding suspension?")
    assert res_susp["intent"] in ["suspension", "disciplinary_procedure", "clarification_general"]
    assert "probabilities" in res_susp
    assert len(res_susp["probabilities"]) == 11

    res_misc = clf.predict("What acts of omission constitute misconduct?")
    assert res_misc["intent"] in ["misconduct", "general_conduct"]

    res_bye = clf.predict("Thank you so much, goodbye!")
    assert res_bye["intent"] in ["goodbye", "greeting"]

    res_greet = clf.predict("Hello good morning assistant")
    assert res_greet["intent"] in ["greeting", "clarification_general"]

# 5. Low-Confidence Intent Handling Test
def test_low_confidence_intent_handling():
    clf = IntentClassifier()
    # High threshold forcing low confidence
    res = clf.predict("asdkjhfasd random noise 999827", threshold=0.95)
    assert res["is_low_confidence"] is True
    assert res["routing_decision"] == "RAG_SEARCH"

# 6. Speech Recognition Empty Audio Handling
def test_voice_transcribe_empty_audio():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("empty.wav", b"", "audio/wav")}

    resp = client.post("/api/voice/transcribe", files=files, headers=headers)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()

# 7. Speech Recognition Invalid Audio Handling
def test_voice_transcribe_invalid_audio():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("test.txt", b"This is not audio", "text/plain")}

    resp = client.post("/api/voice/transcribe", files=files, headers=headers)
    assert resp.status_code == 400
    assert "unsupported" in resp.json()["detail"].lower()

# 8. Speech Recognition Valid Audio Processing
def test_voice_transcribe_valid_audio():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    wav_bytes = create_synthetic_wav(duration_seconds=1.0)
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}

    resp = client.post("/api/voice/transcribe", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "duration_seconds" in data
    assert data["duration_seconds"] >= 0.9

# 9. Voice-to-RAG Chat Pipeline Test
def test_voice_chat_pipeline():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    wav_bytes = create_synthetic_wav(duration_seconds=1.5)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}
    data = {"knowledge_base": "BCCL_Rules"}

    resp = client.post("/api/voice/chat", files=files, data=data, headers=headers)
    assert resp.status_code == 200
    res_json = resp.json()
    assert "conversation_id" in res_json
    assert "answer" in res_json
    assert "citations" in res_json
    assert "recognized_speech" in res_json
    assert "transcribed_text" in res_json
    assert "text" in res_json
    assert "detected_intent" in res_json
    assert "intent" in res_json
    assert "intent_confidence" in res_json
    assert "confidence" in res_json
    assert "latency_ms" in res_json
    # Ensure neither recognized speech nor intent are undefined or None
    assert res_json["recognized_speech"] is not None
    assert res_json["transcribed_text"] == res_json["recognized_speech"]
    assert res_json["text"] == res_json["recognized_speech"]
    assert res_json["detected_intent"] is not None
    assert res_json["intent"] == res_json["detected_intent"]
    assert res_json["intent_confidence"] is not None
    assert res_json["confidence"] == res_json["intent_confidence"]

# 9b. Voice Transcribe Endpoint Contract Test
def test_voice_transcribe_response_contract():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    wav_bytes = create_synthetic_wav(duration_seconds=1.0)
    files = {"file": ("contract_test.wav", wav_bytes, "audio/wav")}

    resp = client.post("/api/voice/transcribe", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "language" in data
    assert "duration_seconds" in data
    assert "is_empty" in data
    assert "latency_ms" in data
    assert isinstance(data["text"], str)
    assert isinstance(data["duration_seconds"], float)

# 10. Voice Follow-Up Conversation Test
def test_voice_follow_up_conversations():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    wav_bytes = create_synthetic_wav(duration_seconds=1.0)

    # First turn
    files1 = {"file": ("q1.wav", wav_bytes, "audio/wav")}
    resp1 = client.post("/api/voice/chat", files=files1, data={"knowledge_base": "BCCL_Rules"}, headers=headers)
    assert resp1.status_code == 200
    conv_id = resp1.json()["conversation_id"]
    assert conv_id > 0

    # Follow-up turn using same conversation_id
    files2 = {"file": ("q2.wav", wav_bytes, "audio/wav")}
    resp2 = client.post("/api/voice/chat", files=files2, data={"conversation_id": conv_id, "knowledge_base": "BCCL_Rules"}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["conversation_id"] == conv_id

# 11. Text Chat Knowledge Base Selection Test
def test_chat_knowledge_base_selection():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/chat",
        json={"message": "What are the rules regarding suspension?", "knowledge_base": "BCCL_Rules"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["knowledge_base"] == "BCCL_Rules"
    if data["citations"]:
        for c in data["citations"]:
            assert c["knowledge_base"] == "BCCL_Rules"

# 12. Abstention Preservation Test
def test_abstention_preserved():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/chat",
        json={"message": "What is the policy for quantum teleportation of lunar rovers?", "knowledge_base": "BCCL_Rules"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_abstention"] is True
    assert "could not find sufficient information" in data["answer"].lower()
    assert len(data["citations"]) == 0
