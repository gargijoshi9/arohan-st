import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, SessionLocal
from routers import schemes_router, applications_router, admin_router, documents_router
from utils.seed import seed_schemes, seed_demo_applications

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    
    # Run database seeder
    db = SessionLocal()
    try:
        seed_schemes(db)
        seed_demo_applications(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="AROHAN-ST Platform API",
    description="Scholarship/Fellowship Management Platform for Scheduled Tribe Students (MoTA schemes)",
    version="1.0.0",
    lifespan=lifespan
)

uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# CORS Configuration for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(schemes_router)
app.include_router(applications_router)
app.include_router(admin_router)
app.include_router(documents_router)

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
