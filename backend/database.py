"""MongoDB access layer.

The application stores every record in MongoDB. This module owns the single
`MongoClient`, exposes the database handle to request handlers, provides the
atomic identifier sequence, and creates the indexes the queries rely on.

Records keep an explicit integer `id` alongside Mongo's own `_id`. The integer
sequence keeps every identifier stable and human-readable in URLs, CSV reports
and audit records while Mongo still enforces uniqueness through an index.
"""

import threading
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.database import Database
from pymongo.errors import PyMongoError

from config import UPLOAD_DIR, get_settings

# Collection names, kept in one place so routers never hard-code strings.
USERS = "users"
SCHEMES = "schemes"
APPLICANTS = "applicants"
APPLICATIONS = "applications"
DOCUMENTS = "documents"
AUDIT_EVENTS = "audit_events"
NOTIFICATIONS = "notifications"
AWARDS = "awards"
AWARD_PAYMENTS = "award_payments"
COUNTERS = "counters"

ALL_COLLECTIONS = (
    USERS,
    SCHEMES,
    APPLICANTS,
    APPLICATIONS,
    DOCUMENTS,
    AUDIT_EVENTS,
    NOTIFICATIONS,
    AWARDS,
    AWARD_PAYMENTS,
)

_client: Optional[MongoClient] = None
_client_lock = threading.Lock()


def utcnow() -> datetime:
    """Timezone-aware current time.

    MongoDB stores instants in UTC. Keeping the offset attached means the API
    serialises timestamps with an explicit `Z`, so the browser never has to
    guess a timezone the way it does with a naive string.
    """
    return datetime.now(timezone.utc)


def get_client() -> MongoClient:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                settings = get_settings()
                _client = MongoClient(
                    settings.mongodb_uri,
                    appname="AROHAN-ST",
                    serverSelectionTimeoutMS=10_000,
                    connectTimeoutMS=10_000,
                    tz_aware=True,
                )
    return _client


def get_db() -> Database:
    """FastAPI dependency: the configured application database."""
    return get_client()[get_settings().mongodb_db]


def ping(db: Database) -> bool:
    try:
        db.command("ping")
        return True
    except PyMongoError:
        return False


def next_id(db: Database, collection: str) -> int:
    """Atomically allocate the next integer identifier for a collection."""
    document = db[COUNTERS].find_one_and_update(
        {"_id": collection},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(document["seq"])


def strip_mongo_id(document: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """Copy a Mongo document without the internal `_id` field."""
    if document is None:
        return None
    return {key: value for key, value in document.items() if key != "_id"}


def ensure_indexes(db: Database) -> None:
    """Create every index the query patterns depend on. Safe to call repeatedly."""
    db[USERS].create_index([("email", ASCENDING)], unique=True, name="uniq_user_email")
    db[USERS].create_index([("role", ASCENDING)], name="user_role")

    db[SCHEMES].create_index([("code", ASCENDING)], unique=True, name="uniq_scheme_code")

    db[APPLICANTS].create_index([("email", ASCENDING)], name="applicant_email")
    db[APPLICANTS].create_index([("user_id", ASCENDING)], unique=True, name="uniq_applicant_user")

    db[APPLICATIONS].create_index([("application_no", ASCENDING)], unique=True, name="uniq_application_no")
    db[APPLICATIONS].create_index([("applicant_id", ASCENDING)], name="application_applicant")
    db[APPLICATIONS].create_index([("scheme_id", ASCENDING)], name="application_scheme")
    db[APPLICATIONS].create_index([("status", ASCENDING)], name="application_status")
    db[APPLICATIONS].create_index(
        [("confidence_score", DESCENDING), ("created_at", DESCENDING)],
        name="application_queue_sort",
    )
    db[APPLICATIONS].create_index([("created_at", DESCENDING)], name="application_created")

    db[DOCUMENTS].create_index(
        [("application_id", ASCENDING), ("doc_type", ASCENDING)],
        unique=True,
        name="uniq_document_per_type",
    )
    db[DOCUMENTS].create_index([("application_id", ASCENDING)], name="document_application")

    db[AUDIT_EVENTS].create_index(
        [("application_id", ASCENDING), ("created_at", ASCENDING)],
        name="audit_by_application",
    )

    db[NOTIFICATIONS].create_index(
        [("applicant_id", ASCENDING), ("created_at", DESCENDING)],
        name="notifications_by_applicant",
    )

    db[AWARDS].create_index([("application_id", ASCENDING)], unique=True, name="uniq_award_per_application")
    db[AWARDS].create_index([("award_status", ASCENDING)], name="award_status")

    db[AWARD_PAYMENTS].create_index([("award_id", ASCENDING)], name="payment_by_award")
    db[AWARD_PAYMENTS].create_index([("status", ASCENDING)], name="payment_status")


def ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def close_client() -> None:
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None
