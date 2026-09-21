from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from database import get_db
from models import Application
from schemas import ApplicationRead, AdminDecisionRequest
from routers.applications import format_application_response

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

@router.get("/queue", response_model=List[ApplicationRead])
def get_review_queue(
    sort_by: str = Query("confidence_score", pattern="^(confidence_score|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    status: Optional[str] = None,
    scheme_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get the admin verification queue.
    Default sort is by confidence_score so officers can inspect flagged cases or fast-track high confidence cases.
    """
    query = db.query(Application)

    if status and status.upper() != "ALL":
        query = query.filter(Application.status == status.upper())

    if scheme_code and scheme_code.upper() != "ALL":
        query = query.join(Application.scheme).filter(Application.scheme.has(code=scheme_code.upper()))

    # Sort
    col = Application.confidence_score if sort_by == "confidence_score" else Application.created_at
    if order == "asc":
        query = query.order_by(asc(col))
    else:
        query = query.order_by(desc(col))

    apps = query.all()
    return [format_application_response(a) for a in apps]

@router.post("/applications/{app_id}/decision", response_model=ApplicationRead)
def submit_admin_decision(
    app_id: int,
    payload: AdminDecisionRequest,
    db: Session = Depends(get_db)
):
    """
    Officer decision action:
    - APPROVE: Marks application as APPROVED
    - REJECT: Marks application as REJECTED
    - DEFICIENT / FLAG: Marks application as DEFICIENT (requires student resubmission)
    - UNDER_REVIEW: Puts application back in UNDER_REVIEW
    """
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    decision_map = {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "DEFICIENT": "DEFICIENT",
        "FLAG": "DEFICIENT",
        "RESUBMIT": "DEFICIENT",
        "UNDER_REVIEW": "UNDER_REVIEW"
    }

    normalized_decision = decision_map.get(payload.decision.upper())
    if not normalized_decision:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision '{payload.decision}'. Allowed: APPROVE, REJECT, DEFICIENT, UNDER_REVIEW"
        )

    app.status = normalized_decision
    if payload.remarks:
        app.admin_remarks = payload.remarks

    db.commit()
    db.refresh(app)

    return format_application_response(app)
