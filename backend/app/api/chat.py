import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.models.audit import AuditLog
from backend.app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, MessageResponse, CitationItem
import time
from backend.app.rag.generator import RAGGenerator
from ml.inference import IntentClassifier

router = APIRouter(prefix="/api/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
def send_chat_message(
    chat_in: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_time = time.time()

    # 1. Get or create conversation
    conv = None
    if chat_in.conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == chat_in.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        title_snippet = chat_in.message.strip()[:40] + ("..." if len(chat_in.message) > 40 else "")
        conv = Conversation(
            user_id=current_user.id,
            title=title_snippet,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Record User Message
    user_msg = Message(
        conversation_id=conv.id,
        sender="user",
        content=chat_in.message.strip(),
        latency_ms=0.0,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user_msg)
    db.commit()

    # 3. Retrieve conversation history for contextual understanding
    history = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).all()

    # 4. Deep Learning Intent Classification & Routing via DistilBERT
    classifier = IntentClassifier()
    intent_res = classifier.predict(chat_in.message.strip())
    detected_intent = intent_res["intent"]
    intent_conf = intent_res["confidence"]
    is_low_conf = intent_res["is_low_confidence"]
    routing = intent_res["routing_decision"]
    target_kb = chat_in.knowledge_base or intent_res.get("suggested_knowledge_base", "BCCL_Rules")

    # 5. Handle Conversational Intents or execute Grounded RAG Generator
    if routing == "GREETING" and not is_low_conf:
        answer = "Hello! I am the official BCCL Enterprise AI Knowledge Assistant. How can I assist you with BCCL Rules, CDA provisions, suspension, misconduct, or disciplinary procedures today?"
        citations = []
        is_abstention = False
        retrieved = []
        latency_ms = (time.time() - start_time) * 1000.0
    elif routing == "GOODBYE" and not is_low_conf:
        answer = "Thank you for using the BCCL Enterprise AI Knowledge Assistant. Feel free to return whenever you need guidance on BCCL governance and rules. Have a great day!"
        citations = []
        is_abstention = False
        retrieved = []
        latency_ms = (time.time() - start_time) * 1000.0
    else:
        generator = RAGGenerator(db)
        answer, citations, is_abstention, _, retrieved = generator.generate_answer(
            query=chat_in.message,
            history=history[:-1],  # exclude just added message
            document_id=chat_in.document_id,
            knowledge_base=target_kb
        )
        latency_ms = (time.time() - start_time) * 1000.0

    # 6. Record Assistant Message
    citations_data = [c.model_dump() for c in citations]
    retrieved_summary = [{"chunk_id": c[0].id, "score": round(c[1], 4)} for c in retrieved]

    asst_msg = Message(
        conversation_id=conv.id,
        sender="assistant",
        content=answer,
        citations_json=json.dumps(citations_data),
        retrieved_chunks_json=json.dumps(retrieved_summary),
        latency_ms=latency_ms,
        created_at=datetime.now(timezone.utc)
    )
    db.add(asst_msg)
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(asst_msg)

    # 7. Audit Log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="QUERY_EXECUTED",
        resource=f"conversation/{conv.id}",
        details_json=json.dumps({
            "query": chat_in.message[:80],
            "detected_intent": detected_intent,
            "intent_confidence": intent_conf,
            "latency_ms": latency_ms,
            "is_abstention": is_abstention,
            "knowledge_base": target_kb
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
        latency_ms=round(latency_ms, 2),
        retrieval_count=len(retrieved),
        recognized_speech=chat_in.message.strip(),
        transcribed_text=chat_in.message.strip(),
        text=chat_in.message.strip(),
        detected_intent=detected_intent,
        intent=detected_intent,
        intent_confidence=intent_conf,
        confidence=intent_conf,
        knowledge_base=target_kb
    )

@router.post("/stream")
def stream_chat_message(
    chat_in: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = None
    if chat_in.conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == chat_in.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
    if not conv:
        conv = Conversation(
            user_id=current_user.id,
            title=chat_in.message[:40],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    user_msg = Message(
        conversation_id=conv.id,
        sender="user",
        content=chat_in.message,
        latency_ms=0.0,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user_msg)
    db.commit()

    history = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).all()
    generator = RAGGenerator(db)

    def event_stream():
        full_content = []
        for token in generator.generate_stream(
            chat_in.message,
            history=history[:-1],
            document_id=chat_in.document_id,
            knowledge_base=chat_in.knowledge_base
        ):
            full_content.append(token)
            yield f"data: {json.dumps({'token': token, 'conversation_id': conv.id})}\n\n"
        
        # Save assistant message at stream finish
        final_answer = "".join(full_content)
        asst_msg = Message(
            conversation_id=conv.id,
            sender="assistant",
            content=final_answer,
            latency_ms=0.0,
            created_at=datetime.now(timezone.utc)
        )
        db.add(asst_msg)
        db.commit()
        yield f"data: {json.dumps({'done': True, 'conversation_id': conv.id, 'message_id': asst_msg.id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Conversations CRUD
conversations_router = APIRouter(prefix="/api/conversations", tags=["Conversations"])

@conversations_router.get("", response_model=List[ConversationResponse])
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.updated_at.desc()).all()
    results = []
    for c in convs:
        c_resp = ConversationResponse.model_validate(c)
        c_resp.messages = []
        results.append(c_resp)
    return results

@conversations_router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    messages = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).all()
    msg_responses = []
    for m in messages:
        citations = []
        if m.citations_json:
            try:
                c_list = json.loads(m.citations_json)
                citations = [CitationItem(**item) for item in c_list]
            except Exception:
                citations = []
        
        msg_resp = MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            sender=m.sender,
            content=m.content,
            citations=citations,
            latency_ms=m.latency_ms,
            created_at=m.created_at
        )
        msg_responses.append(msg_resp)

    conv_resp = ConversationResponse.model_validate(conv)
    conv_resp.messages = msg_responses
    return conv_resp

@conversations_router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return None
