"""Password hashing, session tokens and request guards.

Two independent checks protect every request:

1. The bearer token must carry a valid HMAC signature made with `AUTH_SECRET`
   and must not have expired. Tokens are stateless, so revoking access means
   deactivating the user record, which `require_principal` re-checks on every
   call.
2. The role and ownership rules below must permit the requested operation.

Passwords are stored only as bcrypt hashes. There is no shared or bypassable
access code anywhere in this module.
"""

import base64
import hashlib
import hmac
import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple

import bcrypt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database

from config import get_settings
from database import USERS, get_db

bearer_scheme = HTTPBearer(auto_error=False)

# bcrypt refuses inputs longer than 72 bytes. Truncating with a warning-free
# guard keeps long passphrases from raising a 500.
BCRYPT_MAX_BYTES = 72


def _hash_bytes(secret: str) -> bytes:
    return secret.encode("utf-8")


def normalise_email(email: str) -> str:
    """Canonical form of an address for storage and lookup."""
    return str(email).strip().lower()


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    encoded = _hash_bytes(password)[:BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    if not isinstance(password, str) or not password or not password_hash:
        return False
    try:
        encoded = _hash_bytes(password)[:BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str, min_length: int, email: str = "") -> Optional[str]:
    """Return a human-readable reason the password is unacceptable, or None."""
    if not isinstance(password, str):
        return "Password is required."
    if len(password) < min_length:
        return f"Password must be at least {min_length} characters long."
    if len(password) > 200:
        return "Password must be 200 characters or fewer."
    if password.strip() != password:
        return "Password must not begin or end with whitespace."
    checks = (
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
    )
    if sum(checks) < 2:
        return "Password must combine at least two of: lowercase letters, uppercase letters, digits."
    if email and email.lower() in password.lower():
        return "Password must not contain the email address."
    return None


@dataclass(frozen=True)
class Principal:
    email: str
    role: str
    name: str
    user_id: int


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def issue_token(principal: Principal) -> str:
    settings = get_settings()
    payload = json.dumps(
        {
            "sub": str(principal.user_id),
            "email": principal.email.lower(),
            "role": principal.role,
            "name": principal.name,
            "exp": int(time.time()) + settings.token_ttl_seconds,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    body = _encode(payload)
    secret = settings.auth_secret.encode("utf-8")
    signature = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_encode(signature)}"


# --- Login throttling -------------------------------------------------------
# Repeated password guesses are throttled per account+client address. The
# counter lives in process memory, so a multi-process deployment would need a
# shared store such as Redis to enforce the same limit across workers.
LOGIN_ATTEMPT_LIMIT = 8
LOGIN_ATTEMPT_WINDOW_SECONDS = 5 * 60
_attempt_log: Dict[str, Deque[float]] = defaultdict(deque)
_attempt_lock = threading.Lock()


def _throttle_key(email: str, client: str) -> str:
    return f"{email.lower()}|{client}"


def is_login_throttled(email: str, client: str) -> Tuple[bool, int]:
    """Return (throttled, seconds_remaining) for this account+client pair."""
    key = _throttle_key(email, client)
    now = time.monotonic()
    with _attempt_lock:
        history = _attempt_log[key]
        while history and now - history[0] > LOGIN_ATTEMPT_WINDOW_SECONDS:
            history.popleft()
        if len(history) >= LOGIN_ATTEMPT_LIMIT:
            wait = int(LOGIN_ATTEMPT_WINDOW_SECONDS - (now - history[0])) + 1
            return True, max(wait, 1)
    return False, 0


def record_login_failure(email: str, client: str) -> None:
    with _attempt_lock:
        _attempt_log[_throttle_key(email, client)].append(time.monotonic())


def clear_login_failures(email: str, client: str) -> None:
    with _attempt_lock:
        _attempt_log.pop(_throttle_key(email, client), None)


def reset_throttle_state() -> None:
    with _attempt_lock:
        _attempt_log.clear()


def client_address(request: Optional[Request]) -> str:
    if request is None or request.client is None:
        return "unknown"
    return request.client.host


def require_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Database = Depends(get_db),
) -> Principal:
    """Resolve a signed bearer token into a verified, still-active principal."""
    unauthorized = HTTPException(status_code=401, detail="A valid session is required.")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        body, signature = credentials.credentials.split(".", 1)
        secret = get_settings().auth_secret.encode("utf-8")
        expected = _encode(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise unauthorized
        padding = "=" * (-len(body) % 4)
        data = json.loads(base64.urlsafe_b64decode(body + padding))
        if int(data["exp"]) <= int(time.time()):
            raise unauthorized
        email = str(data["email"]).strip().lower()
        role = str(data["role"])
        name = str(data["name"]).strip()
        user_id = int(data["sub"])
        if not email or not name or role not in ("applicant", "admin"):
            raise unauthorized
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise unauthorized from exc

    # A valid signature alone is not enough: the account must still exist,
    # still be active, and still hold the role the token claims.
    user = db[USERS].find_one({"id": user_id, "email": email})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="This account is no longer active.")
    if user.get("role") != role:
        raise HTTPException(status_code=401, detail="This session is no longer valid for your account.")

    return Principal(email=email, role=role, name=name, user_id=user_id)


def require_admin(principal: Principal = Depends(require_principal)) -> Principal:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Officer access is required.")
    return principal


def require_applicant(principal: Principal = Depends(require_principal)) -> Principal:
    if principal.role != "applicant":
        raise HTTPException(status_code=403, detail="Applicant access is required.")
    return principal
