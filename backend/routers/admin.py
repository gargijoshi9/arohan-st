import csv
import io
import json
import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from database import get_db
from models import Application, Applicant, AuditEvent, Award, AwardPayment, Document, Notification, Scheme
from schemas import AdminDecisionRequest, ApplicationRead, AwardUpdateRequest, DocumentVerificationRequest, PaymentCreateRequest
from security import Principal, require_admin
from routers.applications import format_application_response

router = APIRouter(prefix="/admin", tags=["Admin Operations"])
AWARD_STATES = {"ACTIVE", "ON_HOLD", "COMPLETED", "TERMINATED"}
PAYMENT_STATES = {"PENDING", "PROCESSING", "PAID", "FAILED"}
SELECTION_STATES = {"APPROVED", "REJECTED"}


@router.post("/documents/{document_id:int}/verification")
def verify_document(
    document_id: int,
    payload: DocumentVerificationRequest,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    app = document.application
    if app.status in SELECTION_STATES:
        raise HTTPException(status_code=409, detail="Documents cannot be changed after a final decision.")
    decision = payload.decision.strip().upper()
    if decision not in {"VERIFY", "DEFICIENT"}:
        raise HTTPException(status_code=422, detail="Document decision must be VERIFY or DEFICIENT.")
    remarks = payload.remarks.strip()
    if not remarks:
        raise HTTPException(status_code=422, detail="Record the basis for the document review.")
    if decision == "VERIFY" and document.ocr_status == "FAILED":
        raise HTTPException(
            status_code=409,
            detail="OCR failed for this document. Ask the applicant to upload a readable replacement before verification.",
        )
    previous_doc_status = document.status
    previous_app_status = app.status
    document.status = "VERIFIED" if decision == "VERIFY" else "DEFICIENT"
    if decision == "DEFICIENT":
        app.status = "DEFICIENT"
        app.admin_remarks = remarks
    else:
        config = json.loads(app.scheme.config_json or "{}") if app.scheme else {}
        required = {
            item["id"] for item in config.get("required_documents", [])
            if isinstance(item, dict) and item.get("required") and item.get("id")
        }
        verified = {item.doc_type for item in app.documents if item.status == "VERIFIED"}
        evaluation = json.loads(app.ai_evaluation or "{}")
        if required.issubset(verified) and evaluation.get("pass_fail"):
            app.status = "UNDER_REVIEW"
    db.add(AuditEvent(
        application_id=app.id,
        actor_email=principal.email,
        actor_role=principal.role,
        action=f"DOCUMENT_{decision}",
        from_status=previous_doc_status,
        to_status=document.status,
        remarks=f"{document.doc_type}: {remarks}",
    ))
    applicant = db.query(Applicant).filter(Applicant.id == app.applicant_id).first()
    if applicant:
        db.add(Notification(
            applicant_id=applicant.id,
            application_id=app.id,
            title=f"Document {decision.lower()}",
            message=f"{document.doc_type.replace('_', ' ').title()}: {remarks}",
        ))
    if previous_app_status != app.status:
        db.add(AuditEvent(
            application_id=app.id,
            actor_email=principal.email,
            actor_role=principal.role,
            action="APPLICATION_STATUS_UPDATED_AFTER_DOCUMENT_REVIEW",
            from_status=previous_app_status,
            to_status=app.status,
            remarks=remarks,
        ))
    db.commit()
    return {
        "document_id": document.id,
        "application_id": app.id,
        "document_status": document.status,
        "application_status": app.status,
        "review_remarks": remarks,
    }


@router.get("/queue", response_model=list[ApplicationRead])
def get_review_queue(
    sort_by: str = Query("confidence_score", pattern="^(confidence_score|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    status: Optional[str] = None,
    scheme_code: Optional[str] = None,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Application)
    if status and status.upper() != "ALL":
        query = query.filter(Application.status == status.upper())
    if scheme_code and scheme_code.upper() != "ALL":
        query = query.join(Application.scheme).filter(Scheme.code == scheme_code.upper())
    column = Application.confidence_score if sort_by == "confidence_score" else Application.created_at
    query = query.order_by(asc(column) if order == "asc" else desc(column))
    return [format_application_response(app) for app in query.all()]


@router.post("/applications/{app_id:int}/decision", response_model=ApplicationRead)
def submit_admin_decision(
    app_id: int,
    payload: AdminDecisionRequest,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status in SELECTION_STATES:
        raise HTTPException(status_code=409, detail="A final decision cannot be changed through this prototype.")
    decision_map = {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "DEFICIENT": "DEFICIENT",
        "FLAG": "DEFICIENT",
        "RESUBMIT": "DEFICIENT",
        "UNDER_REVIEW": "UNDER_REVIEW",
        "SELECT": "SELECTED",
        "NOT_SELECT": "NOT_SELECTED",
    }
    normalized_decision = decision_map.get(payload.decision.upper())
    if not normalized_decision:
        raise HTTPException(status_code=400, detail="Decision must be APPROVE, REJECT, DEFICIENT, UNDER_REVIEW, SELECT, or NOT_SELECT.")
    remarks = (payload.remarks or "").strip()
    if normalized_decision in {"APPROVED", "REJECTED", "DEFICIENT", "SELECTED", "NOT_SELECTED"} and not remarks:
        raise HTTPException(status_code=422, detail="Record the officer's reason before saving this decision.")
    if normalized_decision == "APPROVED" and app.status != "SELECTED":
        raise HTTPException(status_code=409, detail="Record the authorized human selection before approving the award.")
    if normalized_decision == "SELECTED":
        config = json.loads(app.scheme.config_json or "{}") if app.scheme else {}
        required = {
            item["id"] for item in config.get("required_documents", [])
            if isinstance(item, dict) and item.get("required") and item.get("id")
        }
        verified = {document.doc_type for document in app.documents if document.status == "VERIFIED"}
        evaluation = json.loads(app.ai_evaluation or "{}")
        if required - verified or not evaluation.get("pass_fail"):
            raise HTTPException(status_code=409, detail="Resolve configured eligibility issues and officer-verify every required document before selection.")
    if normalized_decision == "APPROVED":
        config = json.loads(app.scheme.config_json or "{}") if app.scheme else {}
        required = {
            item["id"] for item in config.get("required_documents", [])
            if isinstance(item, dict) and item.get("required") and item.get("id")
        }
        verified = {document.doc_type for document in app.documents if document.status == "VERIFIED"}
        if required - verified:
            raise HTTPException(status_code=409, detail="Officer verification is required for every required document before approval.")
    previous_status = app.status
    app.status = normalized_decision
    if normalized_decision == "SELECTED":
        app.selected_at = datetime.utcnow()
    app.admin_remarks = remarks
    db.add(AuditEvent(
        application_id=app.id,
        actor_email=principal.email,
        actor_role=principal.role,
        action=f"OFFICER_{normalized_decision}",
        from_status=previous_status,
        to_status=normalized_decision,
        remarks=remarks,
    ))
    if normalized_decision == "APPROVED":
        if not db.query(Award).filter(Award.application_id == app.id).first():
            db.add(Award(application_id=app.id, award_status="ACTIVE", officer_remarks=remarks))
    if normalized_decision in {"APPROVED", "REJECTED", "DEFICIENT", "SELECTED", "NOT_SELECTED"}:
        applicant = db.query(Applicant).filter(Applicant.id == app.applicant_id).first()
        if applicant:
            db.add(Notification(
                applicant_id=applicant.id,
                application_id=app.id,
                title=f"Application {normalized_decision.replace('_', ' ').title()}",
                message=remarks,
            ))
    db.commit()
    db.refresh(app)
    return format_application_response(app)


@router.get("/applications/{app_id:int}/audit")
def get_application_audit(
    app_id: int,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.query(Application.id).filter(Application.id == app_id).first():
        raise HTTPException(status_code=404, detail="Application not found")
    events = db.query(AuditEvent).filter(AuditEvent.application_id == app_id).order_by(AuditEvent.created_at.asc()).all()
    return [{
        "id": event.id,
        "actor_email": event.actor_email,
        "actor_role": event.actor_role,
        "action": event.action,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "remarks": event.remarks,
        "created_at": event.created_at,
    } for event in events]


@router.get("/selection")
def get_selection_rankings(
    scheme_code: str,
    slots: int = Query(10, ge=1, le=500),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    scheme = db.query(Scheme).filter(Scheme.code == scheme_code.upper()).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    config = json.loads(scheme.config_json or "{}")
    mark_field = config.get("selection_config", {}).get("ranking_field") or next(
        (field for field in ("qualifying_percentage", "pg_percentage", "marks_percentage")
         if any(field in json.loads(app.declared_data or "{}") for app in scheme.applications)),
        None,
    )
    ranked = []
    for app in scheme.applications:
        declared = json.loads(app.declared_data or "{}")
        try:
            marks = float(declared.get(mark_field)) if mark_field else None
        except (TypeError, ValueError):
            marks = None
        if marks is not None and not math.isfinite(marks):
            marks = None
        required = {
            item["id"] for item in config.get("required_documents", [])
            if isinstance(item, dict) and item.get("required") and item.get("id")
        }
        verified = {document.doc_type for document in app.documents if document.status == "VERIFIED"}
        checks = json.loads(app.ai_evaluation or "{}")
        eligible_for_ranking = (
            app.status not in {"REJECTED", "DEFICIENT", "NOT_SELECTED"}
            and bool(checks.get("pass_fail"))
            and required.issubset(verified)
            and (marks is not None or not config.get("selection_config", {}).get("ranking_field"))
        )
        ranked.append({
            "application_id": app.id,
            "application_no": app.application_no,
            "applicant_name": app.applicant.full_name if app.applicant else "Applicant",
            "scheme_code": scheme.code,
            "status": app.status,
            "mark_field": mark_field,
            "marks": marks,
            "ranking_mode": config.get("selection_config", {}).get("ranking_mode", "MANUAL_REVIEW"),
            "eligible_for_ranking": eligible_for_ranking,
            "human_decision_required": True,
            "submitted_at": app.created_at,
        })
    ranked.sort(key=lambda item: (
        not item["eligible_for_ranking"],
        -(item["marks"] if item["marks"] is not None else -1),
        item["submitted_at"],
        item["application_no"],
    ))
    eligible_rank = 0
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index if item["eligible_for_ranking"] else None
        if item["eligible_for_ranking"]:
            eligible_rank += 1
        item["within_demo_slots"] = item["eligible_for_ranking"] and eligible_rank <= slots
        item.pop("submitted_at")
    return {
        "scheme_code": scheme.code,
        "scheme_name": scheme.name,
        "mark_field": mark_field,
        "slots": slots,
        "notice": "Advisory ranking only. Verify the published scheme criteria, documents, quota and roster, then record the decision as an authorized officer.",
        "candidates": ranked,
    }


@router.get("/dashboard")
def get_dashboard(
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    apps = db.query(Application).all()
    by_status: dict[str, int] = {}
    by_scheme: dict[str, dict[str, int]] = {}
    for app in apps:
        by_status[app.status] = by_status.get(app.status, 0) + 1
        scheme_code = app.scheme.code if app.scheme else "UNKNOWN"
        scheme_summary = by_scheme.setdefault(scheme_code, {"total": 0, "approved": 0, "deficient": 0, "under_review": 0})
        scheme_summary["total"] += 1
        if app.status == "APPROVED":
            scheme_summary["approved"] += 1
        elif app.status == "DEFICIENT":
            scheme_summary["deficient"] += 1
        elif app.status in {"UNDER_REVIEW", "SUBMITTED"}:
            scheme_summary["under_review"] += 1
    award_count = db.query(Award).count()
    pending_payments = db.query(AwardPayment).filter(AwardPayment.status.in_(["PENDING", "PROCESSING"])).count()
    return {
        "total_applications": len(apps),
        "by_status": by_status,
        "by_scheme": by_scheme,
        "active_awards": db.query(Award).filter(Award.award_status == "ACTIVE").count(),
        "total_awards": award_count,
        "pending_payments": pending_payments,
        "generated_at": datetime.utcnow(),
    }


@router.get("/report.csv")
def download_report(
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Application number", "Scheme", "Applicant", "Email", "Status", "Submitted", "Rule indicator"])

    def safe_cell(value):
        text = "" if value is None else str(value)
        return f"'{text}" if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text

    for app in db.query(Application).order_by(Application.created_at.desc()).all():
        writer.writerow([safe_cell(value) for value in [
            app.application_no,
            app.scheme.code if app.scheme else "",
            app.applicant.full_name if app.applicant else "",
            app.applicant.email if app.applicant else "",
            app.status,
            app.created_at.isoformat() if app.created_at else "",
            app.confidence_score,
        ]])
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=arohan-application-report.csv"},
    )


@router.get("/awards")
def get_awards(
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    awards = db.query(Award).join(Application).order_by(Award.updated_at.desc()).all()
    return [_serialize_award(award) for award in awards]


@router.put("/applications/{app_id:int}/award")
def update_award(
    app_id: int,
    payload: AwardUpdateRequest,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status != "APPROVED":
        raise HTTPException(status_code=409, detail="Only an officer-approved application can have an award record.")
    state = payload.award_status.upper()
    if state not in AWARD_STATES:
        raise HTTPException(status_code=422, detail=f"Award status must be one of {', '.join(sorted(AWARD_STATES))}.")
    if payload.approved_amount is not None and (not math.isfinite(payload.approved_amount) or payload.approved_amount < 0):
        raise HTTPException(status_code=422, detail="Approved amount must be a non-negative finite number.")
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="Award end date cannot precede its start date.")
    award = db.query(Award).filter(Award.application_id == app.id).first()
    if not award:
        award = Award(application_id=app.id)
        db.add(award)
    committed_amount = sum(
        payment.amount for payment in award.payments
        if payment.status in {"PENDING", "PROCESSING", "PAID"}
    )
    if payload.approved_amount is not None and payload.approved_amount < committed_amount:
        raise HTTPException(status_code=409, detail="Approved amount cannot be lower than recorded payment milestones.")
    previous_status = award.award_status
    award.award_status = state
    award.approved_amount = payload.approved_amount
    award.start_date = payload.start_date
    award.end_date = payload.end_date
    award.next_review_date = payload.next_review_date
    award.officer_remarks = (payload.officer_remarks or "").strip()
    db.add(AuditEvent(
        application_id=app.id,
        actor_email=principal.email,
        actor_role=principal.role,
        action="AWARD_RECORD_UPDATED",
        from_status=previous_status,
        to_status=state,
        remarks=award.officer_remarks,
    ))
    applicant = db.query(Applicant).filter(Applicant.id == app.applicant_id).first()
    if applicant:
        db.add(Notification(
            applicant_id=applicant.id,
            application_id=app.id,
            title="Award record updated",
            message=f"Your award status is now {state}. {award.officer_remarks}".strip(),
        ))
    db.commit()
    db.refresh(award)
    return _serialize_award(award)


@router.post("/awards/{award_id:int}/payments")
def add_award_payment(
    award_id: int,
    payload: PaymentCreateRequest,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    award = db.query(Award).filter(Award.id == award_id).first()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    if not payload.period.strip() or not math.isfinite(payload.amount) or payload.amount <= 0:
        raise HTTPException(status_code=422, detail="Provide a period and positive finite payment amount.")
    state = payload.status.upper()
    if state not in PAYMENT_STATES:
        raise HTTPException(status_code=422, detail=f"Payment status must be one of {', '.join(sorted(PAYMENT_STATES))}.")
    if award.approved_amount is not None:
        committed_amount = sum(
            payment.amount for payment in award.payments
            if payment.status in {"PENDING", "PROCESSING", "PAID"}
        )
        if committed_amount + payload.amount > award.approved_amount:
            raise HTTPException(status_code=409, detail="Payment milestones cannot exceed the approved award amount.")
    payment = AwardPayment(
        award_id=award.id,
        period=payload.period.strip(),
        amount=payload.amount,
        status=state,
        reference=(payload.reference or "").strip() or None,
        paid_at=datetime.utcnow() if state == "PAID" else None,
    )
    db.add(payment)
    applicant = award.application.applicant
    if applicant:
        db.add(Notification(
            applicant_id=applicant.id,
            application_id=award.application_id,
            title="Fellowship payment milestone recorded",
            message=f"{payload.period.strip()}: {state.lower()} record for INR {payload.amount:,.2f}.",
        ))
    db.add(AuditEvent(
        application_id=award.application_id,
        actor_email=principal.email,
        actor_role=principal.role,
        action=f"PAYMENT_MILESTONE_{state}",
        remarks=f"{payload.period.strip()}: INR {payload.amount:,.2f}; ref {payload.reference or 'not provided'}",
    ))
    db.commit()
    db.refresh(payment)
    return {
        "id": payment.id,
        "award_id": payment.award_id,
        "period": payment.period,
        "amount": payment.amount,
        "status": payment.status,
        "reference": payment.reference,
        "paid_at": payment.paid_at,
    }


def _serialize_award(award: Award):
    app = award.application if hasattr(award, "application") else None
    if app is None:
        app = award.__dict__.get("application")
    return {
        "id": award.id,
        "application_id": award.application_id,
        "application_no": app.application_no if app else "",
        "applicant_name": app.applicant.full_name if app and app.applicant else "",
        "applicant_email": app.applicant.email if app and app.applicant else "",
        "scheme_code": app.scheme.code if app and app.scheme else "",
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
    }
