import os
import json
import time
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.core.logging import logger
from backend.app.models.user import User
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.models.audit import AuditLog
from backend.app.schemas.chat import ChatResponse, CitationItem
from backend.app.rag.generator import RAGGenerator
from backend.app.providers.speech_provider import SpeechRecognitionProvider
from ml.inference import IntentClassifier

router = APIRouter(prefix="/api/voice", tags=["Voice & Intent Assistant"])

class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration_seconds: float
    is_empty: bool
    latency_ms: float

class ClassifyRequest(BaseModel):
    text: str
    threshold: Optional[float] = 0.50

class ClassifyResponse(BaseModel):
    intent: str
    confidence: float
    is_low_confidence: bool
    routing_decision: str
    suggested_knowledge_base: str
    probabilities: dict

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_voice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Convert uploaded voice/audio recording to recognized speech text using Whisper.
    """
    allowed_exts = [".wav", ".mp3", ".ogg", ".webm", ".m4a", ".flac"]
    filename = file.filename or "recording.wav"
    ext = os.path.splitext(filename.lower())[1]

    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{ext}'. Supported formats: {', '.join(allowed_exts)}"
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file uploaded.")
    if len(content) > 25 * 1024 * 1024:  # 25 MB max
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file exceeds 25MB limit.")

    provider = SpeechRecognitionProvider()
    try:
        result = provider.transcribe(content)
        return TranscribeResponse(**result)
    except Exception as e:
        logger.error(f"Voice transcription error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech recognition failed: {str(e)}"
        )

@router.post("/classify", response_model=ClassifyResponse)
def classify_intent(
    req: ClassifyRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Classify query intent using the fine-tuned DistilBERT Deep Learning model.
    """
    classifier = IntentClassifier()
    result = classifier.predict(req.text, threshold=req.threshold)
    return ClassifyResponse(**result)

@router.post("/chat", response_model=ChatResponse)
async def voice_chat(
    file: UploadFile = File(...),
    conversation_id: Optional[int] = Form(None),
    knowledge_base: Optional[str] = Form("BCCL_Rules"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    End-to-End Voice Chat Pipeline:
    Voice Input -> Speech Recognition (Whisper) -> Recognized Text ->
    Deep Learning Intent Classifier (DistilBERT) -> Intent Router ->
    Selected Knowledge Base -> Hybrid RAG Retrieval -> Grounded Answer + Citations.
    """
    start_time = time.time()

    # Step 1: Transcribe Audio
    allowed_exts = [".wav", ".mp3", ".ogg", ".webm", ".m4a", ".flac"]
    filename = file.filename or "recording.wav"
    ext = os.path.splitext(filename.lower())[1]
    if ext not in allowed_exts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported audio format '{ext}'")

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio recording.")
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file exceeds 25MB limit.")

    speech_provider = SpeechRecognitionProvider()
    transcription = speech_provider.transcribe(audio_bytes)
    recognized_text = transcription.get("text", "").strip()

    if not recognized_text:
        return ChatResponse(
            conversation_id=conversation_id or 0,
            message_id=0,
            answer="I could not detect any clear speech in your recording. Please try speaking again.",
            citations=[],
            is_abstention=True,
            latency_ms=round((time.time() - start_time) * 1000.0, 2),
            retrieval_count=0,
            recognized_speech="",
            transcribed_text="",
            text="",
            detected_intent="unknown",
            intent="unknown",
            intent_confidence=0.0,
            confidence=0.0,
            knowledge_base=knowledge_base
        )

    # Step 2: Deep Learning Intent Classification
    classifier = IntentClassifier()
    intent_res = classifier.predict(recognized_text)
    detected_intent = intent_res["intent"]
    intent_conf = intent_res["confidence"]
    is_low_conf = intent_res["is_low_confidence"]
    routing = intent_res["routing_decision"]

    # Step 3: Handle Conversational Intents (Greeting / Goodbye / Out of Scope)
    target_kb = knowledge_base or intent_res.get("suggested_knowledge_base", "BCCL_Rules")

    # Step 4: Get or Create Conversation
    conv = None
    if conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()

    if not conv:
        snippet = recognized_text[:40] + ("..." if len(recognized_text) > 40 else "")
        conv = Conversation(
            user_id=current_user.id,
            title=f"🎙️ {snippet}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # Step 5: Save User Message (Voice Recognized Text)
    user_msg = Message(
        conversation_id=conv.id,
        sender="user",
        content=f"🎙️ {recognized_text}",
        latency_ms=transcription.get("latency_ms", 0.0),
        created_at=datetime.now(timezone.utc)
    )
    db.add(user_msg)
    db.commit()

    # Step 6: Handle specific conversational responses or execute RAG
    if routing == "GREETING" and not is_low_conf:
        answer = "Hello! I am the official BCCL Enterprise AI Knowledge Assistant. How can I assist you with BCCL Rules, CDA provisions, suspension, misconduct, or disciplinary procedures today?"
        citations = []
        is_abstention = False
        retrieved = []
    elif routing == "GOODBYE" and not is_low_conf:
        answer = "Thank you for using the BCCL Enterprise AI Knowledge Assistant. Feel free to return whenever you need guidance on BCCL governance and rules. Have a great day!"
        citations = []
        is_abstention = False
        retrieved = []
    else:
        # Step 7: Execute Grounded RAG Generator
        history = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).all()
        generator = RAGGenerator(db)
        answer, citations, is_abstention, _, retrieved = generator.generate_answer(
            query=recognized_text,
            history=history[:-1],
            knowledge_base=target_kb
        )

    # Step 8: Save Assistant Message
    citations_data = [c.model_dump() for c in citations]
    retrieved_summary = [{"chunk_id": c[0].id, "score": round(c[1], 4)} for c in retrieved]
    total_latency_ms = (time.time() - start_time) * 1000.0

    asst_msg = Message(
        conversation_id=conv.id,
        sender="assistant",
        content=answer,
        citations_json=json.dumps(citations_data),
        retrieved_chunks_json=json.dumps(retrieved_summary),
        latency_ms=total_latency_ms,
        created_at=datetime.now(timezone.utc)
    )
    db.add(asst_msg)
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(asst_msg)

    # Step 9: Audit Log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="VOICE_QUERY_EXECUTED",
        resource=f"conversation/{conv.id}",
        details_json=json.dumps({
            "recognized_speech": recognized_text[:100],
            "detected_intent": detected_intent,
            "intent_confidence": intent_conf,
            "knowledge_base": target_kb,
            "latency_ms": total_latency_ms,
            "is_abstention": is_abstention
        }),
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()

    return ChatResponse(
        conversation_id=conv.id,
        message_id=asst_msg.id,
        answer=answer,
        citations=citations,
        is_abstention=is_abstention,
        latency_ms=round(total_latency_ms, 2),
        retrieval_count=len(retrieved),
        recognized_speech=recognized_text,
        transcribed_text=recognized_text,
        text=recognized_text,
        detected_intent=detected_intent,
        intent=detected_intent,
        intent_confidence=intent_conf,
        confidence=intent_conf,
        knowledge_base=target_kb
    )
