"""Unit tests for password hashing, session tokens and login throttling."""

import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from config import get_settings
from database import USERS
from security import (
    LOGIN_ATTEMPT_LIMIT,
    Principal,
    clear_login_failures,
    hash_password,
    is_login_throttled,
    issue_token,
    normalise_email,
    record_login_failure,
    require_admin,
    require_applicant,
    require_principal,
    reset_throttle_state,
    validate_password_strength,
    verify_password,
)


class PasswordTests(unittest.TestCase):
    def test_hash_is_salted_so_equal_passwords_differ(self):
        first = hash_password("Correct@Horse9")
        second = hash_password("Correct@Horse9")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("Correct@Horse9", first))
        self.assertTrue(verify_password("Correct@Horse9", second))

    def test_wrong_password_is_rejected(self):
        stored = hash_password("Correct@Horse9")
        self.assertFalse(verify_password("Wrong@Horse9", stored))

    def test_a_malformed_hash_never_authenticates(self):
        for candidate in ("", "not-a-bcrypt-hash", "$2b$12$tooshort"):
            with self.subTest(candidate=candidate):
                self.assertFalse(verify_password("Correct@Horse9", candidate))

    def test_weak_passwords_are_reported_with_a_reason(self):
        minimum = get_settings().min_password_length
        # Fewer than two character classes, or too short.
        for candidate in ("short", "alllowercaseletters", "ALLUPPERCASELONG", "1234567890"):
            with self.subTest(candidate=candidate):
                self.assertTrue(validate_password_strength(candidate, minimum))

    def test_two_character_classes_are_enough(self):
        minimum = get_settings().min_password_length
        self.assertIsNone(validate_password_strength("ALLUPPERCASE123", minimum))

    def test_surrounding_whitespace_is_refused(self):
        minimum = get_settings().min_password_length
        self.assertTrue(validate_password_strength(" Correct@Horse9 ", minimum))

    def test_a_strong_password_is_accepted(self):
        minimum = get_settings().min_password_length
        self.assertIsNone(validate_password_strength("Correct@Horse9", minimum, "student@example.com"))

    def test_a_password_containing_the_email_is_refused(self):
        minimum = get_settings().min_password_length
        problem = validate_password_strength(
            "Student@example.edu9", minimum, "student@example.edu"
        )
        self.assertIsNotNone(problem)

    def test_email_normalisation_is_case_and_space_insensitive(self):
        self.assertEqual(normalise_email("  Student@Example.COM "), "student@example.com")


class _FakeCollection:
    """The smallest collection surface `require_principal` needs."""

    def __init__(self, documents):
        self._documents = documents

    def find_one(self, query):
        for document in self._documents:
            if all(document.get(key) == value for key, value in query.items()):
                return document
        return None


class _FakeDatabase:
    def __init__(self, users):
        self._users = users

    def __getitem__(self, name):
        if name != USERS:
            raise KeyError(name)
        return _FakeCollection(self._users)


class SessionSecurityTests(unittest.TestCase):
    def setUp(self):
        self.principal = Principal(
            email="student@example.edu", role="applicant", name="Student", user_id=42
        )
        self.db = _FakeDatabase([
            {"id": 42, "email": "student@example.edu", "role": "applicant", "is_active": True},
        ])

    def _credentials(self, token):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    def test_signed_token_resolves_principal(self):
        token = issue_token(self.principal)
        resolved = require_principal(self._credentials(token), self.db)
        self.assertEqual(resolved, self.principal)

    def test_missing_credentials_are_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            require_principal(None, self.db)
        self.assertEqual(caught.exception.status_code, 401)

    def test_a_non_bearer_scheme_is_rejected(self):
        token = issue_token(self.principal)
        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials=token)
        with self.assertRaises(HTTPException) as caught:
            require_principal(credentials, self.db)
        self.assertEqual(caught.exception.status_code, 401)

    def test_tampered_token_is_rejected(self):
        token = issue_token(self.principal)
        body, signature = token.split(".", 1)
        altered = ("A" if body[0] != "A" else "B") + body[1:]
        with self.assertRaises(HTTPException) as caught:
            require_principal(self._credentials(f"{altered}.{signature}"), self.db)
        self.assertEqual(caught.exception.status_code, 401)

    def test_expired_token_is_rejected(self):
        ttl = get_settings().token_ttl_seconds
        with patch("security.time.time", return_value=1000):
            token = issue_token(self.principal)
        with patch("security.time.time", return_value=1000 + ttl + 1):
            with self.assertRaises(HTTPException) as caught:
                require_principal(self._credentials(token), self.db)
        self.assertEqual(caught.exception.status_code, 401)

    def test_a_deleted_account_cannot_keep_using_its_token(self):
        token = issue_token(self.principal)
        empty = _FakeDatabase([])
        with self.assertRaises(HTTPException) as caught:
            require_principal(self._credentials(token), empty)
        self.assertEqual(caught.exception.status_code, 401)
        self.assertIn("no longer active", caught.exception.detail)

    def test_a_deactivated_account_is_refused(self):
        token = issue_token(self.principal)
        disabled = _FakeDatabase([
            {"id": 42, "email": "student@example.edu", "role": "applicant", "is_active": False},
        ])
        with self.assertRaises(HTTPException) as caught:
            require_principal(self._credentials(token), disabled)
        self.assertEqual(caught.exception.status_code, 401)

    def test_a_demoted_account_cannot_keep_officer_access(self):
        """The token claims an officer role, but the account no longer holds it."""
        officer = Principal(
            email="officer@example.gov.in", role="admin", name="Officer", user_id=7
        )
        token = issue_token(officer)
        demoted = _FakeDatabase([
            {"id": 7, "email": "officer@example.gov.in", "role": "applicant", "is_active": True},
        ])
        with self.assertRaises(HTTPException) as caught:
            require_principal(self._credentials(token), demoted)
        self.assertEqual(caught.exception.status_code, 401)
        self.assertIn("no longer valid", caught.exception.detail)

    def test_applicant_cannot_use_officer_dependency(self):
        with self.assertRaises(HTTPException) as caught:
            require_admin(self.principal)
        self.assertEqual(caught.exception.status_code, 403)

    def test_officer_cannot_use_applicant_dependency(self):
        officer = Principal(
            email="officer@example.gov.in", role="admin", name="Officer", user_id=1
        )
        with self.assertRaises(HTTPException) as caught:
            require_applicant(officer)
        self.assertEqual(caught.exception.status_code, 403)

    def test_either_role_may_be_read_as_a_principal(self):
        officer = Principal(
            email="officer@example.gov.in", role="admin", name="Officer", user_id=1
        )
        officer_db = _FakeDatabase([
            {"id": 1, "email": "officer@example.gov.in", "role": "admin", "is_active": True},
        ])
        self.assertEqual(
            require_principal(self._credentials(issue_token(officer)), officer_db), officer
        )


class LoginThrottleTests(unittest.TestCase):
    def setUp(self):
        reset_throttle_state()

    def tearDown(self):
        reset_throttle_state()

    def test_repeated_failures_eventually_throttle(self):
        email, client = "student@example.edu", "10.0.0.1"
        throttled, _ = is_login_throttled(email, client)
        self.assertFalse(throttled)

        for _ in range(LOGIN_ATTEMPT_LIMIT):
            record_login_failure(email, client)

        throttled, wait_seconds = is_login_throttled(email, client)
        self.assertTrue(throttled)
        self.assertGreater(wait_seconds, 0)

    def test_a_successful_sign_in_clears_the_counter(self):
        email, client = "student@example.edu", "10.0.0.1"
        record_login_failure(email, client)
        clear_login_failures(email, client)
        throttled, _ = is_login_throttled(email, client)
        self.assertFalse(throttled)

    def test_attempts_are_scoped_to_one_account_and_client(self):
        record_login_failure("student@example.edu", "10.0.0.1")
        throttled, _ = is_login_throttled("someone.else@example.edu", "10.0.0.1")
        self.assertFalse(throttled)
        throttled, _ = is_login_throttled("student@example.edu", "10.0.0.2")
        self.assertFalse(throttled)

    def test_throttle_window_expires(self):
        email, client = "student@example.edu", "10.0.0.1"
        for _ in range(LOGIN_ATTEMPT_LIMIT):
            record_login_failure(email, client)
        # Move past the window so the recorded attempts fall out of range.
        with patch("security.time.monotonic", return_value=time.monotonic() + 10 * 60):
            throttled, _ = is_login_throttled(email, client)
        self.assertFalse(throttled)


if __name__ == "__main__":
    unittest.main()
