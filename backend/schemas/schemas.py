from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class SchemeBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    degree_level: Optional[str] = None
    max_income: Optional[float] = None
    min_percentage: Optional[float] = None

class SchemeRead(SchemeBase):
    id: int
    config: Dict[str, Any]

    class Config:
        from_attributes = True

class DocumentCreate(BaseModel):
    doc_type: str
    file_name: str
    file_path: Optional[str] = None

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

    class Config:
        from_attributes = True

class ApplicationCreate(BaseModel):
    scheme_code: str
    full_name: str
    email: str
    phone: Optional[str] = ""
    declared_fields: Dict[str, Any]
    documents: Optional[List[DocumentCreate]] = []

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

    class Config:
        from_attributes = True

class AdminDecisionRequest(BaseModel):
    decision: str  # APPROVE, REJECT, DEFICIENT, UNDER_REVIEW
    remarks: Optional[str] = ""

class DocumentVerificationRequest(BaseModel):
    decision: str
    remarks: str

class ApplicationCorrectionRequest(BaseModel):
    full_name: str
    phone: Optional[str] = ""
    declared_fields: Dict[str, Any]

class LoginRequest(BaseModel):
    role: str
    email: str
    name: Optional[str] = ""
    password: Optional[str] = ""
    otp: Optional[str] = ""

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    email: str
    name: str

class AwardUpdateRequest(BaseModel):
    award_status: str
    approved_amount: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    officer_remarks: Optional[str] = ""

class PaymentCreateRequest(BaseModel):
    period: str
    amount: float
    status: str = "PENDING"
    reference: Optional[str] = None

class NotificationRead(BaseModel):
    id: int
    application_id: int
    title: str
    message: str
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ApplicantRead(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    category: str
    caste_certificate_no: Optional[str] = None
    annual_income: Optional[float] = None

    class Config:
        from_attributes = True
