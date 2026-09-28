"""Load scheme configuration and a representative application register into MongoDB.

Two entry points:

* `seed_schemes` loads every JSON file in `data/scheme_configs` into the
  `schemes` collection. It is idempotent, so it runs on every start-up.
* `seed_reference_records` creates a small register of accounts and
  applications covering all five schemes and the interesting workflow states.
  It only runs when the database has no applications, so a real register is
  never overwritten.

Uploaded sample documents are written into the same GridFS bucket the applicant
upload route uses, so the officer review flow exercises the identical code path
as a genuine upload.
"""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from pymongo.database import Database

from config import SCHEME_CONFIG_DIR, SAMPLE_DOC_DIR
from database import (
    APPLICATIONS,
    APPLICANTS,
    AUDIT_EVENTS,
    AWARDS,
    AWARD_PAYMENTS,
    DOCUMENTS,
    NOTIFICATIONS,
    SCHEMES,
    USERS,
    next_id,
    utcnow,
)
from models import (
    DOCUMENT_UPLOADED,
    DOCUMENT_VERIFIED,
    ROLE_APPLICANT,
    STATUS_APPROVED,
    STATUS_DEFICIENT,
    STATUS_SELECTED,
    STATUS_SUBMITTED,
    STATUS_UNDER_REVIEW,
    new_applicant,
    new_audit_event,
    new_notification,
    new_user,
)
from security import hash_password, normalise_email
from services import storage
from services.rule_engine import evaluate_application_rules

# One shared password for every seeded account. Each account is real: it holds
# a bcrypt hash in the `users` collection and signs in through /auth/login.
SEED_ACCOUNT_PASSWORD = "Arohan@Seed2025"

# Statuses that let the officer desk show every branch of the workflow.
DECISION_HISTORY = {
    STATUS_APPROVED: (
        "APPLICATION_SUBMITTED",
        "APPLICATION_STATUS_UPDATED_AFTER_DOCUMENT_REVIEW",
        "OFFICER_SELECTED",
        "OFFICER_APPROVED",
    ),
    STATUS_SELECTED: (
        "APPLICATION_SUBMITTED",
        "APPLICATION_STATUS_UPDATED_AFTER_DOCUMENT_REVIEW",
        "OFFICER_SELECTED",
    ),
    STATUS_UNDER_REVIEW: (
        "APPLICATION_SUBMITTED",
        "APPLICATION_STATUS_UPDATED_AFTER_DOCUMENT_REVIEW",
    ),
    STATUS_SUBMITTED: ("APPLICATION_SUBMITTED",),
    STATUS_DEFICIENT: (
        "APPLICATION_SUBMITTED",
        "DOCUMENT_DEFICIENT",
    ),
}


def read_scheme_configs() -> List[Dict[str, Any]]:
    """Every parseable scheme configuration shipped with the repository."""
    configs = []
    for path in sorted(SCHEME_CONFIG_DIR.glob("*.json")):
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Scheme configuration {path.name} could not be read: {exc}") from exc
        if not config.get("code") or not config.get("name"):
            raise ValueError(f"Scheme configuration {path.name} is missing 'code' or 'name'.")
        configs.append(config)
    if not configs:
        raise ValueError(f"No scheme configurations were found in {SCHEME_CONFIG_DIR}.")
    return configs


def seed_schemes(db: Database) -> List[str]:
    """Upsert every configured scheme. Returns the codes that are now present.

    Schemes keep the same integer `id` across updates so applications recorded
    against a scheme keep resolving to it.
    """
    written: List[str] = []
    for config in read_scheme_configs():
        eligibility = config.get("eligibility_rules", {}) or {}
        code = config["code"]
        existing = db[SCHEMES].find_one({"code": code}, {"id": 1})
        scheme_id = existing["id"] if existing and "id" in existing else next_id(db, SCHEMES)
        db[SCHEMES].update_one(
            {"code": code},
            {
                "$set": {
                    "id": scheme_id,
                    "code": code,
                    "name": config["name"],
                    "description": config.get("short_description"),
                    "degree_level": config.get("degree_level"),
                    "max_income": eligibility.get("max_annual_income"),
                    "min_percentage": eligibility.get("min_qualifying_percentage"),
                    "config": config,
                    "updated_at": utcnow(),
                },
                "$setOnInsert": {"created_at": utcnow()},
            },
            upsert=True,
        )
        written.append(code)
    return written


def sample_file(file_name: str) -> bytes:
    path = SAMPLE_DOC_DIR / file_name
    if not path.is_file():
        raise FileNotFoundError(f"Sample document {file_name} is missing from {SAMPLE_DOC_DIR}.")
    return path.read_bytes()


def create_account(
    db: Database,
    *,
    email: str,
    full_name: str,
    phone: str = "",
) -> int:
    """Create a seeded applicant account and its applicant record. Returns the user id."""
    email = normalise_email(email)
    if db[USERS].find_one({"email": email}):
        raise ValueError(f"Cannot seed {email}: an account with that address already exists.")

    user_id = next_id(db, USERS)
    applicant_id = next_id(db, APPLICANTS)
    db[USERS].insert_one(new_user(
        user_id=user_id,
        email=email,
        password_hash=hash_password(SEED_ACCOUNT_PASSWORD),
        role=ROLE_APPLICANT,
        full_name=full_name,
        phone=phone,
    ))
    db[APPLICANTS].insert_one(new_applicant(
        applicant_id=applicant_id,
        user_id=user_id,
        full_name=full_name,
        email=email,
        phone=phone,
    ))
    return user_id


def create_application(
    db: Database,
    *,
    user_id: int,
    applicant_id: int,
    scheme: dict,
    declared_fields: Dict[str, Any],
    documents: Sequence[Dict[str, str]],
    status: str,
    document_status: str,
    admin_remarks: str = "",
    age_days: int = 3,
    award: Optional[Dict[str, Any]] = None,
) -> int:
    """Insert one application with its documents in GridFS. Returns the application id.

    `documents` is a sequence of `{"doc_type": ..., "file_name": ...}` pairs. Each
    file is read from the repository's sample-document directory and written into
    the GridFS bucket, so the officer download and verification routes read from
    the database exactly as they do for a real upload.
    """
    if not documents:
        raise ValueError("A seeded application must carry at least one document.")

    application_id = next_id(db, APPLICATIONS)
    created_at = utcnow() - timedelta(days=age_days)
    scheme_code = scheme["code"]
    config = scheme.get("config") or {}

    # Every scheme form declares full_name, email and phone as required, and the
    # rule engine inspects the same declared data a live submission produces.
    applicant = db[APPLICANTS].find_one({"id": applicant_id})
    declared_fields = {
        "full_name": applicant["full_name"],
        "email": applicant["email"],
        "phone": applicant.get("phone") or "",
        **declared_fields,
    }

    rule_documents = [{"doc_type": item["doc_type"]} for item in documents]
    evaluation = evaluate_application_rules(
        scheme_code=scheme_code,
        declared_fields=declared_fields,
        scheme_config=config,
        documents=rule_documents,
    )
    evaluation["confidence_score"] = max(
        15.0,
        min(
            99.0,
            98.0
            - 20.0 * sum(item["severity"] == "ERROR" for item in evaluation["mismatches"])
            - 4.0 * sum(item["severity"] == "WARNING" for item in evaluation["mismatches"]),
        ),
    )

    db[APPLICATIONS].insert_one({
        "id": application_id,
        "application_no": f"AROHAN-{scheme_code}-{created_at.year}-{10000 + application_id}",
        "scheme_id": scheme["id"],
        "scheme_code": scheme_code,
        "applicant_id": applicant_id,
        "applicant_user_id": user_id,
        "declared_data": declared_fields,
        "confidence_score": evaluation["confidence_score"],
        "status": status,
        "rule_evaluation": evaluation,
        "admin_remarks": admin_remarks,
        "created_at": created_at,
        "updated_at": created_at,
    })

    seen_types = set()
    for item in documents:
        doc_type = item["doc_type"]
        if doc_type in seen_types:
            # The unique index is one document per type per application.
            continue
        seen_types.add(doc_type)
        content = sample_file(item["file_name"])
        stored = storage.store(
            db,
            content,
            file_name=item["file_name"],
            application_id=application_id,
            doc_type=doc_type,
        )
        db[DOCUMENTS].insert_one({
            "id": next_id(db, DOCUMENTS),
            "application_id": application_id,
            "doc_type": doc_type,
            "file_name": item["file_name"],
            "gridfs_id": stored.gridfs_id,
            "media_type": stored.media_type,
            "size_bytes": stored.length,
            "status": document_status,
            "extracted_text": content.decode("utf-8", errors="replace"),
            "ocr_status": "SUCCESS",
            "ocr_confidence": None,
            "extraction_method": "Plain text extraction",
            "parsed_fields": {},
            "failed_reason": None,
            "uploaded_at": created_at,
        })

    _write_workflow_history(db, application_id, applicant_id, status, created_at)
    if award:
        _write_award(db, application_id, award)
    return application_id


def _write_workflow_history(
    db: Database,
    application_id: int,
    applicant_id: int,
    status: str,
    created_at,
) -> None:
    """Record the audit trail and notifications implied by a seeded status."""
    officer = "officer@mota.gov.in"
    steps = DECISION_HISTORY.get(status, ("APPLICATION_SUBMITTED",))
    remarks = {
        "APPLICATION_SUBMITTED": "Application received; automated checks are advisory.",
        "APPLICATION_STATUS_UPDATED_AFTER_DOCUMENT_REVIEW": "All required documents verified by the reviewing officer.",
        "DOCUMENT_DEFICIENT": "Supporting document could not be verified as submitted.",
        "OFFICER_SELECTED": "Selected for sanction on the basis of the published scheme criteria.",
        "OFFICER_APPROVED": "Sanction approved.",
    }
    previous = STATUS_SUBMITTED
    for index, action in enumerate(steps):
        to_status = status if index == len(steps) - 1 else previous
        db[AUDIT_EVENTS].insert_one(new_audit_event(
            event_id=next_id(db, AUDIT_EVENTS),
            application_id=application_id,
            actor_email=officer if action.startswith(("OFFICER_", "DOCUMENT_")) else "applicant@mota.gov.in",
            actor_role="admin" if action.startswith(("OFFICER_", "DOCUMENT_")) else ROLE_APPLICANT,
            action=action,
            from_status=None if index == 0 else previous,
            to_status=to_status,
            remarks=remarks.get(action, ""),
        ))
        previous = to_status

    if status in {STATUS_APPROVED, STATUS_SELECTED, STATUS_DEFICIENT}:
        db[NOTIFICATIONS].insert_one(new_notification(
            notification_id=next_id(db, NOTIFICATIONS),
            applicant_id=applicant_id,
            application_id=application_id,
            title=f"Application {status.replace('_', ' ').title()}",
            message=remarks.get(steps[-1], "Your application status has changed."),
        ))


def _write_award(db: Database, application_id: int, award: Dict[str, Any]) -> None:
    now = utcnow()
    award_id = next_id(db, AWARDS)
    amount = float(award["amount"])
    db[AWARDS].insert_one({
        "id": award_id,
        "application_id": application_id,
        "award_status": award.get("status", "ACTIVE"),
        "approved_amount": amount,
        "currency": "INR",
        "start_date": now - timedelta(days=30),
        "end_date": now + timedelta(days=335),
        "next_review_date": now + timedelta(days=180),
        "officer_remarks": award.get("remarks", ""),
        "created_at": now,
        "updated_at": now,
    })
    first = round(amount / 2, 2)
    db[AWARD_PAYMENTS].insert_one({
        "id": next_id(db, AWARD_PAYMENTS),
        "award_id": award_id,
        "period": "Installment 1",
        "amount": first,
        "status": "PAID",
        "reference": award.get("reference", "NEFT/SCHEDULED-0001"),
        "paid_at": now - timedelta(days=20),
        "created_at": now - timedelta(days=20),
    })
    db[AWARD_PAYMENTS].insert_one({
        "id": next_id(db, AWARD_PAYMENTS),
        "award_id": award_id,
        "period": "Installment 2",
        "amount": round(amount - first, 2),
        "status": "PENDING",
        "reference": None,
        "paid_at": None,
        "created_at": now,
    })


# --- The seeded register -----------------------------------------------------
# Each entry covers one scheme and one workflow branch. Declared values are
# chosen so the configured rules either pass cleanly or fail in a way an officer
# can act on.

REFERENCE_APPLICATIONS: List[Dict[str, Any]] = [
    {
        "scheme": "NFST",
        "email": "ramesh.munda@example.edu",
        "full_name": "Ramesh Chandra Munda",
        "phone": "9876543210",
        "status": STATUS_APPROVED,
        "document_status": DOCUMENT_VERIFIED,
        "age_days": 12,
        "admin_remarks": "All required documents verified. Fellowship sanctioned for three years.",
        "award": {
            "amount": 348000.0,
            "status": "ACTIVE",
            "remarks": "Full fellowship with annual contingency as per NFST norms.",
        },
        "declared_fields": {
            "category": "ST",
            "caste_certificate_no": "ST/JH/2023/88921",
            "annual_family_income": 280000,
            "course_enrolled": "Ph.D",
            "course_level": "Post-Doctoral Research",
            "study_mode": "Regular / Full-time",
            "institution_category": "Central/State Government funded",
            "applicant_age": 29,
            "university_name": "Jawaharlal Nehru University, New Delhi",
            "recognized_course": "Yes",
            "eligible_institution": "Yes",
            "notified_institution": "Yes",
            "other_scholarship": "No",
            "pg_percentage": 68.5,
        },
        "documents": [
            {"doc_type": "caste_cert", "file_name": "st_caste_certificate_sample.txt"},
            {"doc_type": "institution_proof", "file_name": "ramesh_institution_recognition.txt"},
            {"doc_type": "admission_letter", "file_name": "phd_admission_letter_sample.txt"},
            {"doc_type": "pg_marksheet", "file_name": "ramesh_pg_marksheet.txt"},
        ],
    },
    {
        "scheme": "NFST",
        "email": "pooja.boro@example.ac.in",
        "full_name": "Pooja Boro",
        "phone": "9864012345",
        "status": STATUS_UNDER_REVIEW,
        "document_status": DOCUMENT_UPLOADED,
        "age_days": 4,
        "declared_fields": {
            "category": "ST",
            "caste_certificate_no": "ST/AS/2023/33918",
            "annual_family_income": 190000,
            "course_enrolled": "Ph.D",
            "course_level": "Post-Doctoral Research",
            "study_mode": "Regular / Full-time",
            "institution_category": "Central/State Government funded",
            "applicant_age": 25,
            "university_name": "Gauhati University",
            "recognized_course": "Yes",
            "eligible_institution": "Yes",
            "notified_institution": "Yes",
            "other_scholarship": "No",
            "pg_percentage": 62.0,
        },
        "documents": [
            {"doc_type": "caste_cert", "file_name": "pooja_caste_certificate.txt"},
            {"doc_type": "admission_letter", "file_name": "pooja_admission_letter.txt"},
            {"doc_type": "pg_marksheet", "file_name": "pooja_pg_marksheet.txt"},
            {"doc_type": "institution_proof", "file_name": "pooja_institution_recognition.txt"},
        ],
    },
    {
        "scheme": "NOS",
        "email": "sunita.soren@example.com",
        "full_name": "Sunita Devi Soren",
        "phone": "9811223344",
        "status": STATUS_SUBMITTED,
        "document_status": DOCUMENT_UPLOADED,
        "age_days": 2,
        "declared_fields": {
            "category": "ST",
            "caste_certificate_no": "ST/OD/2022/45109",
            "applicant_age": 27,
            "annual_family_income": 350000,
            "course_level": "Master’s",
            "qs_top_1000": "No",
            "one_child_self_certified": "Yes",
            "prior_award": "No",
            "admission_stage": "Already pursuing",
            "is_orphan": "No",
            "destination_country": "United Kingdom",
            "foreign_university": "University of Edinburgh",
            "foreign_course": "MSc in Ecological Economics",
            "has_unconditional_offer": "Yes",
            "qualifying_percentage": 71.4,
            "passport_number": "Z6543219",
        },
        "documents": [
            {"doc_type": "caste_cert", "file_name": "sunita_caste_certificate.txt"},
            {"doc_type": "income_cert", "file_name": "sunita_income_certificate.txt"},
            {"doc_type": "dob_proof", "file_name": "sunita_dob_proof.txt"},
            {"doc_type": "qualifying_marks", "file_name": "sunita_qualifying_marks.txt"},
            {"doc_type": "one_child_declaration", "file_name": "sunita_one_child_declaration.txt"},
            {"doc_type": "admission_proof", "file_name": "foreign_university_offer_sample.txt"},
        ],
    },
    {
        # Declared income and marks both fall outside the NOS ceilings, so the
        # configured rules raise the errors an officer acts on.
        "scheme": "NOS",
        "email": "amit.tirkey@example.com",
        "full_name": "Amit Tirkey",
        "phone": "9933445566",
        "status": STATUS_DEFICIENT,
        "document_status": DOCUMENT_UPLOADED,
        "age_days": 6,
        "admin_remarks": (
            "Declared family income exceeds the NOS ceiling and the qualifying "
            "percentage is below the required minimum. A corrected declaration or "
            "supporting evidence is needed."
        ),
        "declared_fields": {
            "category": "ST",
            "caste_certificate_no": "ST/CG/2021/11029",
            "applicant_age": 31,
            "annual_family_income": 780000,
            "course_level": "Master’s",
            "qs_top_1000": "No",
            "one_child_self_certified": "Yes",
            "prior_award": "No",
            "admission_stage": "Offer / preliminary offer",
            "is_orphan": "No",
            "destination_country": "Australia",
            "foreign_university": "University of Melbourne",
            "foreign_course": "Master of Environmental Science",
            "has_unconditional_offer": "No",
            "qualifying_percentage": 54.5,
            "passport_number": "T9988771",
        },
        "documents": [
            {"doc_type": "caste_cert", "file_name": "amit_caste_certificate.txt"},
            {"doc_type": "income_cert", "file_name": "amit_income_certificate.txt"},
        ],
    },
    {
        "scheme": "PRE_MATRIC",
        "email": "kiran.baiga@example.edu",
        "full_name": "Kiran Kumar Baiga",
        "phone": "9123456780",
        "status": STATUS_APPROVED,
        "document_status": DOCUMENT_VERIFIED,
        "age_days": 9,
        "admin_remarks": "School recognition and domicile confirmed. Class IX award sanctioned.",
        "award": {
            "amount": 12000.0,
            "status": "ACTIVE",
            "remarks": "Day-scholar maintenance allowance plus books grant for Class IX.",
        },
        "declared_fields": {
            "category": "ST",
            "caste_certificate_no": "ST/JH/2025/50218",
            "annual_family_income": 184000,
            "is_orphan": "No",
            "class_studying": "IX",
            "eligible_school": "Yes",
            "other_scholarship": "No",
            "class_repeated": "No",
            "domicile_state": "Jharkhand",
            "hostel_status": "Day Scholar",
            "is_divyangjan": "No",
        },
        "documents": [
            {"doc_type": "caste_cert", "file_name": "kiran_caste_certificate.txt"},
            {"doc_type": "income_cert", "file_name": "kiran_income_certificate.txt"},
            {"doc_type": "domicile_cert", "file_name": "kiran_domicile_certificate.txt"},
            {"doc_type": "school_enrolment", "file_name": "kiran_school_enrolment.txt"},
            {"doc_type": "bank_aadhaar", "file_name": "kiran_bank_aadhaar.txt"},
            {"doc_type": "disability_cert", "file_name": "kiran_disability_certificate.txt"},
        ],
    },
    {
        "scheme": "POST_MATRIC",
        "email": "deepak.nayak@example.com",
        "full_name": "Deepak Nayak",
        "phone": "9437011223",
        "status": STATUS_UNDER_REVIEW,
        "document_status": DOCUMENT_UPLOADED,
        "age_days": 1,
        "declared_fields": {
            "category": "ST",
            "caste_certificate_no": "ST/OD/2025/33471",
            "annual_family_income": 212400,
            "is_orphan": "No",
            "course_name": "+2 Science",
            "recognized_course": "Yes",
            "eligible_institution": "Yes",
            "other_scholarship": "No",
            "top_class_institute": "No",
            "domicile_state": "Odisha",
            "hostel_status": "Day Scholar",
        },
        "documents": [
            {"doc_type": "caste_cert", "file_name": "deepak_caste_certificate.txt"},
            {"doc_type": "income_cert", "file_name": "deepak_income_certificate.txt"},
            {"doc_type": "domicile_cert", "file_name": "deepak_domicile_certificate.txt"},
            {"doc_type": "marksheets", "file_name": "deepak_marksheets.txt"},
            {"doc_type": "admission_proof", "file_name": "deepak_admission_proof.txt"},
            {"doc_type": "bank_aadhaar", "file_name": "deepak_bank_aadhaar.txt"},
        ],
    },
    {
        "scheme": "TOP_CLASS",
        "email": "priya.deb@example.com",
        "full_name": "Priya Kumari Deb",
        "phone": "7080123456",
        "status": STATUS_SELECTED,
        "document_status": DOCUMENT_VERIFIED,
        "age_days": 3,
        "admin_remarks": "Merit admission to a notified institution and course confirmed. Selected for sanction.",
        "declared_fields": {
            "category": "ST",
            "caste_certificate_no": "ST/AS/2025/72103",
            "annual_family_income": 472000,
            "is_orphan": "No",
            "course_level": "Graduate",
            "notified_institution": "Yes",
            "admitted_on_merit": "Yes",
            "management_quota": "No",
            "other_scholarship": "No",
            "married": "No",
            "university_name": "Indian Institute of Technology (BHU), Varanasi",
            "course_name": "Bachelor of Technology in Computer Science and Engineering",
        },
        "documents": [
            {"doc_type": "caste_cert", "file_name": "priya_caste_certificate.txt"},
            {"doc_type": "income_cert", "file_name": "priya_income_certificate.txt"},
            {"doc_type": "admission_proof", "file_name": "priya_admission_proof.txt"},
            {"doc_type": "institution_course_proof", "file_name": "priya_institution_course_proof.txt"},
            {"doc_type": "marksheets", "file_name": "priya_marksheets.txt"},
            {"doc_type": "bank_aadhaar", "file_name": "priya_bank_aadhaar.txt"},
        ],
    },
]


def seed_reference_records(db: Database) -> int:
    """Create the representative application register. Returns the count written.

    This is a no-op once the database holds any application, so it never
    duplicates records on repeated start-ups. If a step fails part-way the
    records this call created are removed, so a failed seed cannot leave an
    unusable half-populated register behind.
    """
    if db[APPLICATIONS].count_documents({}) > 0:
        return 0

    schemes = {doc["code"]: doc for doc in db[SCHEMES].find()}
    created_users: List[int] = []
    created_applicants: List[int] = []
    created_applications: List[int] = []

    try:
        for entry in REFERENCE_APPLICATIONS:
            scheme = schemes.get(entry["scheme"])
            if not scheme:
                raise ValueError(
                    f"Cannot seed {entry['scheme']}: the scheme is not present. Run seed_schemes first."
                )
            user_id = create_account(
                db,
                email=entry["email"],
                full_name=entry["full_name"],
                phone=entry.get("phone", ""),
            )
            created_users.append(user_id)
            applicant = db[APPLICANTS].find_one({"user_id": user_id})
            created_applicants.append(applicant["id"])
            created_applications.append(create_application(
                db,
                user_id=user_id,
                applicant_id=applicant["id"],
                scheme=scheme,
                declared_fields=entry["declared_fields"],
                documents=entry["documents"],
                status=entry["status"],
                document_status=entry["document_status"],
                admin_remarks=entry.get("admin_remarks", ""),
                age_days=entry.get("age_days", 3),
                award=entry.get("award"),
            ))
    except Exception:
        _roll_back_seed(
            db,
            user_ids=created_users,
            applicant_ids=created_applicants,
            application_ids=created_applications,
        )
        raise

    return len(created_applications)


def _roll_back_seed(
    db: Database,
    *,
    user_ids: Sequence[int],
    applicant_ids: Sequence[int],
    application_ids: Sequence[int],
) -> None:
    """Remove exactly the records a failed seed created, plus its stray files."""
    applications = list(db[APPLICATIONS].find({"id": {"$in": list(application_ids)}}, {"_id": 1}))
    if applications:
        award_ids = [award["id"] for award in db[AWARDS].find(
            {"application_id": {"$in": list(application_ids)}}, {"id": 1}
        )]
        # Payments reference awards, so they have to go first.
        db[AWARD_PAYMENTS].delete_many({"award_id": {"$in": award_ids}})
        db[AWARDS].delete_many({"id": {"$in": award_ids}})
        db[AUDIT_EVENTS].delete_many({"application_id": {"$in": list(application_ids)}})
        db[NOTIFICATIONS].delete_many({"application_id": {"$in": list(application_ids)}})
        db[APPLICATIONS].delete_many({"id": {"$in": list(application_ids)}})

    documents = list(db[DOCUMENTS].find({"application_id": {"$in": list(application_ids)}}, {"gridfs_id": 1}))
    db[DOCUMENTS].delete_many({"application_id": {"$in": list(application_ids)}})
    for document in documents:
        storage.discard(db, document.get("gridfs_id"))

    if applicant_ids:
        db[APPLICANTS].delete_many({"id": {"$in": list(applicant_ids)}})
    if user_ids:
        db[USERS].delete_many({"id": {"$in": list(user_ids)}})


__all__ = [
    "REFERENCE_APPLICATIONS",
    "SEED_ACCOUNT_PASSWORD",
    "create_account",
    "create_application",
    "read_scheme_configs",
    "seed_reference_records",
    "seed_schemes",
]
