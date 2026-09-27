import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

TOKEN_TTL_SECONDS = 8 * 60 * 60
AUTH_SECRET = os.getenv("AUTH_SECRET", "local-demo-only-change-before-deployment").encode("utf-8")
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    email: str
    role: str
    name: str


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def issue_token(principal: Principal) -> str:
    payload = json.dumps({
        "email": principal.email.lower(),
        "role": principal.role,
        "name": principal.name,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }, separators=(",", ":")).encode("utf-8")
    body = _encode(payload)
    signature = hmac.new(AUTH_SECRET, body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_encode(signature)}"


def require_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    unauthorized = HTTPException(status_code=401, detail="A valid session is required.")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        body, signature = credentials.credentials.split(".", 1)
        expected = _encode(hmac.new(AUTH_SECRET, body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise unauthorized
        padding = "=" * (-len(body) % 4)
        data = json.loads(base64.urlsafe_b64decode(body + padding))
        if int(data["exp"]) <= int(time.time()) or data["role"] not in {"applicant", "admin"}:
            raise unauthorized
        email = str(data["email"]).strip().lower()
        name = str(data["name"]).strip()
        if not email:
            raise unauthorized
        return Principal(email=email, role=data["role"], name=name)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise unauthorized from exc


def require_admin(principal: Principal = Depends(require_principal)) -> Principal:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Officer access is required.")
    return principal


def require_applicant(principal: Principal = Depends(require_principal)) -> Principal:
    if principal.role != "applicant":
        raise HTTPException(status_code=403, detail="Applicant access is required.")
    return principal
