import json
import math
from datetime import datetime
from pathlib import Path
from secrets import randbelow
from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from models import Scheme, Applicant, Application, Document
from schemas import ApplicationCreate, ApplicationRead, DocumentRead, RuleEvaluation
from services.ocr_service import process_document_ocr
from services.rule_engine import evaluate_application_rules

router = APIRouter(prefix="/applications", tags=["Applications"])
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024

def generate_application_no(scheme_code: str) -> str:
    return f"AROHAN-{scheme_code.upper()}-{datetime.now().year}-{randbelow(100000):05d}"

def format_application_response(app: Application) -> ApplicationRead:
    declared_dict = json.loads(app.declared_data) if app.declared_data else {}
    ai_eval_dict = json.loads(app.ai_evaluation) if app.ai_evaluation else None
    ai_eval = RuleEvaluation(**ai_eval_dict) if ai_eval_dict else None
    
    docs = [
        DocumentRead(
            id=d.id,
            doc_type=d.doc_type,
            file_name=d.file_name,
            file_path=d.file_path,
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
        documents=docs
    )

@router.post("", response_model=ApplicationRead)
def submit_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    """
    Submit a scholarship/fellowship application.
    Applies configured scheme rules; uploaded documents are OCR-checked after creation.
    """
    scheme = db.query(Scheme).filter(Scheme.code == payload.scheme_code.upper()).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{payload.scheme_code}' not found")
    
    scheme_config = json.loads(scheme.config_json) if scheme.config_json else {}
    
    # Find or create applicant
    applicant = db.query(Applicant).filter(Applicant.email == payload.email).first()
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
            email=payload.email,
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

    # Convert documents to list of dicts for rule checking
    docs_payload = payload.documents or []
    docs_dict_list = [{"doc_type": d.doc_type, "file_name": d.file_name} for d in docs_payload]

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
            mismatch["field"].startswith("doc_") for mismatch in eval_result["mismatches"]
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

    # Save document references
    for doc in docs_payload:
        doc_record = Document(
            application_id=app_record.id,
            doc_type=doc.doc_type,
            file_name=doc.file_name,
            file_path=doc.file_path or f"/uploads/{doc.file_name}",
            status="UPLOADED"
        )
        db.add(doc_record)
    
    db.commit()
    db.refresh(app_record)

    return format_application_response(app_record)

@router.post("/{app_id}/documents", response_model=DocumentRead)
async def upload_document(
    app_id: int,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """Store and OCR one required application document, then recalculate its checks."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=409, detail="Documents cannot be changed after a final decision.")

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

    db.commit()
    db.refresh(doc)
    db.refresh(app)

    return DocumentRead(
        id=doc.id,
        doc_type=doc.doc_type,
        file_name=doc.file_name,
        file_path=doc.file_path,
        status=doc.status,
        extracted_text=doc.extracted_text,
        ocr_status=doc.ocr_status,
        ocr_confidence=doc.ocr_confidence,
        extraction_method=doc.extraction_method,
        parsed_fields=json.loads(doc.parsed_fields) if doc.parsed_fields else None,
        failed_reason=doc.failed_reason,
        uploaded_at=doc.uploaded_at
    )

@router.get("/{app_id}", response_model=ApplicationRead)
def get_application_status(app_id: int, db: Session = Depends(get_db)):
    """Retrieve application status, declared data, and AI evaluation report."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return format_application_response(app)

@router.get("/applicant/{applicant_id}", response_model=List[ApplicationRead])
def get_applicant_applications(applicant_id: int, db: Session = Depends(get_db)):
    """List all applications submitted by an applicant."""
    apps = db.query(Application).filter(Application.applicant_id == applicant_id).order_by(Application.created_at.desc()).all()
    return [format_application_response(a) for a in apps]

@router.get("/by-email/{email}", response_model=List[ApplicationRead])
def get_applications_by_email(email: str, db: Session = Depends(get_db)):
    """List applications matching applicant email."""
    applicant = db.query(Applicant).filter(Applicant.email == email).first()
    if not applicant:
        return []
    apps = db.query(Application).filter(Application.applicant_id == applicant.id).order_by(Application.created_at.desc()).all()
    return [format_application_response(a) for a in apps]
