"""Account registration, sign-in and the signed-in profile.

Accounts live in the `users` collection. Every password is stored as a bcrypt
hash, and an officer account is created once from the environment so a fresh
database is usable immediately.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo.database import Database

from config import get_settings
from database import APPLICANTS, USERS, get_db, next_id, utcnow
from models import ROLE_APPLICANT, ROLE_OFFICER, new_applicant, new_user
from schemas import LoginRequest, LoginResponse, ProfileRead, RegisterRequest
from security import (
    Principal,
    clear_login_failures,
    client_address,
    hash_password,
    is_login_throttled,
    issue_token,
    normalise_email,
    record_login_failure,
    require_principal,
    validate_password_strength,
    verify_password,
)
from services.repository import get_applicant_by_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

INVALID_CREDENTIALS = HTTPException(status_code=401, detail="Email or password is incorrect.")


def find_user(db: Database, email: str) -> Optional[dict]:
    return db[USERS].find_one({"email": normalise_email(email)})


def issue_session(db: Database, user: dict) -> LoginResponse:
    settings = get_settings()
    db[USERS].update_one({"id": user["id"]}, {"$set": {"last_login_at": utcnow()}})
    principal = Principal(
        email=user["email"],
        role=user["role"],
        name=user["full_name"],
        user_id=user["id"],
    )
    return LoginResponse(
        access_token=issue_token(principal),
        expires_in=settings.token_ttl_seconds,
        role=user["role"],
        email=user["email"],
        name=user["full_name"],
    )


@router.post("/register", response_model=LoginResponse, status_code=201)
def register(payload: RegisterRequest, db: Database = Depends(get_db)):
    """Create an applicant account with a hashed password and sign the new user in."""
    settings = get_settings()
    email = normalise_email(payload.email)

    problem = validate_password_strength(payload.password, settings.min_password_length, email)
    if problem:
        raise HTTPException(status_code=422, detail=problem)

    if find_user(db, email):
        raise HTTPException(status_code=409, detail="An account already exists for this email address.")

    applicant_id = next_id(db, APPLICANTS)
    user_id = next_id(db, USERS)
    full_name = payload.full_name.strip()
    phone = payload.phone.strip()

    db[USERS].insert_one(new_user(
        user_id=user_id,
        email=email,
        password_hash=hash_password(payload.password),
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

    user = find_user(db, email)
    return issue_session(db, user)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Database = Depends(get_db)):
    """Authenticate an applicant or officer with their email and password."""
    email = normalise_email(payload.email)
    client = client_address(request)

    throttled, wait_seconds = is_login_throttled(email, client)
    if throttled:
        raise HTTPException(
            status_code=429,
            detail=f"Too many sign-in attempts. Try again in {wait_seconds} seconds.",
        )

    user = find_user(db, email)
    # The same response is returned whether the account exists or the password
    # is wrong, so the endpoint does not reveal which emails are registered.
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        record_login_failure(email, client)
        raise INVALID_CREDENTIALS

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    clear_login_failures(email, client)
    return issue_session(db, user)


@router.get("/me", response_model=ProfileRead)
def current_profile(
    principal: Principal = Depends(require_principal),
    db: Database = Depends(get_db),
):
    """Return the signed-in account, including its applicant record when it has one."""
    user = db[USERS].find_one({"id": principal.user_id})
    if not user:
        raise HTTPException(status_code=401, detail="This account no longer exists.")
    applicant = get_applicant_by_user(db, principal.user_id)
    return ProfileRead(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        phone=user.get("phone", "") or "",
        role=user["role"],
        applicant_id=applicant["id"] if applicant else None,
        created_at=user["created_at"],
    )


@router.get("/officer-check", response_model=dict)
def officer_bootstrap_status(db: Database = Depends(get_db)):
    """Report whether an officer account exists, so the portal can show a hint."""
    return {"officer_account_exists": db[USERS].find_one({"role": ROLE_OFFICER}) is not None}
