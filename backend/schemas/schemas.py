"""Request and response contracts for the HTTP API.

These models are the boundary the frontend codes against. Field names here must
match `frontend/src/api/types.ts`.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# --- Schemes ---

class SchemeRead(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    degree_level: Optional[str] = None
    max_income: Optional[float] = None
    min_percentage: Optional[float] = None
    config: Dict[str, Any]

    model_config = {"from_attributes": True}


# --- Authentication ---

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(default="", max_length=20)
    password: str = Field(min_length=6, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    email: str
    name: str


class ProfileRead(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str = ""
    role: str
    applicant_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Documents ---

class DocumentRead(BaseModel):
    id: int
    doc_type: str
    file_name: str
    file_path: Optional[str] = None
    status: str
    extracted_text: Optional[str] = None
    ocr_status: str = "PENDING"
    ocr_confidence: Optional[float] = None
    extraction_method: Optional[str] = None
    parsed_fields: Optional[Dict[str, Any]] = None
    failed_reason: Optional[str] = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# --- Rule evaluation ---

class RuleMismatch(BaseModel):
    field: str
    label: str
    declared_value: Any
    expected_rule: str
    severity: str = "ERROR"  # ERROR, WARNING
    description: str


class RuleEvaluation(BaseModel):
    pass_fail: bool
    confidence_score: float
    mismatches: List[RuleMismatch]
    passed_checks: List[str]
    summary: str


# --- Applications ---

class ApplicationCreate(BaseModel):
    scheme_code: str = Field(min_length=2, max_length=40)
    full_name: str = Field(min_length=2, max_length=120)
    # The applicant email always comes from the signed-in account. A body value
    # is accepted for backwards compatibility with older clients but is never
    # trusted, so a signed-in applicant cannot submit a claim for someone else.
    email: Optional[EmailStr] = None
    phone: Optional[str] = ""
    declared_fields: Dict[str, Any]


class ApplicationCorrectionRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: Optional[str] = ""
    declared_fields: Dict[str, Any]


class ApplicationRead(BaseModel):
    id: int
    application_no: str
    scheme_id: int
    scheme_code: str
    scheme_name: str
    applicant_id: int
    applicant_name: str
    applicant_email: str
    declared_data: Dict[str, Any]
    confidence_score: float
    status: str
    ai_evaluation: Optional[RuleEvaluation] = None
    admin_remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentRead] = []
    merit_score: Optional[float] = None
    selection_rank: Optional[int] = None

    model_config = {"from_attributes": True}


class PaginatedApplications(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ApplicationRead]


# --- Officer actions ---

class AdminDecisionRequest(BaseModel):
    decision: str  # APPROVE, REJECT, DEFICIENT, UNDER_REVIEW, SELECT, NOT_SELECT
    remarks: Optional[str] = ""


class DocumentVerificationRequest(BaseModel):
    decision: str
    remarks: str = Field(min_length=1, max_length=2000)


class DocumentVerificationResult(BaseModel):
    document_id: int
    application_id: int
    document_status: str
    application_status: str
    review_remarks: str


class AuditEventRead(BaseModel):
    id: int
    actor_email: str
    actor_role: str
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Selection ---

class SelectionCandidate(BaseModel):
    application_id: int
    application_no: str
    applicant_name: str
    scheme_code: str
    status: str
    mark_field: Optional[str] = None
    marks: Optional[float] = None
    ranking_mode: str
    eligible_for_ranking: bool
    human_decision_required: bool
    rank: Optional[int] = None
    within_available_slots: bool


class SelectionResult(BaseModel):
    scheme_code: str
    scheme_name: str
    mark_field: Optional[str] = None
    slots: int
    notice: str
    candidates: List[SelectionCandidate]


# --- Dashboard and reports ---

class DashboardSummary(BaseModel):
    total_applications: int
    by_status: Dict[str, int]
    by_scheme: Dict[str, Dict[str, int]]
    active_awards: int
    total_awards: int
    pending_payments: int
    generated_at: datetime


# --- Awards and payments ---

class AwardUpdateRequest(BaseModel):
    award_status: str
    approved_amount: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    officer_remarks: Optional[str] = ""


class PaymentCreateRequest(BaseModel):
    period: str = Field(min_length=1, max_length=100)
    amount: float
    status: str = "PENDING"
    reference: Optional[str] = Field(default=None, max_length=120)

    @field_validator("amount")
    @classmethod
    def _finite_amount(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Payment amount must be a finite number.")
        return value


class AwardPaymentRead(BaseModel):
    id: int
    period: str
    amount: float
    status: str
    reference: Optional[str] = None
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AwardRead(BaseModel):
    id: int
    application_id: int
    application_no: str
    applicant_name: str = ""
    applicant_email: str = ""
    scheme_code: str = ""
    award_status: str
    approved_amount: Optional[float] = None
    currency: str = "INR"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    officer_remarks: Optional[str] = None
    updated_at: datetime
    payments: List[AwardPaymentRead] = []


# --- Notifications ---

class NotificationRead(BaseModel):
    id: int
    application_id: int
    title: str
    message: str
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationReadResult(BaseModel):
    id: int
    read_at: Optional[datetime] = None
