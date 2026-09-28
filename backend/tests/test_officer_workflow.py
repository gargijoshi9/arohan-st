"""End-to-end guard for the officer document-review and selection workflow.

This is the priority flow: an officer opens an application, reads each
supporting document, records a verification decision, and only then records a
merit selection. The test drives it through the real HTTP API against MongoDB so
the seeder, the GridFS sample documents, the OCR parsers and the selection gate
all have to agree.

The tests run against a throwaway database named by `AROHAN_TEST_DB`, so the
development database is never touched. Dropping that database afterwards keeps
repeat runs deterministic.
"""

import os
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# The database is resolved at import time, so the test database must be chosen
# before `config` is imported. No other test module imports `main`.
TEST_DB_NAME = os.getenv("AROHAN_TEST_DB", "arohan_st_test")
os.environ["MONGODB_DB"] = TEST_DB_NAME

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from database import close_client, get_db  # noqa: E402
from utils.seed import SEED_ACCOUNT_PASSWORD  # noqa: E402

# The officer account is bootstrapped from configuration, so the suite signs in
# with the configured password rather than inventing one.
OFFICER = {
    "email": os.getenv("BOOTSTRAP_OFFICER_EMAIL", "motaofficer@gmail.com"),
    "password": os.getenv("BOOTSTRAP_OFFICER_PASSWORD", ""),
}

# Each test drives a different seeded applicant so the tests stay independent of
# unittest's alphabetical execution order.
APPROVED_APPLICANT = "Ramesh Chandra Munda"      # seeded as a final decision
WORKFLOW_APPLICANT = "Pooja Boro"                # seeded as under review
PENDING_APPLICANT = "Sunita Devi Soren"          # seeded as submitted
DEFICIENT_APPLICANT = "Amit Tirkey"              # seeded as deficient


def drop_test_database() -> None:
    """Remove the throwaway database so the next run starts from empty."""
    try:
        client = get_db().client
        client.drop_database(TEST_DB_NAME)
    finally:
        close_client()


class OfficerDocumentWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start from an empty database so the seeder always builds a full
        # register, then drop whatever the previous run left behind.
        drop_test_database()
        cls.client_context = TestClient(main.app)
        cls.client = cls.client_context.__enter__()

        if not OFFICER["password"]:
            OFFICER["password"] = SEED_ACCOUNT_PASSWORD
        response = cls.client.post("/auth/login", json=OFFICER)
        if response.status_code != 200:
            raise RuntimeError(f"officer login failed: {response.status_code} {response.text}")
        cls.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        drop_test_database()

    def _queue(self):
        response = self.client.get("/admin/queue?page_size=100", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _application(self, name):
        return next(item for item in self._queue()["items"] if item["applicant_name"] == name)

    def test_seeded_documents_are_all_downloadable_from_gridfs(self):
        unreadable = []
        for application in self._queue()["items"]:
            for document in application.get("documents", []):
                response = self.client.get(
                    f"/private-documents/{document['id']}/file", headers=self.headers
                )
                if response.status_code != 200:
                    unreadable.append(
                        (application["application_no"], document["doc_type"], response.status_code)
                    )
                elif not response.content:
                    unreadable.append((application["application_no"], document["doc_type"], "empty"))
        self.assertEqual(unreadable, [], f"seeded documents are not readable: {unreadable}")

    def test_documents_cannot_be_changed_after_a_final_decision(self):
        application = self._application(APPROVED_APPLICANT)
        self.assertEqual(application["status"], "APPROVED")
        document = application["documents"][0]
        response = self.client.post(
            f"/admin/documents/{document['id']}/verification",
            headers=self.headers,
            json={"decision": "VERIFY", "remarks": "attempted edit after approval"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("final decision", response.json()["detail"].lower())

    def test_verification_requires_a_written_basis(self):
        application = self._application(PENDING_APPLICANT)
        document = application["documents"][0]
        response = self.client.post(
            f"/admin/documents/{document['id']}/verification",
            headers=self.headers,
            json={"decision": "VERIFY", "remarks": "   "},
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_selection_is_refused_until_every_required_document_is_verified(self):
        application = self._application(PENDING_APPLICANT)
        response = self.client.post(
            f"/admin/applications/{application['id']}/decision",
            headers=self.headers,
            json={"decision": "SELECT", "remarks": "attempted early selection"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        unverified = [
            document for document in application["documents"]
            if document["status"] != "VERIFIED"
        ]
        self.assertTrue(unverified, "gate is only meaningful while documents are unverified")

    def test_approval_is_refused_until_a_selection_is_recorded(self):
        application = self._application(DEFICIENT_APPLICANT)
        response = self.client.post(
            f"/admin/applications/{application['id']}/decision",
            headers=self.headers,
            json={"decision": "APPROVE", "remarks": "attempted approval without a selection"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("selection", response.json()["detail"].lower())

    def test_marking_a_document_deficient_returns_the_application_to_the_applicant(self):
        application = self._application(DEFICIENT_APPLICANT)
        document = application["documents"][0]
        response = self.client.post(
            f"/admin/documents/{document['id']}/verification",
            headers=self.headers,
            json={"decision": "DEFICIENT", "remarks": "Scan is illegible; upload a readable copy."},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["document_status"], "DEFICIENT")
        self.assertEqual(response.json()["application_status"], "DEFICIENT")

    def test_full_verify_select_approve_workflow(self):
        application = self._application(WORKFLOW_APPLICANT)
        app_id = application["id"]

        for document in application["documents"]:
            response = self.client.post(
                f"/admin/documents/{document['id']}/verification",
                headers=self.headers,
                json={
                    "decision": "VERIFY",
                    "remarks": f"Checked {document['doc_type']} against the issuing authority.",
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["document_status"], "VERIFIED")

        selection = self.client.post(
            f"/admin/applications/{app_id}/decision",
            headers=self.headers,
            json={"decision": "SELECT", "remarks": "Merit list approved for NFST."},
        )
        self.assertEqual(selection.status_code, 200, selection.text)
        self.assertEqual(selection.json()["status"], "SELECTED")

        approval = self.client.post(
            f"/admin/applications/{app_id}/decision",
            headers=self.headers,
            json={"decision": "APPROVE", "remarks": "Sanctioned for the current award year."},
        )
        self.assertEqual(approval.status_code, 200, approval.text)
        self.assertEqual(approval.json()["status"], "APPROVED")

        response = self.client.get(f"/admin/applications/{app_id}/audit", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        audit = response.json()
        events = audit if isinstance(audit, list) else audit.get("events", [])
        actions = [event["action"] for event in events]
        self.assertEqual(actions.count("DOCUMENT_VERIFY"), len(application["documents"]))
        self.assertIn("OFFICER_SELECTED", actions)
        self.assertIn("OFFICER_APPROVED", actions)

    def test_an_award_and_its_payments_are_recorded_on_approval(self):
        response = self.client.get("/admin/awards", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        awards = response.json()
        self.assertTrue(awards, "the seeded register must carry at least one award")
        for award in awards:
            self.assertTrue(award["application_no"])
            self.assertIn("payments", award)
            # Payments may never exceed the sanctioned amount.
            paid = sum(item["amount"] for item in award["payments"])
            self.assertLessEqual(paid, award["approved_amount"] or 0)

    def test_anonymous_callers_cannot_reach_officer_document_review(self):
        application = self._application(PENDING_APPLICANT)
        document = application["documents"][0]
        response = self.client.post(
            f"/admin/documents/{document['id']}/verification",
            json={"decision": "VERIFY", "remarks": "unauthenticated attempt"},
        )
        self.assertIn(response.status_code, (401, 403))

    def test_applicant_cannot_verify_their_own_documents(self):
        application = self._application(PENDING_APPLICANT)
        document = application["documents"][0]
        login = self.client.post(
            "/auth/login",
            json={
                "email": application["applicant_email"],
                "password": SEED_ACCOUNT_PASSWORD,
            },
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(login.json()["role"], "applicant")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = self.client.post(
            f"/admin/documents/{document['id']}/verification",
            headers=headers,
            json={"decision": "VERIFY", "remarks": "self verification attempt"},
        )
        self.assertIn(response.status_code, (401, 403))

    def test_applicant_cannot_read_another_accounts_documents(self):
        application = self._application(PENDING_APPLICANT)
        other = self._application(APPROVED_APPLICANT)
        login = self.client.post(
            "/auth/login",
            json={"email": application["applicant_email"], "password": SEED_ACCOUNT_PASSWORD},
        )
        self.assertEqual(login.status_code, 200, login.text)
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = self.client.get(
            f"/private-documents/{other['documents'][0]['id']}/file", headers=headers
        )
        self.assertIn(response.status_code, (401, 403))

    def test_a_final_decision_cannot_be_rewritten(self):
        application = self._application(APPROVED_APPLICANT)
        response = self.client.post(
            f"/admin/applications/{application['id']}/decision",
            headers=self.headers,
            json={"decision": "REJECT", "remarks": "attempted reversal of a final decision"},
        )
        self.assertEqual(response.status_code, 409, response.text)


if __name__ == "__main__":
    unittest.main()
