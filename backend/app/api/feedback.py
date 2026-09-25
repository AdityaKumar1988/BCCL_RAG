from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.models.message import Message
from backend.app.models.feedback import Feedback
from backend.app.models.audit import AuditLog
from backend.app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    fb_in: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    msg = db.query(Message).filter(Message.id == fb_in.message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    # Check if feedback already exists for this message
    existing_fb = db.query(Feedback).filter(Feedback.message_id == fb_in.message_id, Feedback.user_id == current_user.id).first()
    if existing_fb:
        existing_fb.rating = fb_in.rating
        existing_fb.comment = fb_in.comment
        db.commit()
        db.refresh(existing_fb)
        return existing_fb

    feedback = Feedback(
        message_id=fb_in.message_id,
        user_id=current_user.id,
        rating=fb_in.rating,
        comment=fb_in.comment,
        created_at=datetime.now(timezone.utc)
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    # Log audit
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="FEEDBACK_SUBMITTED",
        resource=f"message/{fb_in.message_id}",
        details_json=f'{{"rating": {fb_in.rating}}}',
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()

    return feedback
