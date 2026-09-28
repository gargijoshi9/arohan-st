"""Application entry point.

Start-up order:

1. Connect to MongoDB and refuse to serve if it is unreachable, so a request
   never fails later on a silent storage error.
2. Create the indexes the query patterns depend on.
3. Load scheme configuration and, on an empty database, the reference register.
4. Create the officer account from the environment on a fresh database.

Uploads are held in MongoDB GridFS, so there is no local upload directory to
prepare.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Running `python backend/main.py` must resolve the backend's own modules.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

from config import get_settings
from database import USERS, close_client, ensure_indexes, get_db, next_id, ping, utcnow
from models import ROLE_OFFICER, new_user
from routers import (
    admin_router,
    applications_router,
    auth_router,
    private_documents_router,
    schemes_router,
)
from security import hash_password, normalise_email
from utils.seed import seed_reference_records, seed_schemes

logger = logging.getLogger("arohan_st")

API_TITLE = "AROHAN-ST Platform API"
API_VERSION = "1.0.0"


def bootstrap_officer_account(db) -> str:
    """Create the officer account from the environment on a fresh database.

    The password is read from configuration and stored only as a bcrypt hash, so
    it never reaches MongoDB in plaintext. Returns a one-word outcome for the
    start-up log.
    """
    settings = get_settings()
    if not settings.has_bootstrap_officer:
        return "skipped"

    email = normalise_email(settings.bootstrap_officer_email)
    if db[USERS].find_one({"email": email}):
        return "existing"

    db[USERS].insert_one(new_user(
        user_id=next_id(db, USERS),
        email=email,
        password_hash=hash_password(settings.bootstrap_officer_password),
        role=ROLE_OFFICER,
        full_name=settings.bootstrap_officer_name,
        phone="",
    ))
    return "created"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()

    if not ping(db):
        # Fail loudly. A portal that cannot reach its database has no useful
        # behaviour, and a half-started server hides the real cause.
        raise RuntimeError(
            "Could not reach MongoDB. Check MONGODB_URI in .env and that the "
            "Atlas cluster allows this machine's IP address."
        )

    settings = get_settings()
    ensure_indexes(db)
    scheme_codes = seed_schemes(db)
    applications = seed_reference_records(db)
    officer = bootstrap_officer_account(db)

    logger.info(
        "Connected to MongoDB database '%s': %d schemes, %d seeded applications, officer account %s.",
        settings.mongodb_db,
        len(scheme_codes),
        applications,
        officer,
    )
    if officer == "skipped":
        logger.warning(
            "No officer account was created because BOOTSTRAP_OFFICER_EMAIL or "
            "BOOTSTRAP_OFFICER_PASSWORD is unset. Set them in .env before deploying."
        )
    yield
    close_client()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=API_TITLE,
        description=(
            "Scholarship and fellowship management platform for Scheduled Tribe "
            "students under Ministry of Tribal Affairs schemes."
        ),
        version=API_VERSION,
        lifespan=lifespan,
    )

    # Credentials are not sent as cookies anywhere, so the session token stays a
    # bearer token held by the frontend.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

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
            "version": API_VERSION,
            "status": "online",
            "storage": "MongoDB",
            "endpoints": {
                "schemes": "/schemes",
                "register": "/auth/register",
                "login": "/auth/login",
                "applications": "/applications",
                "review_queue": "/admin/queue",
            },
        }

    @app.get("/health")
    def health_check():
        """Report service and database health.

        Returns 503 rather than a healthy body when the database cannot be
        reached, so a load balancer or uptime check sees the real state.
        """
        try:
            db = get_db()
            reachable = ping(db)
        except PyMongoError:
            reachable = False
        if not reachable:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="The database is not reachable.")
        return {
            "status": "healthy",
            "database": "reachable",
            "checked_at": utcnow(),
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
