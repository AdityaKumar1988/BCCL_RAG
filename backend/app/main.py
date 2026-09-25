import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import engine, SessionLocal, Base
from backend.app.core.security import get_password_hash
from backend.app.core.logging import logger
from backend.app.core.rate_limiter import RateLimiterMiddleware
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.ingestion.pipeline import IngestionPipeline

from backend.app.api.auth import router as auth_router
from backend.app.api.documents import router as documents_router
from backend.app.api.chat import router as chat_router, conversations_router
from backend.app.api.admin import router as admin_router
from backend.app.api.feedback import router as feedback_router

def init_db_and_seed():
    """Initializes tables, seeds default users and initial BCCL CDA knowledge documents."""
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # 1. Seed Admin User
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            logger.info("Creating default admin account (admin / admin123)...")
            admin = User(
                username="admin",
                email="admin@bccl.gov.in",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                full_name="System Administrator (BCCL Systems Dept)",
                department="Systems Department",
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # 2. Seed Standard User
        user = db.query(User).filter(User.username == "user").first()
        if not user:
            logger.info("Creating default employee user account (user / user123)...")
            user = User(
                username="user",
                email="employee@bccl.gov.in",
                hashed_password=get_password_hash("user123"),
                role="user",
                full_name="BCCL Mining Executive",
                department="Operations",
                is_active=True
            )
            db.add(user)
            db.commit()

        # 3. Seed initial BCCL CDA Rules Document if present in data/raw
        cda_pdf = os.path.join(settings.RAW_DATA_DIR, "BCCL_CDA_Rules_1978.pdf")
        if os.path.exists(cda_pdf):
            doc = db.query(Document).filter(Document.filename == "BCCL_CDA_Rules_1978.pdf").first()
            if not doc:
                logger.info("Auto-ingesting initial BCCL CDA Rules 1978 into Knowledge Base...")
                doc = Document(
                    title="BCCL Conduct, Discipline and Appeal (CDA) Rules, 1978",
                    filename="BCCL_CDA_Rules_1978.pdf",
                    file_path=cda_pdf,
                    file_size=os.path.getsize(cda_pdf),
                    mime_type="application/pdf",
                    status="UPLOADED",
                    uploaded_by=admin.id
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                
                pipeline = IngestionPipeline(db)
                pipeline.process_document(doc.id)

    except Exception as e:
        logger.error(f"Database initialization and seeding error: {e}", exc_info=True)
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db_and_seed()
    yield
    # Shutdown
    logger.info("Shutting down BCCL RAG Application Gateway")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Authentic Enterprise AI-powered RAG Knowledge Retrieval System for Bharat Coking Coal Limited (BCCL)",
    lifespan=lifespan
)

# Attach Rate Limiting Middleware
app.add_middleware(RateLimiterMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(admin_router)
app.include_router(feedback_router)

@app.get("/")
def root():
    return {
        "system": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "OPERATIONAL",
        "docs_url": "/docs",
        "organization": "Bharat Coking Coal Limited (BCCL) / Coal India Limited"
    }

@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "environment": settings.ENVIRONMENT}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
