"""Applicant-facing application workflow: submit, attach documents, track, correct.

Every route is scoped to the signed-in applicant. Document uploads are stored
outside the web root and are only ever served back through
`/private-documents/{id}/file`, which re-checks ownership.
"""

import math
from datetime import datetime, timezone
from pathlib import Path
from secrets import randbelow
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from database import APPLICATIONS, APPLICANTS, DOCUMENTS, NOTIFICATIONS, get_db, next_id, utcnow
from models import (
    DOCUMENT_DEFICIENT,
    DOCUMENT_UPLOADED,
    LOCKED_STATUSES,
    OCR_FAILED,
    OCR_PARTIAL,
    OCR_USABLE_STATUSES,
    ROLE_APPLICANT,
    STATUS_DEFICIENT,
    STATUS_SUBMITTED,
    STATUS_UNDER_REVIEW,
    STATUS_WITHDRAWN,
)
from schemas import (
    ApplicationCorrectionRequest,
    ApplicationCreate,
    ApplicationRead,
    AwardRead,
    DocumentRead,
    NotificationRead,
    NotificationReadResult,
)
from security import Principal, normalise_email, require_applicant, require_principal
from services import storage
from services.ocr_service import process_document_ocr
from services.repository import (
    application_payload,
    application_payloads,
    award_payloads,
    configured_document_ids,
    document_payload,
    get_applicant_by_user,
    get_application,
    get_document_by_type,
    get_documents,
    get_scheme_by_code,
    list_awards,
    list_notifications,
    record_audit,
    required_document_ids,
    rule_check_documents,
    scheme_config,
)
from services.rule_engine import evaluate_application_rules

router = APIRouter(prefix="/applications", tags=["Applications"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024

# Magic-byte prefixes, so a renamed executable is rejected before OCR runs.
_FILE_SIGNATURES = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8",),
    ".jpeg": (b"\xff\xd8",),
}


# --- Helpers ---

def generate_application_no(scheme_code: str) -> str:
    return f"AROHAN-{scheme_code.upper()}-{datetime.now(timezone.utc).year}-{randbelow(100000):05d}"


def unique_application_no(db: Database, scheme_code: str) -> str:
    """Allocate an application number, retrying on the unlikely collision."""
    for _ in range(8):
        candidate = generate_application_no(scheme_code)
        if not db[APPLICATIONS].find_one({"application_no": candidate}, {"_id": 1}):
            return candidate
    return f"AROHAN-{scheme_code.upper()}-{datetime.now(timezone.utc).year}-{next_id(db, APPLICATIONS):06d}"


def owned_application(db: Database, application_id: int, principal: Principal) -> dict:
    application = get_application(db, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.get("applicant_user_id") != principal.user_id:
        raise HTTPException(status_code=403, detail="This application belongs to another account.")
    return application


def parse_annual_income(declared_fields: Dict[str, Any]) -> Optional[float]:
    raw = declared_fields.get("annual_family_income")
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Annual family income must be a number.") from exc
    if not math.isfinite(value):
        raise HTTPException(status_code=422, detail="Annual family income must be a finite number.")
    return value


def _values_match(declared_value: Any, extracted_value: Any) -> bool:
    try:
        return float(declared_value) == float(extracted_value)
    except (TypeError, ValueError):
        def normalise(value: Any) -> str:
            return " ".join(str(value).strip().casefold().split()).removeprefix("the ")
        return normalise(declared_value) == normalise(extracted_value)


def _scored_evaluation(evaluation: Dict[str, Any], description: str) -> Dict[str, Any]:
    """Recompute the indicator, pass state and summary from the mismatch list."""
    errors = sum(item["severity"] == "ERROR" for item in evaluation["mismatches"])
    warnings = sum(item["severity"] == "WARNING" for item in evaluation["mismatches"])
    evaluation["pass_fail"] = errors == 0
    evaluation["confidence_score"] = max(15.0, min(99.0, 98.0 - 20.0 * errors - 4.0 * warnings))
    evaluation["summary"] = (
        f"Rule checks flagged {errors} issue(s) and {warnings} warning(s); officer review required."
        if errors or warnings
        else f"No configured eligibility rule failures found. {len(evaluation['passed_checks'])} checks passed; "
             "documents and claims still require official verification."
    )
    return evaluation


def evaluate_with_documents(
    db: Database,
    application: dict,
    declared_fields: Dict[str, Any],
    config: Dict[str, Any],
    mismatch_description: str,
) -> Dict[str, Any]:
    """Run the rule engine over declared data, then reconcile it with extracted document fields.

    A value that the applicant declared but that the document contradicts is
    reported as an error so an officer sees the conflict rather than silently
    trusting either side.
    """
    documents = get_documents(db, application["id"])
    usable = [doc for doc in documents if doc.get("ocr_status") in OCR_USABLE_STATUSES]

    merged = dict(declared_fields)
    for document in usable:
        merged.update(document.get("parsed_fields") or {})

    evaluation = evaluate_application_rules(
        scheme_code=application.get("scheme_code", ""),
        declared_fields=merged,
        scheme_config=config,
        documents=rule_check_documents(usable),
    )

    for document in usable:
        for field, extracted_value in (document.get("parsed_fields") or {}).items():
            declared_value = declared_fields.get(field)
            if declared_value is None or str(declared_value).strip() == "":
                continue
            if not _values_match(declared_value, extracted_value):
                evaluation["mismatches"].append({
                    "field": field,
                    "label": field.replace("_", " ").title(),
                    "declared_value": f"Applicant: {declared_value}; document: {extracted_value}",
                    "expected_rule": "Application details should agree with the uploaded document",
                    "severity": "ERROR",
                    "description": mismatch_description,
                })

    for document in documents:
        ocr_status = document.get("ocr_status", "PENDING")
        if ocr_status in {"FAILED", "PENDING"}:
            evaluation["mismatches"].append({
                "field": f"doc_{document['doc_type']}_ocr",
                "label": document["doc_type"].replace("_", " ").title(),
                "declared_value": ocr_status,
                "expected_rule": "Readable document with the expected information",
                "severity": "ERROR",
                "description": document.get("failed_reason") or "Document OCR needs a clearer replacement.",
            })
        elif ocr_status == OCR_PARTIAL:
            evaluation["mismatches"].append({
                "field": f"doc_{document['doc_type']}_ocr",
                "label": document["doc_type"].replace("_", " ").title(),
                "declared_value": ocr_status,
                "expected_rule": "Expected fields extracted for officer review",
                "severity": "WARNING",
                "description": document.get("failed_reason") or "Some fields need manual officer verification.",
            })

    return _scored_evaluation(evaluation, mismatch_description)


def derive_status(evaluation: Dict[str, Any], documents: List[dict], config: Dict[str, Any]) -> str:
    """The status a submission should hold given its checks and uploaded documents."""
    required = required_document_ids(config)
    usable = {doc["doc_type"] for doc in documents if doc.get("ocr_status") in OCR_USABLE_STATUSES}
    if required - usable:
        return STATUS_DEFICIENT
    has_partial = any(doc.get("ocr_status") == OCR_PARTIAL for doc in documents)
    if not evaluation["pass_fail"] or has_partial:
        return STATUS_UNDER_REVIEW
    return STATUS_SUBMITTED


# --- Submission ---

@router.post("", response_model=ApplicationRead, status_code=201)
def submit_application(
    payload: ApplicationCreate,
    principal: Principal = Depends(require_applicant),
    db: Database = Depends(get_db),
):
    """Submit an application for the signed-in applicant and run the configured checks."""
    # An older client may still send an email. When one is supplied it must match
    # the signed-in account, and the stored email always comes from the session.
    if payload.email and normalise_email(payload.email) != principal.email:
        raise HTTPException(status_code=403, detail="Applications can only be submitted for the signed-in account.")

    scheme = get_scheme_by_code(db, payload.scheme_code)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{payload.scheme_code}' not found")

    config = scheme_config(scheme)
    full_name = payload.full_name.strip()
    phone = (payload.phone or "").strip()
    # The scheme form declares full_name, email and phone as required fields, so
    # they have to be part of the data the rule engine inspects. They are taken
    # from the signed-in account rather than trusted from the request body.
    declared_fields = dict(payload.declared_fields)
    declared_fields["full_name"] = full_name
    declared_fields["email"] = principal.email
    declared_fields["phone"] = phone
    category = declared_fields.get("category") or "ST"
    caste_number = declared_fields.get("caste_certificate_no") or None
    annual_income = parse_annual_income(declared_fields)

    # The applicant record mirrors the identity fields of the signed-in account.
    applicant = get_applicant_by_user(db, principal.user_id)
    if applicant is None:
        applicant = {
            "id": next_id(db, APPLICANTS),
            "user_id": principal.user_id,
            "full_name": full_name,
            "email": principal.email,
            "phone": phone,
            "category": category,
            "caste_certificate_no": caste_number,
            "annual_income": annual_income,
            "created_at": utcnow(),
        }
        db[APPLICANTS].insert_one(dict(applicant))
    else:
        db[APPLICANTS].update_one(
            {"id": applicant["id"]},
            {"$set": {
                "full_name": full_name,
                "phone": phone or applicant.get("phone", ""),
                "category": category,
                "caste_certificate_no": caste_number,
                "annual_income": annual_income,
            }},
        )
        applicant.update({
            "full_name": full_name,
            "phone": phone or applicant.get("phone", ""),
            "category": category,
            "caste_certificate_no": caste_number,
            "annual_income": annual_income,
        })

    evaluation = _scored_evaluation(
        evaluate_application_rules(
            scheme_code=scheme["code"],
            declared_fields=declared_fields,
            scheme_config=config,
            documents=[],
        ),
        "",
    )

    status = STATUS_SUBMITTED
    if not evaluation["pass_fail"]:
        has_document_issue = any(
            mismatch["field"].startswith(("doc_", "required_"))
            for mismatch in evaluation["mismatches"]
        )
        status = STATUS_DEFICIENT if has_document_issue else STATUS_UNDER_REVIEW

    application_id = next_id(db, APPLICATIONS)
    record = {
        "id": application_id,
        "application_no": unique_application_no(db, scheme["code"]),
        "scheme_id": scheme["id"],
        "scheme_code": scheme["code"],
        "applicant_id": applicant["id"],
        "applicant_user_id": principal.user_id,
        "declared_data": declared_fields,
        "confidence_score": evaluation["confidence_score"],
        "status": status,
        "rule_evaluation": evaluation,
        "admin_remarks": "",
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    try:
        db[APPLICATIONS].insert_one(dict(record))
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Application number collision; please submit again.") from exc

    record_audit(
        db,
        application_id=application_id,
        actor_email=principal.email,
        actor_role=principal.role,
        action="APPLICATION_SUBMITTED",
        to_status=status,
        remarks="Application received; automated checks are advisory.",
    )

    return ApplicationRead(**application_payload(db, record))


# --- Documents ---

@router.post("/{app_id:int}/documents", response_model=DocumentRead)
async def upload_document(
    app_id: int,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    principal: Principal = Depends(require_applicant),
    db: Database = Depends(get_db),
):
    """Store one required document, extract its text, and recalculate the application checks."""
    application = owned_application(db, app_id, principal)
    if application["status"] in LOCKED_STATUSES:
        raise HTTPException(status_code=409, detail="Documents cannot be changed after a final decision.")

    scheme_code = application.get("scheme_code", "")
    scheme = get_scheme_by_code(db, scheme_code)
    if not scheme:
        raise HTTPException(status_code=404, detail="The scheme for this application is no longer configured.")
    config = scheme_config(scheme)

    doc_type = doc_type.strip()
    if not configured_document_ids(config, doc_type):
        raise HTTPException(status_code=400, detail="Document type is not configured for this scheme.")

    original_name = Path(file.filename or "document").name[:255]
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload a PDF, image, or TXT file.")

    content = await file.read(MAX_FILE_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")

    for suffix, signatures in _FILE_SIGNATURES.items():
        if extension == suffix and not content.startswith(signatures):
            raise HTTPException(status_code=400, detail=f"The selected file is not a valid {suffix.upper()[1:]} file.")

    scheme_code = application.get("scheme_code", "")
    try:
        stored = storage.store(
            db,
            content,
            file_name=original_name,
            application_id=app_id,
            doc_type=doc_type,
        )
    except storage.DocumentStorageError as exc:
        raise HTTPException(status_code=503, detail="The document could not be saved. Please try again.") from exc

    ocr_result = process_document_ocr(content, doc_type, scheme_code, file_name=original_name)
    document_status = DOCUMENT_DEFICIENT if ocr_result["ocr_status"] == OCR_FAILED else DOCUMENT_UPLOADED

    existing = get_document_by_type(db, app_id, doc_type)
    common = {
        "file_name": original_name,
        "gridfs_id": stored.gridfs_id,
        "media_type": stored.media_type,
        "size_bytes": stored.length,
        "status": document_status,
        "extracted_text": ocr_result.get("extracted_text"),
        "ocr_status": ocr_result["ocr_status"],
        "ocr_confidence": ocr_result.get("ocr_confidence"),
        "extraction_method": ocr_result.get("extraction_method"),
        "parsed_fields": ocr_result.get("parsed_fields") or {},
        "failed_reason": ocr_result.get("failed_reason"),
        "uploaded_at": utcnow(),
    }
    if existing:
        document_id = existing["id"]
        # The replaced file is no longer referenced by any record, so drop its
        # chunks rather than leaving copies in the bucket.
        storage.discard(db, existing.get("gridfs_id"))
        db[DOCUMENTS].update_one({"id": document_id}, {"$set": common})
    else:
        document_id = next_id(db, DOCUMENTS)
        db[DOCUMENTS].insert_one({
            "id": document_id,
            "application_id": app_id,
            "doc_type": doc_type,
            **common,
        })

    previous_status = application["status"]
    declared_fields = application.get("declared_data") or {}
    evaluation = evaluate_with_documents(
        db,
        application,
        declared_fields,
        config,
        "The value extracted from the document differs from the applicant's declaration; officer review is required.",
    )
    documents = get_documents(db, app_id)
    new_status = derive_status(evaluation, documents, config)

    db[APPLICATIONS].update_one(
        {"id": app_id},
        {"$set": {
            "rule_evaluation": evaluation,
            "confidence_score": evaluation["confidence_score"],
            "status": new_status,
            "updated_at": utcnow(),
        }},
    )
    record_audit(
        db,
        application_id=app_id,
        actor_email=principal.email,
        actor_role=principal.role,
        action=f"DOCUMENT_UPLOADED_{doc_type.upper()}",
        from_status=previous_status,
        to_status=new_status,
        remarks=f"Extraction status: {ocr_result['ocr_status']}. Extracted values are advisory.",
    )

    return DocumentRead(**document_payload(db[DOCUMENTS].find_one({"id": document_id})))


# --- Retrieval ---

@router.get("/mine", response_model=List[ApplicationRead])
def get_my_applications(
    principal: Principal = Depends(require_applicant),
    db: Database = Depends(get_db),
):
    """Applications belonging to the signed-in applicant, newest first."""
    records = list(
        db[APPLICATIONS]
        .find({"applicant_user_id": principal.user_id})
        .sort("created_at", -1)
    )
    return [ApplicationRead(**payload) for payload in application_payloads(db, records)]


@router.get("/awards", response_model=List[AwardRead])
def get_my_awards(
    principal: Principal = Depends(require_applicant),
    db: Database = Depends(get_db),
):
    """Award and payment records for the signed-in applicant."""
    application_ids = [
        record["id"]
        for record in db[APPLICATIONS].find({"applicant_user_id": principal.user_id}, {"id": 1})
    ]
    return [AwardRead(**payload) for payload in award_payloads(db, list_awards(db, application_ids))]


@router.get("/notifications", response_model=List[NotificationRead])
def get_my_notifications(
    principal: Principal = Depends(require_applicant),
    db: Database = Depends(get_db),
):
    """Notifications addressed to the signed-in applicant."""
    applicant = get_applicant_by_user(db, principal.user_id)
    if not applicant:
        return []
    return [NotificationRead(**item) for item in list_notifications(db, applicant["id"])]


@router.post("/notifications/{notification_id:int}/read", response_model=NotificationReadResult)
def mark_notification_read(
    notification_id: int,
    principal: Principal = Depends(require_applicant),
    db: Database = Depends(get_db),
):
    """Mark one of the applicant's own notifications as read."""
    notification = db[NOTIFICATIONS].find_one({"id": notification_id})
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    applicant = get_applicant_by_user(db, principal.user_id)
    if not applicant or notification["applicant_id"] != applicant["id"]:
        raise HTTPException(status_code=403, detail="This notification belongs to another account.")
    if notification.get("read_at") is None:
        db[NOTIFICATIONS].update_one(
            {"id": notification_id},
            {"$set": {"read_at": utcnow()}},
        )
        return NotificationReadResult(id=notification_id, read_at=utcnow())
    return NotificationReadResult(id=notification_id, read_at=notification["read_at"])


@router.get("/{app_id:int}", response_model=ApplicationRead)
def get_application_status(
    app_id: int,
    principal: Principal = Depends(require_principal),
    db: Database = Depends(get_db),
):
    """Application detail, available to its applicant and to officers."""
    application = get_application(db, app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if principal.role == ROLE_APPLICANT and application.get("applicant_user_id") != principal.user_id:
        raise HTTPException(status_code=403, detail="This application belongs to another account.")
    return ApplicationRead(**application_payload(db, application))


# --- Correction and withdrawal ---

@router.patch("/{app_id:int}", response_model=ApplicationRead)
def correct_application(
    app_id: int,
    payload: ApplicationCorrectionRequest,
    principal: Principal = Depends(require_applicant),
    db: Database = Depends(get_db),
):
    """Correct a deficient application and return it to officer review."""
    application = owned_application(db, app_id, principal)
    if application["status"] != STATUS_DEFICIENT:
        raise HTTPException(status_code=409, detail="Application corrections are enabled only while deficient.")

    full_name = payload.full_name.strip()
    if not full_name:
        raise HTTPException(status_code=422, detail="Applicant name cannot be empty.")
    declared_fields = dict(payload.declared_fields)
    declared_fields["full_name"] = full_name
    declared_fields["email"] = principal.email
    declared_fields["phone"] = (payload.phone or "").strip()

    scheme = get_scheme_by_code(db, application.get("scheme_code", ""))
    if not scheme:
        raise HTTPException(status_code=404, detail="The scheme for this application is no longer configured.")
    config = scheme_config(scheme)

    annual_income = parse_annual_income(declared_fields)
    evaluation = evaluate_with_documents(
        db,
        application,
        declared_fields,
        config,
        "The corrected declaration still differs from the uploaded document; officer review is required.",
    )
    documents = get_documents(db, app_id)
    new_status = derive_status(evaluation, documents, config)

    previous_status = application["status"]
    db[APPLICATIONS].update_one(
        {"id": app_id},
        {"$set": {
            "declared_data": declared_fields,
            "confidence_score": evaluation["confidence_score"],
            "rule_evaluation": evaluation,
            "status": new_status,
            "admin_remarks": "",
            "updated_at": utcnow(),
        }},
    )
    db[APPLICANTS].update_one(
        {"id": application["applicant_id"]},
        {"$set": {
            "full_name": full_name,
            "phone": declared_fields.get("phone", ""),
            "category": declared_fields.get("category"),
            "caste_certificate_no": declared_fields.get("caste_certificate_no"),
            "annual_income": annual_income,
        }},
    )
    record_audit(
        db,
        application_id=app_id,
        actor_email=principal.email,
        actor_role=principal.role,
        action="APPLICANT_CORRECTION_SUBMITTED",
        from_status=previous_status,
        to_status=new_status,
        remarks="Applicant updated declared application details.",
    )
    return ApplicationRead(**application_payload(db, get_application(db, app_id)))


@router.post("/{app_id:int}/withdraw", response_model=ApplicationRead)
def withdraw_application(
    app_id: int,
    reason: str = "",
    principal: Principal = Depends(require_applicant),
    db: Database = Depends(get_db),
):
    """Withdraw an application that has not reached a final decision."""
    application = owned_application(db, app_id, principal)
    if application["status"] in LOCKED_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="A decided or awarded application cannot be withdrawn; contact the officer desk.",
        )
    previous_status = application["status"]
    db[APPLICATIONS].update_one(
        {"id": app_id},
        {"$set": {"status": STATUS_WITHDRAWN, "updated_at": utcnow()}},
    )
    record_audit(
        db,
        application_id=app_id,
        actor_email=principal.email,
        actor_role=principal.role,
        action="APPLICATION_WITHDRAWN",
        from_status=previous_status,
        to_status=STATUS_WITHDRAWN,
        remarks=(reason or "").strip() or "Withdrawn by the applicant.",
    )
    return ApplicationRead(**application_payload(db, get_application(db, app_id)))
