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
from backend.app.api.voice import router as voice_router

def init_db_and_seed():
    """Initializes tables, seeds default users and initial BCCL CDA knowledge documents."""
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # 1. Seed Admin User
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_pwd = os.environ.get("ADMIN_DEFAULT_PASSWORD", "admin123")
            logger.info("Initializing system administrator account (admin)...")
            admin = User(
                username="admin",
                email="admin@bccl.gov.in",
                hashed_password=get_password_hash(admin_pwd),
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
            user_pwd = os.environ.get("USER_DEFAULT_PASSWORD", "user123")
            logger.info("Initializing standard employee user account (user)...")
            user = User(
                username="user",
                email="employee@bccl.gov.in",
                hashed_password=get_password_hash(user_pwd),
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

        # 4. Seed BCCL_Rules knowledge base from new_data if not yet present
        new_data_pdf = os.path.join(settings.BASE_DIR, "new_data", "CDA_Rules_1978_amended_upto_July_2006_10052018-ocr.pdf")
        if os.path.exists(new_data_pdf):
            bccl_doc = db.query(Document).filter(Document.knowledge_base == "BCCL_Rules").first()
            if not bccl_doc:
                logger.info("Auto-ingesting new_data BCCL_Rules into Knowledge Base...")
                bccl_doc = Document(
                    title="BCCL Conduct, Discipline & Appeal Rules, 1978 (Amended upto July 2006)",
                    filename="CDA_Rules_1978_amended_upto_July_2006_10052018-ocr.pdf",
                    file_path=new_data_pdf,
                    file_size=os.path.getsize(new_data_pdf),
                    mime_type="application/pdf",
                    status="UPLOADED",
                    knowledge_base="BCCL_Rules",
                    uploaded_by=admin.id if admin else 1
                )
                db.add(bccl_doc)
                db.commit()
                db.refresh(bccl_doc)
                pipeline = IngestionPipeline(db)
                pipeline.process_document(bccl_doc.id)

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

# Configure CORS (merging local defaults and production FRONTEND_URL)
cors_origins = list(settings.ALLOWED_ORIGINS)
if settings.FRONTEND_URL:
    for u in settings.FRONTEND_URL.split(","):
        clean_u = u.strip().rstrip("/")
        if clean_u and clean_u not in cors_origins:
            cors_origins.append(clean_u)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
app.include_router(voice_router)

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
