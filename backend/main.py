import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import inspect

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, SessionLocal
from models import Application, Award
from routers import schemes_router, applications_router, admin_router, auth_router, private_documents_router
from utils.seed import seed_schemes, seed_demo_applications

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    ensure_document_ocr_columns()
    ensure_workflow_columns()
    
    # Run database seeder
    db = SessionLocal()
    try:
        seed_schemes(db)
        seed_demo_applications(db)
        seed_demo_awards(db)
    finally:
        db.close()
    yield


def ensure_document_ocr_columns():
    columns = {column["name"] for column in inspect(engine).get_columns("documents")}
    new_columns = {
        "extracted_text": "TEXT",
        "ocr_status": "VARCHAR(50)",
        "ocr_confidence": "FLOAT",
        "extraction_method": "VARCHAR(50)",
        "parsed_fields": "TEXT",
        "failed_reason": "TEXT",
    }
    with engine.begin() as connection:
        for name, column_type in new_columns.items():
            if name not in columns:
                connection.exec_driver_sql(f"ALTER TABLE documents ADD COLUMN {name} {column_type}")
        connection.exec_driver_sql("UPDATE documents SET ocr_status = 'PENDING' WHERE ocr_status IS NULL")


def ensure_workflow_columns():
    columns = {column["name"] for column in inspect(engine).get_columns("applications")}
    new_columns = {
        "merit_score": "FLOAT",
        "selection_rank": "INTEGER",
        "selected_at": "DATETIME",
    }
    with engine.begin() as connection:
        for name, column_type in new_columns.items():
            if name not in columns:
                connection.exec_driver_sql(f"ALTER TABLE applications ADD COLUMN {name} {column_type}")


def seed_demo_awards(db):
    for app_record in db.query(Application).filter(Application.status == "APPROVED").all():
        exists = db.query(Award.id).filter(Award.application_id == app_record.id).first()
        if not exists:
            db.add(Award(
                application_id=app_record.id,
                award_status="ACTIVE",
                officer_remarks="Seeded demo record; confirm actual sanction details before use.",
            ))
    db.commit()

app = FastAPI(
    title="AROHAN-ST Platform API",
    description="Scholarship/Fellowship Management Platform for Scheduled Tribe Students (MoTA schemes)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration for frontend access
allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(schemes_router)
app.include_router(applications_router)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(private_documents_router)

@app.get("/")
def root():
    return {
        "platform": "AROHAN-ST",
        "ministry": "Ministry of Tribal Affairs, Government of India",
        "version": "1.0.0",
        "status": "online",
        "schemes_supported": ["NFST", "NOS", "TOP_CLASS", "POST_MATRIC", "PRE_MATRIC"],
        "endpoints": {
            "schemes": "/schemes",
            "applications": "/applications",
            "admin_queue": "/admin/queue"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
