import json
import math
from datetime import datetime
from pathlib import Path
from secrets import randbelow
from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from models import Scheme, Applicant, Application, Document, AuditEvent, Notification, Award
from schemas import ApplicationCreate, ApplicationCorrectionRequest, ApplicationRead, DocumentRead, RuleEvaluation
from security import Principal, require_applicant, require_principal
from services.ocr_service import process_document_ocr
from services.rule_engine import evaluate_application_rules

router = APIRouter(prefix="/applications", tags=["Applications"])
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024

def generate_application_no(scheme_code: str) -> str:
    return f"AROHAN-{scheme_code.upper()}-{datetime.now().year}-{randbelow(100000):05d}"


def get_private_document_url(document: Document) -> str | None:
    if not document.file_path:
        return None
    normalized_path = document.file_path.replace("\\", "/")
    if normalized_path.startswith("/uploads/"):
        root = UPLOAD_DIR
        stored_path = root.joinpath(*Path(normalized_path).parts[2:])
    elif normalized_path.startswith("/sample-documents/"):
        root = UPLOAD_DIR.parent.parent / "docs" / "sample-documents"
        stored_path = root.joinpath(*Path(normalized_path).parts[2:])
    else:
        return None
    resolved = stored_path.resolve()
    if resolved.is_relative_to(root.resolve()) and resolved.is_file():
        return f"/private-documents/{document.id}/file"
    return None


def format_application_response(app: Application) -> ApplicationRead:
    declared_dict = json.loads(app.declared_data) if app.declared_data else {}
    ai_eval_dict = json.loads(app.ai_evaluation) if app.ai_evaluation else None
    ai_eval = RuleEvaluation(**ai_eval_dict) if ai_eval_dict else None
    
    docs = [
        DocumentRead(
            id=d.id,
            doc_type=d.doc_type,
            file_name=d.file_name,
            file_path=get_private_document_url(d),
            status=d.status,
            extracted_text=d.extracted_text,
            ocr_status=d.ocr_status,
            ocr_confidence=d.ocr_confidence,
            extraction_method=d.extraction_method,
            parsed_fields=json.loads(d.parsed_fields) if d.parsed_fields else None,
            failed_reason=d.failed_reason,
            uploaded_at=d.uploaded_at
        )
        for d in app.documents
    ]
    
    return ApplicationRead(
        id=app.id,
        application_no=app.application_no,
        scheme_id=app.scheme_id,
        scheme_code=app.scheme.code if app.scheme else "UNKNOWN",
        scheme_name=app.scheme.name if app.scheme else "Scholarship",
        applicant_id=app.applicant_id,
        applicant_name=app.applicant.full_name if app.applicant else "Applicant",
        applicant_email=app.applicant.email if app.applicant else "",
        declared_data=declared_dict,
        confidence_score=app.confidence_score,
        status=app.status,
        ai_evaluation=ai_eval,
        admin_remarks=app.admin_remarks,
        created_at=app.created_at,
        updated_at=app.updated_at,
        documents=docs,
        merit_score=app.merit_score,
        selection_rank=app.selection_rank
    )

@router.post("", response_model=ApplicationRead)
def submit_application(
    payload: ApplicationCreate,
    principal: Principal = Depends(require_applicant),
    db: Session = Depends(get_db)
):
    """
    Submit a scholarship/fellowship application.
    Applies configured scheme rules; uploaded documents are OCR-checked after creation.
    """
    if payload.email.strip().lower() != principal.email:
        raise HTTPException(status_code=403, detail="Applications can only be submitted for the signed-in account.")
    scheme = db.query(Scheme).filter(Scheme.code == payload.scheme_code.upper()).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{payload.scheme_code}' not found")
    docs_payload = payload.documents or []
    if docs_payload:
        raise HTTPException(
            status_code=422,
            detail="Submit the application first, then upload each document through the application document endpoint.",
        )
    
    scheme_config = json.loads(scheme.config_json) if scheme.config_json else {}
    
    # Find or create applicant
    applicant = db.query(Applicant).filter(func.lower(Applicant.email) == principal.email).first()
    category = payload.declared_fields.get("category", "ST")
    caste_no = payload.declared_fields.get("caste_certificate_no", "")
    try:
        annual_inc = float(payload.declared_fields["annual_family_income"]) if payload.declared_fields.get("annual_family_income") not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Annual family income must be a number.") from exc
    if annual_inc is not None and not math.isfinite(annual_inc):
        raise HTTPException(status_code=422, detail="Annual family income must be a finite number.")

    if not applicant:
        applicant = Applicant(
            full_name=payload.full_name,
            email=principal.email,
            phone=payload.phone,
            category=category,
            caste_certificate_no=caste_no,
            annual_income=annual_inc
        )
        db.add(applicant)
        db.commit()
        db.refresh(applicant)
    else:
        # update details
        applicant.full_name = payload.full_name
        applicant.phone = payload.phone or applicant.phone
        applicant.category = category
        applicant.caste_certificate_no = caste_no
        applicant.annual_income = annual_inc
        db.commit()

    docs_dict_list = []

    # Run AI Rule Engine
    eval_result = evaluate_application_rules(
        scheme_code=scheme.code,
        declared_fields=payload.declared_fields,
        scheme_config=scheme_config,
        documents=docs_dict_list
    )

    # If critical errors exist, status can start as UNDER_REVIEW or DEFICIENT
    # Default is SUBMITTED with AI flag
    initial_status = "SUBMITTED"
    if not eval_result["pass_fail"]:
        initial_status = "DEFICIENT" if any(
            mismatch["field"].startswith(("doc_", "required_")) for mismatch in eval_result["mismatches"]
        ) else "UNDER_REVIEW"

    app_record = Application(
        application_no=generate_application_no(scheme.code),
        scheme_id=scheme.id,
        applicant_id=applicant.id,
        declared_data=json.dumps(payload.declared_fields),
        confidence_score=eval_result["confidence_score"],
        status=initial_status,
        ai_evaluation=json.dumps(eval_result),
        admin_remarks=""
    )
    db.add(app_record)
    db.commit()
    db.refresh(app_record)
    db.add(AuditEvent(
        application_id=app_record.id,
        actor_email=principal.email,
        actor_role=principal.role,
        action="APPLICATION_SUBMITTED",
        to_status=initial_status,
        remarks="Application received; automated checks are advisory.",
    ))
    db.commit()
    db.refresh(app_record)

    return format_application_response(app_record)

@router.post("/{app_id}/documents", response_model=DocumentRead)
async def upload_document(
    app_id: int,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    principal: Principal = Depends(require_applicant),
    db: Session = Depends(get_db)
):
    """Store and OCR one required application document, then recalculate its checks."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.applicant.email.strip().lower() != principal.email:
        raise HTTPException(status_code=403, detail="This application belongs to another account.")
    if app.status in {"APPROVED", "REJECTED", "SELECTED", "NOT_SELECTED"}:
        raise HTTPException(status_code=409, detail="Documents cannot be changed after a final decision.")
    previous_status = app.status

    original_name = Path(file.filename or "document").name[:255]
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload a PDF, image, or TXT file.")

    scheme_config = json.loads(app.scheme.config_json) if app.scheme and app.scheme.config_json else {}
    allowed_doc_types = {
        item["id"] for item in scheme_config.get("required_documents", [])
        if isinstance(item, dict) and item.get("id")
    }
    if doc_type not in allowed_doc_types:
        raise HTTPException(status_code=400, detail="Document type is not configured for this scheme.")

    content = await file.read(MAX_FILE_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")

    if extension == ".pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The selected file is not a valid PDF.")
    if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="The selected file is not a valid PNG image.")
    if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8"):
        raise HTTPException(status_code=400, detail="The selected file is not a valid JPEG image.")

    upload_dir = UPLOAD_DIR / str(app_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    file_path = upload_dir / stored_name
    file_path.write_bytes(content)
    ocr_result = process_document_ocr(str(file_path), doc_type, app.scheme.code if app.scheme else None)

    existing_doc = db.query(Document).filter(Document.application_id == app_id, Document.doc_type == doc_type).first()
    if existing_doc:
        existing_doc.file_name = original_name
        existing_doc.file_path = f"/uploads/{app_id}/{stored_name}"
        existing_doc.status = "DEFICIENT" if ocr_result["ocr_status"] == "FAILED" else "UPLOADED"
        existing_doc.extracted_text = ocr_result.get("extracted_text")
        existing_doc.ocr_status = ocr_result["ocr_status"]
        existing_doc.ocr_confidence = ocr_result.get("ocr_confidence")
        existing_doc.extraction_method = ocr_result.get("extraction_method")
        existing_doc.parsed_fields = json.dumps(ocr_result.get("parsed_fields") or {})
        existing_doc.failed_reason = ocr_result.get("failed_reason")
        doc = existing_doc
    else:
        doc = Document(
            application_id=app_id,
            doc_type=doc_type,
            file_name=original_name,
            file_path=f"/uploads/{app_id}/{stored_name}",
            status="DEFICIENT" if ocr_result["ocr_status"] == "FAILED" else "UPLOADED",
            extracted_text=ocr_result.get("extracted_text"),
            ocr_status=ocr_result["ocr_status"],
            ocr_confidence=ocr_result.get("ocr_confidence"),
            extraction_method=ocr_result.get("extraction_method"),
            parsed_fields=json.dumps(ocr_result.get("parsed_fields") or {}),
            failed_reason=ocr_result.get("failed_reason")
        )
        db.add(doc)

    db.flush()
    all_docs = db.query(Document).filter(Document.application_id == app_id).all()
    declared = json.loads(app.declared_data) if app.declared_data else {}
    verified_fields = dict(declared)
    valid_docs = []
    for stored_doc in all_docs:
        parsed_fields = json.loads(stored_doc.parsed_fields) if stored_doc.parsed_fields else {}
        if stored_doc.ocr_status in {"SUCCESS", "PARTIAL"}:
            verified_fields.update(parsed_fields)
            valid_docs.append({"doc_type": stored_doc.doc_type, "file_name": stored_doc.file_name})
    ai_eval = evaluate_application_rules(
        scheme_code=app.scheme.code if app.scheme else "NFST",
        declared_fields=verified_fields,
        scheme_config=scheme_config,
        documents=valid_docs
    )
    for stored_doc in all_docs:
        parsed_fields = json.loads(stored_doc.parsed_fields) if stored_doc.parsed_fields else {}
        for field, extracted_value in parsed_fields.items():
            declared_value = declared.get(field)
            if declared_value is None or str(declared_value).strip() == "":
                continue
            try:
                values_match = float(declared_value) == float(extracted_value)
            except (TypeError, ValueError):
                declared_text = " ".join(str(declared_value).strip().casefold().split())
                extracted_text = " ".join(str(extracted_value).strip().casefold().split())
                values_match = declared_text.removeprefix("the ") == extracted_text.removeprefix("the ")
            if not values_match:
                ai_eval["mismatches"].append({
                    "field": field,
                    "label": field.replace("_", " ").title(),
                    "declared_value": f"Applicant: {declared_value}; document: {extracted_value}",
                    "expected_rule": "Application details should agree with the uploaded document",
                    "severity": "ERROR",
                    "description": "The value extracted from the document differs from the applicant's declaration; officer review is required.",
                })
    for stored_doc in all_docs:
        if stored_doc.ocr_status in {"FAILED", "PENDING"}:
            ai_eval["mismatches"].append({
                "field": f"doc_{stored_doc.doc_type}_ocr",
                "label": stored_doc.doc_type.replace("_", " ").title(),
                "declared_value": stored_doc.ocr_status,
                "expected_rule": "Readable document with the expected information",
                "severity": "ERROR",
                "description": stored_doc.failed_reason or "Document OCR needs a clearer replacement.",
            })
        elif stored_doc.ocr_status == "PARTIAL":
            ai_eval["mismatches"].append({
                "field": f"doc_{stored_doc.doc_type}_ocr",
                "label": stored_doc.doc_type.replace("_", " ").title(),
                "declared_value": stored_doc.ocr_status,
                "expected_rule": "Expected fields extracted for officer review",
                "severity": "WARNING",
                "description": stored_doc.failed_reason or "Some fields need manual officer verification.",
            })
    has_errors = any(item["severity"] == "ERROR" for item in ai_eval["mismatches"])
    ai_eval["pass_fail"] = not has_errors
    ai_eval["confidence_score"] = max(
        15.0,
        min(
            99.0,
            98.0
            - 20.0 * sum(item["severity"] == "ERROR" for item in ai_eval["mismatches"])
            - 4.0 * sum(item["severity"] == "WARNING" for item in ai_eval["mismatches"]),
        ),
    )
    error_count = sum(item["severity"] == "ERROR" for item in ai_eval["mismatches"])
    warning_count = sum(item["severity"] == "WARNING" for item in ai_eval["mismatches"])
    if error_count or warning_count:
        ai_eval["summary"] = (
            f"Rule checks flagged {error_count} issue(s) and {warning_count} warning(s); officer review required."
        )
    app.ai_evaluation = json.dumps(ai_eval)
    app.confidence_score = ai_eval["confidence_score"]
    required_doc_ids = {
        item["id"] for item in scheme_config.get("required_documents", [])
        if isinstance(item, dict) and item.get("required") and item.get("id")
    }
    successful_doc_ids = {
        stored_doc.doc_type for stored_doc in all_docs
        if stored_doc.ocr_status in {"SUCCESS", "PARTIAL"}
    }
    if required_doc_ids - successful_doc_ids:
        app.status = "DEFICIENT"
    else:
        has_partial_ocr = any(stored_doc.ocr_status == "PARTIAL" for stored_doc in all_docs)
        app.status = "UNDER_REVIEW" if not ai_eval["pass_fail"] or has_partial_ocr else "SUBMITTED"
    db.add(AuditEvent(
        application_id=app.id,
        actor_email=principal.email,
        actor_role=principal.role,
        action=f"DOCUMENT_UPLOADED_{doc_type.upper()}",
        from_status=previous_status,
        to_status=app.status,
        remarks=f"OCR status: {doc.ocr_status}. OCR findings are advisory.",
    ))

    db.commit()
    db.refresh(doc)
    db.refresh(app)

    return DocumentRead(
        id=doc.id,
        doc_type=doc.doc_type,
        file_name=doc.file_name,
        file_path=f"/private-documents/{doc.id}/file" if doc.file_path else None,
        status=doc.status,
        extracted_text=doc.extracted_text,
        ocr_status=doc.ocr_status,
        ocr_confidence=doc.ocr_confidence,
        extraction_method=doc.extraction_method,
        parsed_fields=json.loads(doc.parsed_fields) if doc.parsed_fields else None,
        failed_reason=doc.failed_reason,
        uploaded_at=doc.uploaded_at
    )

@router.get("/{app_id:int}", response_model=ApplicationRead)
def get_application_status(
    app_id: int,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db)
):
    """Retrieve application status, declared data, and AI evaluation report."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if principal.role == "applicant" and app.applicant.email.strip().lower() != principal.email:
        raise HTTPException(status_code=403, detail="This application belongs to another account.")
    return format_application_response(app)

@router.get("/mine", response_model=List[ApplicationRead])
def get_my_applications(
    principal: Principal = Depends(require_applicant),
    db: Session = Depends(get_db)
):
    applicant = db.query(Applicant).filter(Applicant.email == principal.email).first()
    if not applicant:
        return []
    apps = db.query(Application).filter(Application.applicant_id == applicant.id).order_by(Application.created_at.desc()).all()
    return [format_application_response(a) for a in apps]


@router.get("/awards")
def get_my_awards(
    principal: Principal = Depends(require_applicant),
    db: Session = Depends(get_db),
):
    awards = db.query(Award).join(Application).join(Applicant).filter(
        Applicant.email == principal.email
    ).order_by(Award.updated_at.desc()).all()
    return [{
        "id": award.id,
        "application_id": award.application_id,
        "application_no": award.application.application_no,
        "scheme_code": award.application.scheme.code if award.application.scheme else "",
        "award_status": award.award_status,
        "approved_amount": award.approved_amount,
        "currency": award.currency,
        "start_date": award.start_date,
        "end_date": award.end_date,
        "next_review_date": award.next_review_date,
        "officer_remarks": award.officer_remarks,
        "updated_at": award.updated_at,
        "payments": [{
            "id": payment.id,
            "period": payment.period,
            "amount": payment.amount,
            "status": payment.status,
            "reference": payment.reference,
            "paid_at": payment.paid_at,
        } for payment in award.payments],
    } for award in awards]


@router.patch("/{app_id:int}", response_model=ApplicationRead)
def correct_application(
    app_id: int,
    payload: ApplicationCorrectionRequest,
    principal: Principal = Depends(require_applicant),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.applicant.email.strip().lower() != principal.email:
        raise HTTPException(status_code=403, detail="This application belongs to another account.")
    if app.status != "DEFICIENT":
        raise HTTPException(status_code=409, detail="Application corrections are enabled only while deficient.")
    declared_email = str(payload.declared_fields.get("email", principal.email)).strip().lower()
    if declared_email != principal.email:
        raise HTTPException(status_code=422, detail="The registered email cannot be changed.")
    if not payload.full_name.strip():
        raise HTTPException(status_code=422, detail="Applicant name cannot be empty.")
    old_status = app.status
    declared = dict(payload.declared_fields)
    declared["full_name"] = payload.full_name.strip()
    declared["email"] = principal.email
    declared["phone"] = payload.phone or ""
    config = json.loads(app.scheme.config_json) if app.scheme and app.scheme.config_json else {}
    docs = [
        {"doc_type": d.doc_type, "file_name": d.file_name}
        for d in app.documents if d.ocr_status in {"SUCCESS", "PARTIAL"}
    ]
    evaluation = evaluate_application_rules(app.scheme.code, declared, config, docs)
    for document in app.documents:
        if document.ocr_status not in {"SUCCESS", "PARTIAL"} or not document.parsed_fields:
            continue
        extracted_fields = json.loads(document.parsed_fields)
        for field, extracted_value in extracted_fields.items():
            declared_value = declared.get(field)
            if declared_value is None or str(declared_value).strip() == "":
                continue
            try:
                values_match = float(declared_value) == float(extracted_value)
            except (TypeError, ValueError):
                normalize = lambda value: " ".join(str(value).strip().casefold().split()).removeprefix("the ")
                values_match = normalize(declared_value) == normalize(extracted_value)
            if not values_match:
                evaluation["mismatches"].append({
                    "field": field,
                    "label": field.replace("_", " ").title(),
                    "declared_value": f"Applicant: {declared_value}; document: {extracted_value}",
                    "expected_rule": "Application details should agree with the uploaded document",
                    "severity": "ERROR",
                    "description": "The corrected declaration still differs from the uploaded document; officer review is required.",
                })
    error_count = sum(item["severity"] == "ERROR" for item in evaluation["mismatches"])
    warning_count = sum(item["severity"] == "WARNING" for item in evaluation["mismatches"])
    evaluation["pass_fail"] = error_count == 0
    evaluation["confidence_score"] = max(15.0, min(99.0, 98.0 - 20.0 * error_count - 4.0 * warning_count))
    if error_count or warning_count:
        evaluation["summary"] = f"Rule checks flagged {error_count} issue(s) and {warning_count} warning(s); officer review required."
    app.declared_data = json.dumps(declared)
    app.confidence_score = evaluation["confidence_score"]
    app.ai_evaluation = json.dumps(evaluation)
    has_missing_required_items = any(
        mismatch["field"].startswith(("doc_", "required_"))
        for mismatch in evaluation["mismatches"]
    )
    app.status = "DEFICIENT" if has_missing_required_items or not evaluation["pass_fail"] else "UNDER_REVIEW"
    app.admin_remarks = ""
    app.applicant.full_name = payload.full_name.strip()
    app.applicant.phone = payload.phone or ""
    app.applicant.category = declared.get("category", app.applicant.category)
    app.applicant.caste_certificate_no = declared.get("caste_certificate_no", app.applicant.caste_certificate_no)
    try:
        applicant_income = declared.get("annual_family_income")
        app.applicant.annual_income = float(applicant_income) if applicant_income not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Annual family income must be a number.") from exc
    if app.applicant.annual_income is not None and not math.isfinite(app.applicant.annual_income):
        raise HTTPException(status_code=422, detail="Annual family income must be a finite number.")
    db.add(AuditEvent(
        application_id=app.id,
        actor_email=principal.email,
        actor_role=principal.role,
        action="APPLICANT_CORRECTION_SUBMITTED",
        from_status=old_status,
        to_status=app.status,
        remarks="Applicant updated declared application details.",
    ))
    db.commit()
    db.refresh(app)
    return format_application_response(app)


@router.get("/notifications")
def get_my_notifications(
    principal: Principal = Depends(require_applicant),
    db: Session = Depends(get_db),
):
    applicant = db.query(Applicant).filter(Applicant.email == principal.email).first()
    if not applicant:
        return []
    notifications = db.query(Notification).filter(
        Notification.applicant_id == applicant.id
    ).order_by(Notification.created_at.desc()).all()
    return [{
        "id": item.id,
        "application_id": item.application_id,
        "title": item.title,
        "message": item.message,
        "read_at": item.read_at,
        "created_at": item.created_at,
    } for item in notifications]


@router.post("/notifications/{notification_id:int}/read")
def mark_notification_read(
    notification_id: int,
    principal: Principal = Depends(require_applicant),
    db: Session = Depends(get_db),
):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    owner = db.query(Applicant).filter(Applicant.id == notification.applicant_id).first()
    if not owner or owner.email.strip().lower() != principal.email:
        raise HTTPException(status_code=403, detail="This notification belongs to another account.")
    if notification.read_at is None:
        notification.read_at = datetime.utcnow()
        db.commit()
    return {"id": notification.id, "read_at": notification.read_at}
