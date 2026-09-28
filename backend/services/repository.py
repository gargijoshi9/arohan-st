"""Shared read and write helpers over the MongoDB collections.

Routers stay thin by delegating record assembly, audit writes and notification
writes here. The batched `application_payloads` helper exists so the review
queue does not issue three lookups per row.
"""

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pymongo import DESCENDING
from pymongo.database import Database

from database import (
    APPLICATIONS,
    APPLICANTS,
    AUDIT_EVENTS,
    AWARDS,
    AWARD_PAYMENTS,
    DOCUMENTS,
    NOTIFICATIONS,
    SCHEMES,
    next_id,
    strip_mongo_id,
    utcnow,
)
from models import (
    OCR_USABLE_STATUSES,
    ROLE_APPLICANT,
    new_audit_event,
    new_notification,
)


# --- Schemes ---

def list_schemes(db: Database) -> List[dict]:
    return list(db[SCHEMES].find().sort("code", 1))


def get_scheme_by_id(db: Database, scheme_id: int) -> Optional[dict]:
    return db[SCHEMES].find_one({"id": scheme_id})


def get_scheme_by_code(db: Database, code: str) -> Optional[dict]:
    return db[SCHEMES].find_one({"code": code.strip().upper()})


def scheme_config(scheme: Optional[dict]) -> Dict[str, Any]:
    """Return the parsed rule configuration for a scheme document."""
    if not scheme:
        return {}
    config = scheme.get("config")
    if isinstance(config, dict):
        return config
    if isinstance(config, str) and config:
        return json.loads(config)
    return {}


# --- Applicants ---

def get_applicant_by_user(db: Database, user_id: int) -> Optional[dict]:
    return db[APPLICANTS].find_one({"user_id": user_id})


def get_applicant_by_email(db: Database, email: str) -> Optional[dict]:
    return db[APPLICANTS].find_one({"email": email.strip().lower()})


def get_applicant(db: Database, applicant_id: int) -> Optional[dict]:
    return db[APPLICANTS].find_one({"id": applicant_id})


# --- Applications ---

def get_application(db: Database, application_id: int) -> Optional[dict]:
    return db[APPLICATIONS].find_one({"id": application_id})


def private_document_url(document: Optional[dict]) -> Optional[str]:
    """The authorised download path for a stored document, or None if absent.

    Uploaded files live in MongoDB GridFS rather than on a filesystem path, so
    there is no stored location to validate here: a document is downloadable
    exactly when a GridFS reference exists on the record. The route it resolves
    to re-checks ownership before streaming anything.
    """
    if not document:
        return None
    if document.get("gridfs_id") is None:
        return None
    return f"/private-documents/{document['id']}/file"


def document_payload(document: dict) -> dict:
    parsed = document.get("parsed_fields")
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError:
            parsed = None
    return {
        "id": document["id"],
        "doc_type": document["doc_type"],
        "file_name": document["file_name"],
        "file_path": private_document_url(document),
        "status": document.get("status", "UPLOADED"),
        "extracted_text": document.get("extracted_text"),
        "ocr_status": document.get("ocr_status", "PENDING"),
        "ocr_confidence": document.get("ocr_confidence"),
        "extraction_method": document.get("extraction_method"),
        "parsed_fields": parsed,
        "failed_reason": document.get("failed_reason"),
        "uploaded_at": document.get("uploaded_at") or utcnow(),
    }


def application_payloads(db: Database, applications: Sequence[dict]) -> List[dict]:
    """Serialise applications with their scheme, applicant and documents resolved."""
    if not applications:
        return []

    scheme_ids = {item["scheme_id"] for item in applications}
    applicant_ids = {item["applicant_id"] for item in applications}
    application_ids = [item["id"] for item in applications]

    schemes = {
        doc["id"]: doc
        for doc in db[SCHEMES].find({"id": {"$in": list(scheme_ids)}})
    }
    applicants = {
        doc["id"]: doc
        for doc in db[APPLICANTS].find({"id": {"$in": list(applicant_ids)}})
    }
    documents_by_application: Dict[int, List[dict]] = {}
    for document in db[DOCUMENTS].find({"application_id": {"$in": application_ids}}).sort("id", 1):
        documents_by_application.setdefault(document["application_id"], []).append(document)

    payloads = []
    for application in applications:
        scheme = schemes.get(application["scheme_id"])
        applicant = applicants.get(application["applicant_id"])
        payloads.append({
            "id": application["id"],
            "application_no": application["application_no"],
            "scheme_id": application["scheme_id"],
            "scheme_code": scheme["code"] if scheme else "UNKNOWN",
            "scheme_name": scheme["name"] if scheme else "Scholarship",
            "applicant_id": application["applicant_id"],
            "applicant_name": applicant["full_name"] if applicant else "Applicant",
            "applicant_email": applicant["email"] if applicant else "",
            "declared_data": application.get("declared_data") or {},
            "confidence_score": application.get("confidence_score", 0.0),
            "status": application["status"],
            "ai_evaluation": application.get("rule_evaluation"),
            "admin_remarks": application.get("admin_remarks"),
            "created_at": application.get("created_at") or utcnow(),
            "updated_at": application.get("updated_at") or application.get("created_at") or utcnow(),
            "documents": [document_payload(doc) for doc in documents_by_application.get(application["id"], [])],
            "merit_score": application.get("merit_score"),
            "selection_rank": application.get("selection_rank"),
        })
    return payloads


def application_payload(db: Database, application: dict) -> dict:
    return application_payloads(db, [application])[0]


# --- Application documents ---

def get_documents(db: Database, application_id: int) -> List[dict]:
    return list(db[DOCUMENTS].find({"application_id": application_id}).sort("id", 1))


def get_document(db: Database, document_id: int) -> Optional[dict]:
    return db[DOCUMENTS].find_one({"id": document_id})


def get_document_by_type(db: Database, application_id: int, doc_type: str) -> Optional[dict]:
    return db[DOCUMENTS].find_one({"application_id": application_id, "doc_type": doc_type})


def usable_documents(db: Database, application_id: int) -> List[dict]:
    """Documents whose extracted fields are usable for rule comparison."""
    return list(db[DOCUMENTS].find({
        "application_id": application_id,
        "ocr_status": {"$in": list(OCR_USABLE_STATUSES)},
    }))


def rule_check_documents(documents: Iterable[dict]) -> List[dict]:
    """The compact document list the rule engine expects."""
    return [
        {"doc_type": document["doc_type"], "file_name": document["file_name"]}
        for document in documents
    ]


# --- Required document identifiers ---

def required_document_ids(config: Dict[str, Any], required_only: bool = True) -> set:
    return {
        item["id"]
        for item in config.get("required_documents", [])
        if isinstance(item, dict) and item.get("id")
        and (item.get("required") or not required_only)
    }


def verified_document_types(documents: Iterable[dict]) -> set:
    return {document["doc_type"] for document in documents if document.get("status") == "VERIFIED"}


def configured_document_ids(config: Dict[str, Any], doc_type: str) -> bool:
    return doc_type in required_document_ids(config, required_only=False)


# --- Audit trail ---

def record_audit(
    db: Database,
    *,
    application_id: int,
    actor_email: str,
    actor_role: str,
    action: str,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    remarks: str = "",
) -> dict:
    event = new_audit_event(
        event_id=next_id(db, AUDIT_EVENTS),
        application_id=application_id,
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )
    db[AUDIT_EVENTS].insert_one(dict(event))
    return event


def audit_history(db: Database, application_id: int) -> List[dict]:
    events = db[AUDIT_EVENTS].find({"application_id": application_id}).sort("created_at", 1)
    return [strip_mongo_id(event) for event in events]


# --- Notifications ---

def notify(
    db: Database,
    *,
    applicant_id: int,
    application_id: int,
    title: str,
    message: str,
) -> dict:
    notification = new_notification(
        notification_id=next_id(db, NOTIFICATIONS),
        applicant_id=applicant_id,
        application_id=application_id,
        title=title,
        message=message,
    )
    db[NOTIFICATIONS].insert_one(dict(notification))
    return notification


def list_notifications(db: Database, applicant_id: int) -> List[dict]:
    return [
        strip_mongo_id(item)
        for item in db[NOTIFICATIONS]
        .find({"applicant_id": applicant_id})
        .sort("created_at", DESCENDING)
    ]


# --- Awards ---

def award_payloads(db: Database, awards: Sequence[dict]) -> List[dict]:
    if not awards:
        return []

    award_ids = [award["id"] for award in awards]
    payments_by_award: Dict[int, List[dict]] = {}
    for payment in db[AWARD_PAYMENTS].find({"award_id": {"$in": award_ids}}).sort("id", 1):
        payments_by_award.setdefault(payment["award_id"], []).append(payment)

    application_ids = [award["application_id"] for award in awards]
    applications = {
        doc["id"]: doc
        for doc in db[APPLICATIONS].find({"id": {"$in": application_ids}})
    }
    referenced = [applications[app_id] for app_id in application_ids if app_id in applications]
    scheme_by_application: Dict[int, dict] = {}
    applicant_by_id: Dict[int, dict] = {}
    if referenced:
        scheme_ids = {item["scheme_id"] for item in referenced}
        applicant_ids = {item["applicant_id"] for item in referenced}
        scheme_by_application = {
            doc["id"]: doc for doc in db[SCHEMES].find({"id": {"$in": list(scheme_ids)}})
        }
        applicant_by_id = {
            doc["id"]: doc for doc in db[APPLICANTS].find({"id": {"$in": list(applicant_ids)}})
        }

    payloads = []
    for award in awards:
        application = applications.get(award["application_id"])
        applicant = applicant_by_id.get(application["applicant_id"]) if application else None
        scheme = scheme_by_application.get(application["scheme_id"]) if application else None
        payloads.append({
            "id": award["id"],
            "application_id": award["application_id"],
            "application_no": application["application_no"] if application else "",
            "applicant_name": applicant["full_name"] if applicant else "",
            "applicant_email": applicant["email"] if applicant else "",
            "scheme_code": scheme["code"] if scheme else "",
            "award_status": award.get("award_status", "ACTIVE"),
            "approved_amount": award.get("approved_amount"),
            "currency": award.get("currency", "INR"),
            "start_date": award.get("start_date"),
            "end_date": award.get("end_date"),
            "next_review_date": award.get("next_review_date"),
            "officer_remarks": award.get("officer_remarks"),
            "updated_at": award.get("updated_at") or utcnow(),
            "payments": [
                {
                    "id": payment["id"],
                    "period": payment["period"],
                    "amount": payment["amount"],
                    "status": payment["status"],
                    "reference": payment.get("reference"),
                    "paid_at": payment.get("paid_at"),
                }
                for payment in payments_by_award.get(award["id"], [])
            ],
        })
    return payloads


def award_payload(db: Database, award: dict) -> dict:
    return award_payloads(db, [award])[0]


def get_award_by_application(db: Database, application_id: int) -> Optional[dict]:
    return db[AWARDS].find_one({"application_id": application_id})


def get_award(db: Database, award_id: int) -> Optional[dict]:
    return db[AWARDS].find_one({"id": award_id})


def list_awards(db: Database, application_ids: Optional[Sequence[int]] = None) -> List[dict]:
    query = {"application_id": {"$in": list(application_ids)}} if application_ids is not None else {}
    return list(db[AWARDS].find(query).sort("updated_at", DESCENDING))


def committed_payment_total(db: Database, award_id: int, states: Sequence[str]) -> float:
    """Sum of payment amounts that still count against the approved award total."""
    pipeline = [
        {"$match": {"award_id": award_id, "status": {"$in": list(states)}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    result = list(db[AWARD_PAYMENTS].aggregate(pipeline))
    return float(result[0]["total"]) if result else 0.0


__all__ = [
    "ROLE_APPLICANT",
    "application_payload",
    "application_payloads",
    "audit_history",
    "award_payload",
    "award_payloads",
    "committed_payment_total",
    "configured_document_ids",
    "document_payload",
    "get_applicant",
    "get_applicant_by_email",
    "get_applicant_by_user",
    "get_application",
    "get_award",
    "get_award_by_application",
    "get_document",
    "get_document_by_type",
    "get_documents",
    "get_scheme_by_code",
    "get_scheme_by_id",
    "list_awards",
    "list_notifications",
    "list_schemes",
    "notify",
    "private_document_url",
    "record_audit",
    "required_document_ids",
    "rule_check_documents",
    "scheme_config",
    "usable_documents",
    "verified_document_types",
]
