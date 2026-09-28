"""Document shapes, status vocabularies and index definitions for MongoDB.

There is no ORM layer: routers read and write plain dictionaries that match the
field names documented here. Keeping the shapes and the allowed status values
in a single module stops a typo from silently creating a new field.
"""

from database import (
    APPLICATIONS,
    APPLICANTS,
    AUDIT_EVENTS,
    AWARDS,
    AWARD_PAYMENTS,
    COUNTERS,
    DOCUMENTS,
    NOTIFICATIONS,
    SCHEMES,
    USERS,
    ensure_indexes,
    utcnow,
)

# Collections are re-exported so routers can import everything they need from one place.
COLLECTIONS = (
    USERS,
    SCHEMES,
    APPLICANTS,
    APPLICATIONS,
    DOCUMENTS,
    AUDIT_EVENTS,
    NOTIFICATIONS,
    AWARDS,
    AWARD_PAYMENTS,
    COUNTERS,
)

# --- Users ---
ROLE_APPLICANT = "applicant"
ROLE_OFFICER = "admin"
USER_ROLES = (ROLE_APPLICANT, ROLE_OFFICER)

# --- Application workflow ---
STATUS_SUBMITTED = "SUBMITTED"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_DEFICIENT = "DEFICIENT"
STATUS_SELECTED = "SELECTED"
STATUS_NOT_SELECTED = "NOT_SELECTED"
STATUS_WITHDRAWN = "WITHDRAWN"

APPLICATION_STATUSES = (
    STATUS_SUBMITTED,
    STATUS_UNDER_REVIEW,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_DEFICIENT,
    STATUS_SELECTED,
    STATUS_NOT_SELECTED,
    STATUS_WITHDRAWN,
)

# A final adjudication cannot be revisited, so document edits and new decisions
# are refused once an application reaches one of these.
FINAL_STATUSES = frozenset({STATUS_APPROVED, STATUS_REJECTED})
# A withdrawn application is closed to the applicant, so it must not be edited
# or withdrawn again.
LOCKED_STATUSES = FINAL_STATUSES | {STATUS_SELECTED, STATUS_NOT_SELECTED, STATUS_WITHDRAWN}

# --- Documents ---
DOCUMENT_UPLOADED = "UPLOADED"
DOCUMENT_VERIFIED = "VERIFIED"
DOCUMENT_DEFICIENT = "DEFICIENT"
DOCUMENT_STATUSES = (DOCUMENT_UPLOADED, DOCUMENT_VERIFIED, DOCUMENT_DEFICIENT)

OCR_PENDING = "PENDING"
OCR_SUCCESS = "SUCCESS"
OCR_PARTIAL = "PARTIAL"
OCR_FAILED = "FAILED"
# Statuses whose extracted fields are reliable enough to compare against the
# applicant's declaration.
OCR_USABLE_STATUSES = (OCR_SUCCESS, OCR_PARTIAL)

# --- Awards ---
AWARD_ACTIVE = "ACTIVE"
AWARD_ON_HOLD = "ON_HOLD"
AWARD_COMPLETED = "COMPLETED"
AWARD_TERMINATED = "TERMINATED"
AWARD_STATES = (AWARD_ACTIVE, AWARD_ON_HOLD, AWARD_COMPLETED, AWARD_TERMINATED)

PAYMENT_PENDING = "PENDING"
PAYMENT_PROCESSING = "PROCESSING"
PAYMENT_PAID = "PAID"
PAYMENT_FAILED = "FAILED"
PAYMENT_STATES = (PAYMENT_PENDING, PAYMENT_PROCESSING, PAYMENT_PAID, PAYMENT_FAILED)
# Payment states that still count against the approved award amount.
COMMITTED_PAYMENT_STATES = (PAYMENT_PENDING, PAYMENT_PROCESSING, PAYMENT_PAID)


def new_user(
    *,
    user_id: int,
    email: str,
    password_hash: str,
    role: str,
    full_name: str,
    phone: str = "",
) -> dict:
    return {
        "id": user_id,
        "email": email.lower(),
        "password_hash": password_hash,
        "role": role,
        "full_name": full_name,
        "phone": phone or "",
        "is_active": True,
        "created_at": utcnow(),
        "last_login_at": None,
    }


def new_applicant(*, applicant_id: int, user_id: int, full_name: str, email: str, phone: str = "") -> dict:
    return {
        "id": applicant_id,
        "user_id": user_id,
        "full_name": full_name,
        "email": email.lower(),
        "phone": phone or "",
        "category": "ST",
        "caste_certificate_no": None,
        "annual_income": None,
        "created_at": utcnow(),
    }


def new_audit_event(
    *,
    event_id: int,
    application_id: int,
    actor_email: str,
    actor_role: str,
    action: str,
    from_status: str = None,
    to_status: str = None,
    remarks: str = "",
) -> dict:
    return {
        "id": event_id,
        "application_id": application_id,
        "actor_email": actor_email,
        "actor_role": actor_role,
        "action": action,
        "from_status": from_status,
        "to_status": to_status,
        "remarks": remarks,
        "created_at": utcnow(),
    }


def new_notification(
    *,
    notification_id: int,
    applicant_id: int,
    application_id: int,
    title: str,
    message: str,
) -> dict:
    return {
        "id": notification_id,
        "applicant_id": applicant_id,
        "application_id": application_id,
        "title": title,
        "message": message,
        "read_at": None,
        "created_at": utcnow(),
    }


__all__ = [
    "COLLECTIONS",
    "APPLICATION_STATUSES",
    "AWARD_PAYMENTS",
    "AWARD_STATES",
    "COMMITTED_PAYMENT_STATES",
    "DOCUMENT_STATUSES",
    "DOCUMENT_DEFICIENT",
    "DOCUMENT_UPLOADED",
    "DOCUMENT_VERIFIED",
    "FINAL_STATUSES",
    "LOCKED_STATUSES",
    "APPLICATION_STATUSES",
    "OCR_PARTIAL",
    "OCR_PENDING",
    "OCR_SUCCESS",
    "OCR_USABLE_STATUSES",
    "PAYMENT_FAILED",
    "PAYMENT_PAID",
    "PAYMENT_PENDING",
    "PAYMENT_PROCESSING",
    "PAYMENT_STATES",
    "ROLE_APPLICANT",
    "ROLE_OFFICER",
    "STATUS_APPROVED",
    "STATUS_DEFICIENT",
    "STATUS_NOT_SELECTED",
    "STATUS_REJECTED",
    "STATUS_SELECTED",
    "STATUS_SUBMITTED",
    "STATUS_UNDER_REVIEW",
    "STATUS_WITHDRAWN",
    "USER_ROLES",
    "ensure_indexes",
    "new_applicant",
    "new_audit_event",
    "new_notification",
    "new_user",
    "utcnow",
]
