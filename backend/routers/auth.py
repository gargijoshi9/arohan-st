import os

from fastapi import APIRouter, HTTPException

from schemas import LoginRequest, LoginResponse
from security import Principal, TOKEN_TTL_SECONDS, issue_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    email = str(payload.email).strip().lower()
    if len(email) > 254 or email.count("@") != 1 or any(char.isspace() for char in email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    role = payload.role.strip().lower()
    if role == "admin":
        officer_email = os.getenv("DEMO_ADMIN_EMAIL", "motaofficer@gmail.com").strip().lower()
        officer_password = os.getenv("DEMO_ADMIN_PASSWORD", "MotaOfficer")
        if email != officer_email or payload.password != officer_password:
            raise HTTPException(status_code=401, detail="Officer credentials are incorrect.")
        name = payload.name.strip() or "MoTA Officer"
    elif role == "applicant":
        demo_otp = os.getenv("DEMO_APPLICANT_OTP", "123456")
        if payload.otp != demo_otp:
            raise HTTPException(status_code=401, detail="The demo verification code is incorrect.")
        name = payload.name.strip() or email.split("@", 1)[0]
    else:
        raise HTTPException(status_code=422, detail="Choose applicant or officer access.")

    principal = Principal(email=email, role=role, name=name)
    return LoginResponse(
        access_token=issue_token(principal),
        expires_in=TOKEN_TTL_SECONDS,
        role=role,
        email=email,
        name=name,
    )
