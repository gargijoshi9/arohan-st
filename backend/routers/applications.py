import json
import os
import random
import string
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from models import Scheme, Applicant, Application, Document
from schemas import ApplicationCreate, ApplicationRead, DocumentRead, RuleEvaluation
from services.ocr_service import process_document_ocr
from services.rule_engine import evaluate_application_rules

router = APIRouter(prefix="/applications", tags=["Applications"])

def generate_application_no(scheme_code: str) -> str:
    year = datetime.now().year
    suffix = ''.join(random.choices(string.digits, k=5))
    return f"AROHAN-{scheme_code.upper()}-{year}-{suffix}"

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
    Executes mock AI Rule Engine to compute confidence score & identify discrepancies.
    """
    scheme = db.query(Scheme).filter(Scheme.code == payload.scheme_code.upper()).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{payload.scheme_code}' not found")
    
    scheme_config = json.loads(scheme.config_json) if scheme.config_json else {}
    
    # Find or create applicant
    applicant = db.query(Applicant).filter(Applicant.email == payload.email).first()
    category = payload.declared_fields.get("category", "ST")
    caste_no = payload.declared_fields.get("caste_certificate_no", "")
    annual_inc = float(payload.declared_fields.get("annual_family_income", 0))

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
        initial_status = "UNDER_REVIEW"

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
    """Upload a supporting document, OCR it, and update the application using extracted values."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    filename = file.filename or f"{doc_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", str(app_id), doc_type)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    ocr_result = process_document_ocr(file_path, doc_type, app.scheme.code if app.scheme else None)

    existing_doc = db.query(Document).filter(Document.application_id == app_id, Document.doc_type == doc_type).first()
    if existing_doc:
        existing_doc.file_name = filename
        existing_doc.file_path = file_path
        existing_doc.status = "UPLOADED"
        existing_doc.extracted_text = ocr_result.get("extracted_text")
        existing_doc.ocr_status = ocr_result.get("ocr_status", "PENDING")
        existing_doc.ocr_confidence = ocr_result.get("ocr_confidence", 0.0)
        existing_doc.parsed_fields = json.dumps(ocr_result.get("parsed_fields") or {})
        existing_doc.failed_reason = ocr_result.get("failed_reason")
        doc = existing_doc
    else:
        doc = Document(
            application_id=app_id,
            doc_type=doc_type,
            file_name=filename,
            file_path=file_path,
            status="UPLOADED",
            extracted_text=ocr_result.get("extracted_text"),
            ocr_status=ocr_result.get("ocr_status", "PENDING"),
            ocr_confidence=ocr_result.get("ocr_confidence", 0.0),
            parsed_fields=json.dumps(ocr_result.get("parsed_fields") or {}),
            failed_reason=ocr_result.get("failed_reason")
        )
        db.add(doc)

    # Merge OCR fields into application declaration to support downstream validation
    declared = json.loads(app.declared_data) if app.declared_data else {}
    for key, value in (ocr_result.get("parsed_fields") or {}).items():
        if value is not None and (key not in declared or declared.get(key) in (None, '', 0)):
            declared[key] = value
    app.declared_data = json.dumps(declared)

    scheme_config = json.loads(app.scheme.config_json) if app.scheme and app.scheme.config_json else {}
    ai_eval = evaluate_application_rules(
        scheme_code=app.scheme.code if app.scheme else "NFST",
        declared_fields=declared,
        scheme_config=scheme_config,
        documents=[{"doc_type": d.doc_type, "file_name": d.file_name} for d in app.documents]
    )
    app.ai_evaluation = json.dumps(ai_eval)
    app.confidence_score = ai_eval["confidence_score"]
    app.status = "UNDER_REVIEW" if not ai_eval["pass_fail"] else app.status

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
