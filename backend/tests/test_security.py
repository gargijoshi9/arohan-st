import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from security import Principal, TOKEN_TTL_SECONDS, issue_token, require_admin, require_principal


class SessionSecurityTests(unittest.TestCase):
    def setUp(self):
        self.principal = Principal(email="student@example.edu", role="applicant", name="Student")

    def test_signed_token_resolves_principal(self):
        token = issue_token(self.principal)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        self.assertEqual(require_principal(credentials), self.principal)

    def test_tampered_token_is_rejected(self):
        token = issue_token(self.principal)
        body, signature = token.split(".", 1)
        altered = ("A" if body[0] != "A" else "B") + body[1:]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=f"{altered}.{signature}")
        with self.assertRaises(HTTPException) as caught:
            require_principal(credentials)
        self.assertEqual(caught.exception.status_code, 401)

    def test_expired_token_is_rejected(self):
        with patch("security.time.time", return_value=1000):
            token = issue_token(self.principal)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("security.time.time", return_value=1000 + TOKEN_TTL_SECONDS + 1):
            with self.assertRaises(HTTPException) as caught:
                require_principal(credentials)
        self.assertEqual(caught.exception.status_code, 401)

    def test_applicant_cannot_use_officer_dependency(self):
        with self.assertRaises(HTTPException) as caught:
            require_admin(self.principal)
        self.assertEqual(caught.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
