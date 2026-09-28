"""Officer workspace: document review, adjudication, ranking, awards and reports.

Two invariants are enforced here rather than in the UI:

* A merit selection is refused until every configured required document is
  officer-verified and the application has no outstanding rule errors.
* An approval is refused until a selection has been recorded.

Every decision writes an audit event and, where the applicant is affected, a
notification.
"""

import csv
import io
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from database import APPLICATIONS, APPLICANTS, AWARDS, AWARD_PAYMENTS, DOCUMENTS, get_db, next_id, utcnow
from models import (
    AWARD_STATES,
    COMMITTED_PAYMENT_STATES,
    DOCUMENT_DEFICIENT,
    DOCUMENT_VERIFIED,
    FINAL_STATUSES,
    PAYMENT_PENDING,
    PAYMENT_PROCESSING,
    PAYMENT_STATES,
    STATUS_APPROVED,
    STATUS_DEFICIENT,
    STATUS_NOT_SELECTED,
    STATUS_REJECTED,
    STATUS_SELECTED,
    STATUS_SUBMITTED,
    STATUS_UNDER_REVIEW,
    STATUS_WITHDRAWN,
)
from schemas import (
    AdminDecisionRequest,
    ApplicationRead,
    AuditEventRead,
    AwardRead,
    AwardUpdateRequest,
    DashboardSummary,
    DocumentVerificationRequest,
    DocumentVerificationResult,
    PaginatedApplications,
    PaymentCreateRequest,
    SelectionResult,
)
from security import Principal, require_admin
from services.repository import (
    application_payload,
    application_payloads,
    award_payload,
    award_payloads,
    audit_history,
    committed_payment_total,
    get_application,
    get_award,
    get_award_by_application,
    get_document,
    get_documents,
    get_scheme_by_code,
    get_scheme_by_id,
    list_awards,
    notify,
    record_audit,
    required_document_ids,
    scheme_config,
    verified_document_types,
)

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

DECISION_MAP = {
    "APPROVE": STATUS_APPROVED,
    "REJECT": STATUS_REJECTED,
    "DEFICIENT": STATUS_DEFICIENT,
    "FLAG": STATUS_DEFICIENT,
    "RESUBMIT": STATUS_DEFICIENT,
    "UNDER_REVIEW": STATUS_UNDER_REVIEW,
    "SELECT": STATUS_SELECTED,
    "NOT_SELECT": STATUS_NOT_SELECTED,
}
# Decisions that must carry a written reason.
DECISIONS_REQUIRING_REASONS = (
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_DEFICIENT,
    STATUS_SELECTED,
    STATUS_NOT_SELECTED,
)
QUEUE_SORT_FIELDS = {
    "confidence_score": [("confidence_score", DESCENDING), ("created_at", DESCENDING)],
    "created_at": [("created_at", DESCENDING)],
    "status": [("status", ASCENDING), ("created_at", DESCENDING)],
    "application_no": [("application_no", ASCENDING)],
}


def selection_blockers(db: Database, application: dict) -> Tuple[List[str], str]:
    """Return (blocking reasons, scheme config) for a merit selection."""
    scheme = get_scheme_by_id(db, application["scheme_id"])
    config = scheme_config(scheme)
    required = required_document_ids(config)
    verified = verified_document_types(get_documents(db, application["id"]))
    evaluation = application.get("rule_evaluation") or {}

    blockers: List[str] = []
    missing = sorted(required - verified)
    if missing:
        blockers.append(f"Verify every required document first: {', '.join(missing)}.")
    if not evaluation.get("pass_fail", False):
        blockers.append("Configured eligibility checks still report issues.")
    return blockers, config


# --- Document review ---

@router.post("/documents/{document_id:int}/verification", response_model=DocumentVerificationResult)
def verify_document(
    document_id: int,
    payload: DocumentVerificationRequest,
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Record an officer's verification or deficiency judgement on one document."""
    document = get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    application = get_application(db, document["application_id"])
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application["status"] in FINAL_STATUSES:
        raise HTTPException(status_code=409, detail="Documents cannot be changed after a final decision.")

    decision = payload.decision.strip().upper()
    if decision not in {"VERIFY", "DEFICIENT"}:
        raise HTTPException(status_code=422, detail="Document decision must be VERIFY or DEFICIENT.")
    remarks = payload.remarks.strip()
    if not remarks:
        raise HTTPException(status_code=422, detail="Record the basis for the document review.")
    if decision == "VERIFY" and document.get("ocr_status") == "FAILED":
        raise HTTPException(
            status_code=409,
            detail="Extraction failed for this document. Ask the applicant to upload a readable replacement before verification.",
        )

    previous_document_status = document.get("status")
    previous_application_status = application["status"]
    new_document_status = DOCUMENT_VERIFIED if decision == "VERIFY" else DOCUMENT_DEFICIENT
    new_application_status = previous_application_status

    db[DOCUMENTS].update_one({"id": document_id}, {"$set": {"status": new_document_status}})

    if decision == "DEFICIENT":
        new_application_status = STATUS_DEFICIENT
        db[APPLICATIONS].update_one(
            {"id": application["id"]},
            {"$set": {"status": STATUS_DEFICIENT, "admin_remarks": remarks, "updated_at": utcnow()}},
        )
    else:
        # Once every required document is verified and the checks pass, the
        # application is ready for a decision rather than sitting deficient.
        scheme = get_scheme_by_id(db, application["scheme_id"])
        required = required_document_ids(scheme_config(scheme))
        verified = verified_document_types(get_documents(db, application["id"]))
        evaluation = application.get("rule_evaluation") or {}
        if not (required - verified) and evaluation.get("pass_fail", False):
            new_application_status = STATUS_UNDER_REVIEW
            db[APPLICATIONS].update_one(
                {"id": application["id"]},
                {"$set": {"status": STATUS_UNDER_REVIEW, "updated_at": utcnow()}},
            )

    record_audit(
        db,
        application_id=application["id"],
        actor_email=principal.email,
        actor_role=principal.role,
        action=f"DOCUMENT_{decision}",
        from_status=previous_document_status,
        to_status=new_document_status,
        remarks=f"{document['doc_type']}: {remarks}",
    )
    notify(
        db,
        applicant_id=application["applicant_id"],
        application_id=application["id"],
        title=f"Document {decision.lower()}",
        message=f"{document['doc_type'].replace('_', ' ').title()}: {remarks}",
    )
    if previous_application_status != new_application_status:
        record_audit(
            db,
            application_id=application["id"],
            actor_email=principal.email,
            actor_role=principal.role,
            action="APPLICATION_STATUS_UPDATED_AFTER_DOCUMENT_REVIEW",
            from_status=previous_application_status,
            to_status=new_application_status,
            remarks=remarks,
        )

    return DocumentVerificationResult(
        document_id=document_id,
        application_id=application["id"],
        document_status=new_document_status,
        application_status=new_application_status,
        review_remarks=remarks,
    )


# --- Review queue ---

@router.get("/queue", response_model=PaginatedApplications)
def get_review_queue(
    sort_by: str = Query("confidence_score", pattern="^(confidence_score|created_at|status|application_no)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    status: Optional[str] = None,
    scheme_code: Optional[str] = None,
    search: Optional[str] = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """The officer review queue, filtered, sorted and paginated."""
    query: Dict[str, Any] = {}
    if status and status.upper() != "ALL":
        query["status"] = status.upper()
    if scheme_code and scheme_code.upper() != "ALL":
        scheme = get_scheme_by_code(db, scheme_code)
        query["scheme_id"] = scheme["id"] if scheme else -1
    if search:
        escaped = search.strip()[:120]
        # Application numbers live on one collection and applicant names on
        # another, so resolve matching applicant ids before querying.
        matching = [
            record["id"]
            for record in db[APPLICANTS].find(
                {
                    "$or": [
                        {"full_name": {"$regex": escaped, "$options": "i"}},
                        {"email": {"$regex": escaped, "$options": "i"}},
                    ]
                },
                {"id": 1},
            )
        ]
        query["$or"] = [
            {"application_no": {"$regex": escaped, "$options": "i"}},
            {"applicant_id": {"$in": matching}},
        ]

    sort_key = QUEUE_SORT_FIELDS.get(sort_by, QUEUE_SORT_FIELDS["confidence_score"])
    direction = ASCENDING if order == "asc" else DESCENDING
    cursor = db[APPLICATIONS].find(query).sort([(field, direction) for field, _ in sort_key])
    total = db[APPLICATIONS].count_documents(query)
    page_items = list(cursor.skip((page - 1) * page_size).limit(page_size))

    return PaginatedApplications(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
        items=[ApplicationRead(**payload) for payload in application_payloads(db, page_items)],
    )


# --- Adjudication ---

@router.post("/applications/{app_id:int}/decision", response_model=ApplicationRead)
def submit_admin_decision(
    app_id: int,
    payload: AdminDecisionRequest,
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Record a reasoned officer decision on an application."""
    application = get_application(db, app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application["status"] in FINAL_STATUSES:
        raise HTTPException(status_code=409, detail="A final decision cannot be changed.")

    decision = payload.decision.strip().upper()
    status = DECISION_MAP.get(decision)
    if not status:
        raise HTTPException(
            status_code=400,
            detail="Decision must be APPROVE, REJECT, DEFICIENT, UNDER_REVIEW, SELECT, or NOT_SELECT.",
        )
    remarks = (payload.remarks or "").strip()
    if status in DECISIONS_REQUIRING_REASONS and not remarks:
        raise HTTPException(status_code=422, detail="Record the officer's reason before saving this decision.")

    if status == STATUS_APPROVED:
        if application["status"] != STATUS_SELECTED:
            raise HTTPException(status_code=409, detail="Record the authorised selection before approving the award.")
        required = required_document_ids(scheme_config(get_scheme_by_id(db, application["scheme_id"])))
        missing = required - verified_document_types(get_documents(db, app_id))
        if missing:
            raise HTTPException(
                status_code=409,
                detail=f"Officer verification is required for these documents before approval: {', '.join(sorted(missing))}.",
            )

    if status == STATUS_SELECTED:
        blockers, _ = selection_blockers(db, application)
        if blockers:
            raise HTTPException(status_code=409, detail=" ".join(blockers))

    previous_status = application["status"]
    updates: Dict[str, Any] = {
        "status": status,
        "admin_remarks": remarks,
        "updated_at": utcnow(),
    }
    if status == STATUS_SELECTED:
        updates["selected_at"] = utcnow()
    db[APPLICATIONS].update_one({"id": app_id}, {"$set": updates})

    record_audit(
        db,
        application_id=app_id,
        actor_email=principal.email,
        actor_role=principal.role,
        action=f"OFFICER_{status}",
        from_status=previous_status,
        to_status=status,
        remarks=remarks,
    )

    if status == STATUS_APPROVED and not get_award_by_application(db, app_id):
        db[AWARDS].insert_one({
            "id": next_id(db, AWARDS),
            "application_id": app_id,
            "award_status": "ACTIVE",
            "approved_amount": None,
            "currency": "INR",
            "start_date": None,
            "end_date": None,
            "next_review_date": None,
            "officer_remarks": remarks,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        })

    if status in DECISIONS_REQUIRING_REASONS:
        notify(
            db,
            applicant_id=application["applicant_id"],
            application_id=app_id,
            title=f"Application {status.replace('_', ' ').title()}",
            message=remarks,
        )

    return ApplicationRead(**application_payload(db, get_application(db, app_id)))


@router.get("/applications/{app_id:int}/audit", response_model=List[AuditEventRead])
def get_application_audit(
    app_id: int,
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """The full workflow history for one application."""
    if not get_application(db, app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    return [AuditEventRead(**event) for event in audit_history(db, app_id)]


# --- Ranking ---

@router.get("/selection", response_model=SelectionResult)
def get_selection_rankings(
    scheme_code: str,
    slots: int = Query(10, ge=1, le=500),
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Marks-based ordering aid. It never selects or rejects an applicant."""
    scheme = get_scheme_by_code(db, scheme_code)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    config = scheme_config(scheme)
    selection_config = config.get("selection_config", {})
    ranking_field = selection_config.get("ranking_field")

    applications = list(db[APPLICATIONS].find({"scheme_id": scheme["id"]}))
    required = required_document_ids(config)

    candidates: List[dict] = []
    for application in applications:
        declared = application.get("declared_data") or {}
        marks: Optional[float] = None
        if ranking_field:
            try:
                marks = float(declared.get(ranking_field))
                if not math.isfinite(marks):
                    marks = None
            except (TypeError, ValueError):
                marks = None

        verified = verified_document_types(get_documents(db, application["id"]))
        evaluation = application.get("rule_evaluation") or {}
        eligible = (
            application["status"] not in {STATUS_REJECTED, STATUS_DEFICIENT, STATUS_NOT_SELECTED, STATUS_WITHDRAWN}
            and bool(evaluation.get("pass_fail", False))
            and not (required - verified)
            and (marks is not None or not ranking_field)
        )
        candidates.append({
            "application_id": application["id"],
            "application_no": application["application_no"],
            "applicant_name": _applicant_name(db, application),
            "scheme_code": scheme["code"],
            "status": application["status"],
            "mark_field": ranking_field,
            "marks": marks,
            "ranking_mode": selection_config.get("ranking_mode", "MANUAL_REVIEW"),
            "eligible_for_ranking": eligible,
            "human_decision_required": True,
            "_sort_marks": marks,
            "_created_at": application.get("created_at") or utcnow(),
        })

    candidates.sort(key=lambda item: (
        not item["eligible_for_ranking"],
        -(item["_sort_marks"] if item["_sort_marks"] is not None else -1),
        item["_created_at"],
        item["application_no"],
    ))

    eligible_rank = 0
    for index, candidate in enumerate(candidates, start=1):
        candidate["rank"] = index if candidate["eligible_for_ranking"] else None
        if candidate["eligible_for_ranking"]:
            eligible_rank += 1
        candidate["within_available_slots"] = candidate["eligible_for_ranking"] and eligible_rank <= slots
        candidate.pop("_sort_marks")
        candidate.pop("_created_at")

    return SelectionResult(
        scheme_code=scheme["code"],
        scheme_name=scheme["name"],
        mark_field=ranking_field,
        slots=slots,
        notice=(
            "Advisory ranking only. Verify the published scheme criteria, documents, quota and roster, "
            "then record the decision as an authorised officer."
        ),
        candidates=candidates,
    )


def _applicant_name(db: Database, application: dict) -> str:
    applicant = db[APPLICANTS].find_one({"id": application["applicant_id"]}, {"full_name": 1})
    return applicant["full_name"] if applicant else "Applicant"


# --- Dashboard and reports ---

@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Aggregated workflow counts across every scheme."""
    by_status: Dict[str, int] = {}
    by_scheme: Dict[str, Dict[str, int]] = {}

    for application in db[APPLICATIONS].find({}, {"status": 1, "scheme_id": 1}):
        by_status[application["status"]] = by_status.get(application["status"], 0) + 1
        scheme_code = application.get("scheme_code", "UNKNOWN")
        summary = by_scheme.setdefault(
            scheme_code,
            {"total": 0, "approved": 0, "deficient": 0, "under_review": 0, "rejected": 0, "withdrawn": 0},
        )
        summary["total"] += 1
        if application["status"] == STATUS_APPROVED:
            summary["approved"] += 1
        elif application["status"] == STATUS_DEFICIENT:
            summary["deficient"] += 1
        elif application["status"] in {STATUS_UNDER_REVIEW, STATUS_SUBMITTED, STATUS_SELECTED}:
            summary["under_review"] += 1
        elif application["status"] == STATUS_REJECTED:
            summary["rejected"] += 1
        elif application["status"] == STATUS_WITHDRAWN:
            summary["withdrawn"] += 1

    return DashboardSummary(
        total_applications=db[APPLICATIONS].count_documents({}),
        by_status=by_status,
        by_scheme=by_scheme,
        active_awards=db[AWARDS].count_documents({"award_status": "ACTIVE"}),
        total_awards=db[AWARDS].count_documents({}),
        pending_payments=db[AWARD_PAYMENTS].count_documents(
            {"status": {"$in": [PAYMENT_STATES[0], PAYMENT_STATES[1]]}}
        ),
        generated_at=utcnow(),
    )


@router.get("/report.csv")
def download_report(
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Download the application register as CSV."""
    applicants = {
        doc["id"]: doc
        for doc in db[APPLICANTS].find({}, {"id": 1, "full_name": 1, "email": 1})
    }
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Application number", "Scheme", "Applicant", "Email",
        "Status", "Submitted", "Rule indicator", "Documents", "Officer remarks",
    ])

    def safe_cell(value: Any) -> str:
        text = "" if value is None else str(value)
        # Neutralise spreadsheet formula injection from free-text fields.
        return f"'{text}" if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text

    for application in db[APPLICATIONS].find().sort("created_at", DESCENDING):
        applicant = applicants.get(application["applicant_id"], {})
        writer.writerow([safe_cell(value) for value in [
            application["application_no"],
            application.get("scheme_code", ""),
            applicant.get("full_name", ""),
            applicant.get("email", ""),
            application["status"],
            application["created_at"].isoformat() if application.get("created_at") else "",
            application.get("confidence_score"),
            len(get_documents(db, application["id"])),
            application.get("admin_remarks"),
        ]])

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=arohan-application-report.csv"},
    )


# --- Awards and payments ---

@router.get("/awards", response_model=List[AwardRead])
def get_awards(
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Every award record, most recently updated first."""
    return [AwardRead(**payload) for payload in award_payloads(db, list_awards(db))]


@router.put("/applications/{app_id:int}/award", response_model=AwardRead)
def update_award(
    app_id: int,
    payload: AwardUpdateRequest,
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Update the award lifecycle and sanction details of an approved application."""
    application = get_application(db, app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application["status"] != STATUS_APPROVED:
        raise HTTPException(status_code=409, detail="Only an approved application can have an award record.")

    state = payload.award_status.strip().upper()
    if state not in AWARD_STATES:
        raise HTTPException(status_code=422, detail=f"Award status must be one of {', '.join(AWARD_STATES)}.")
    if payload.approved_amount is not None and (
        not math.isfinite(payload.approved_amount) or payload.approved_amount < 0
    ):
        raise HTTPException(status_code=422, detail="Approved amount must be a non-negative finite number.")
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="Award end date cannot precede its start date.")

    award = get_award_by_application(db, app_id)
    if not award:
        award = {
            "id": next_id(db, AWARDS),
            "application_id": app_id,
            "award_status": state,
            "approved_amount": None,
            "currency": "INR",
            "start_date": None,
            "end_date": None,
            "next_review_date": None,
            "officer_remarks": "",
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        db[AWARDS].insert_one(dict(award))

    already_committed = committed_payment_total(db, award["id"], COMMITTED_PAYMENT_STATES)
    if payload.approved_amount is not None and payload.approved_amount < already_committed:
        raise HTTPException(status_code=409, detail="Approved amount cannot be lower than recorded payment milestones.")

    previous_status = award.get("award_status")
    db[AWARDS].update_one(
        {"id": award["id"]},
        {"$set": {
            "award_status": state,
            "approved_amount": payload.approved_amount,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "next_review_date": payload.next_review_date,
            "officer_remarks": (payload.officer_remarks or "").strip(),
            "updated_at": utcnow(),
        }},
    )
    record_audit(
        db,
        application_id=app_id,
        actor_email=principal.email,
        actor_role=principal.role,
        action="AWARD_RECORD_UPDATED",
        from_status=previous_status,
        to_status=state,
        remarks=(payload.officer_remarks or "").strip(),
    )
    notify(
        db,
        applicant_id=application["applicant_id"],
        application_id=app_id,
        title="Award record updated",
        message=f"Your award status is now {state}. {(payload.officer_remarks or '').strip()}".strip(),
    )
    return AwardRead(**award_payload(db, get_award(db, award["id"])))


@router.post("/awards/{award_id:int}/payments")
def add_award_payment(
    award_id: int,
    payload: PaymentCreateRequest,
    principal: Principal = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Record a payment milestone against an award. No funds are transferred."""
    award = get_award(db, award_id)
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    if not payload.period.strip():
        raise HTTPException(status_code=422, detail="Provide a payment period.")
    if not math.isfinite(payload.amount) or payload.amount <= 0:
        raise HTTPException(status_code=422, detail="Provide a positive finite payment amount.")

    state = payload.status.strip().upper()
    if state not in PAYMENT_STATES:
        raise HTTPException(status_code=422, detail=f"Payment status must be one of {', '.join(PAYMENT_STATES)}.")

    if award.get("approved_amount") is not None:
        already_committed = committed_payment_total(db, award_id, COMMITTED_PAYMENT_STATES)
        if already_committed + payload.amount > award["approved_amount"]:
            raise HTTPException(
                status_code=409,
                detail="Payment milestones cannot exceed the approved award amount.",
            )

    application = get_application(db, award["application_id"])
    payment_id = next_id(db, AWARD_PAYMENTS)
    payment = {
        "id": payment_id,
        "award_id": award_id,
        "period": payload.period.strip(),
        "amount": payload.amount,
        "status": state,
        "reference": (payload.reference or "").strip() or None,
        "paid_at": utcnow() if state == "PAID" else None,
        "created_at": utcnow(),
    }
    db[AWARD_PAYMENTS].insert_one(dict(payment))

    if application:
        notify(
            db,
            applicant_id=application["applicant_id"],
            application_id=award["application_id"],
            title="Fellowship payment milestone recorded",
            message=f"{payload.period.strip()}: {state.lower()} record for INR {payload.amount:,.2f}.",
        )
    record_audit(
        db,
        application_id=award["application_id"],
        actor_email=principal.email,
        actor_role=principal.role,
        action=f"PAYMENT_MILESTONE_{state}",
        remarks=f"{payload.period.strip()}: INR {payload.amount:,.2f}; ref {payload.reference or 'not provided'}",
    )
    return {
        "id": payment_id,
        "award_id": award_id,
        "period": payment["period"],
        "amount": payment["amount"],
        "status": payment["status"],
        "reference": payment["reference"],
        "paid_at": payment["paid_at"],
    }
