from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.core.database import get_db
from backend.app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from backend.app.models.user import User
from backend.app.models.audit import AuditLog
from backend.app.schemas.auth import UserCreate, UserLogin, Token, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter((User.username == user_in.username) | (User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered"
        )
    
    # Restrict admin role assignment on public register if admin exists
    role = "user"
    if user_in.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count == 0:
            role = "admin"
        else:
            role = "user"

    hashed_pw = get_password_hash(user_in.password)
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        role=role,
        full_name=user_in.full_name,
        department=user_in.department or "General",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit
    audit = AuditLog(
        user_id=user.id,
        username=user.username,
        action="USER_REGISTERED",
        resource=f"user/{user.id}",
        details_json=f'{{"role": "{user.role}"}}',
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()

    return user

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role, "id": user.id})
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        full_name=user.full_name
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
