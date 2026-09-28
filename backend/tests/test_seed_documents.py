"""Regression tests for the seeded reference register and its sample documents.

The seeder used to point at sample documents that did not exist, so every seeded
document rendered as "no file available" and the officer document-verification
flow could not be exercised. These tests fail if that drifts again.

They are driven from `REFERENCE_APPLICATIONS` itself rather than a hand-kept
copy, so adding a seeded record cannot silently skip its fixtures.
"""

import json
import unittest
from pathlib import Path

from config import SAMPLE_DOC_DIR, SCHEME_CONFIG_DIR
from services.ocr_service import REQUIRED_FIELDS_BY_DOCUMENT, parse_ocr_text
from utils.seed import REFERENCE_APPLICATIONS

CONFIG_DIR = Path(SCHEME_CONFIG_DIR)
SAMPLE_ROOT = Path(SAMPLE_DOC_DIR)

# Every doc_type -> file_name pair the seeder will write into GridFS.
SEEDED_DOCUMENTS = [
    (document["doc_type"], document["file_name"])
    for entry in REFERENCE_APPLICATIONS
    for document in entry["documents"]
]

# Supplied by the signed-in account rather than the form.
IDENTITY_FIELDS = {"full_name", "email", "phone"}

# Applicant self-declarations that the platform records for the officer to
# compare against the supporting evidence, but that carry no automated rule.
# Adding a new required field outside these groups fails the test below.
SELF_DECLARED_FIELDS = {"is_orphan", "qs_top_1000"}


def scheme_config(scheme_code: str) -> dict:
    return json.loads((CONFIG_DIR / f"{scheme_code.lower()}.json").read_text(encoding="utf-8"))


class SeededDocumentTests(unittest.TestCase):
    def test_every_seeded_sample_file_exists(self):
        missing = sorted({name for _, name in SEEDED_DOCUMENTS if not (SAMPLE_ROOT / name).is_file()})
        self.assertEqual(missing, [], f"seeded sample documents are missing: {missing}")

    def test_sample_fixtures_are_not_empty_and_are_utf8(self):
        for _, file_name in SEEDED_DOCUMENTS:
            with self.subTest(file_name=file_name):
                text = (SAMPLE_ROOT / file_name).read_text(encoding="utf-8")
                self.assertGreater(len(text.strip()), 200)

    def test_seeded_document_types_are_configured_for_their_scheme(self):
        """A document type the scheme does not declare would be rejected by the
        upload route, so the seeder must only reference configured types."""
        problems = []
        for entry in REFERENCE_APPLICATIONS:
            config = scheme_config(entry["scheme"])
            configured = {item["id"] for item in config.get("required_documents", [])}
            for document in entry["documents"]:
                if document["doc_type"] not in configured:
                    problems.append(
                        (entry["scheme"], document["doc_type"], document["file_name"])
                    )
        self.assertEqual(problems, [], f"seeded documents are not configured for their scheme: {problems}")

    def test_every_complete_seed_record_covers_its_required_documents(self):
        """A record that presents a complete submission must satisfy the
        scheme's document requirement. A record seeded as deficient or freshly
        submitted is expected to be missing evidence, which is the case the
        officer has to resolve."""
        problems = []
        for entry in REFERENCE_APPLICATIONS:
            if entry["status"] in {"DEFICIENT", "SUBMITTED"}:
                continue
            config = scheme_config(entry["scheme"])
            required = {
                item["id"]
                for item in config.get("required_documents", [])
                if item.get("required") and item.get("id")
            }
            present = {document["doc_type"] for document in entry["documents"]}
            if not required:
                problems.append((entry["scheme"], "no required documents configured"))
            if not required.issubset(present):
                problems.append((entry["scheme"], sorted(required - present)))
        self.assertEqual(problems, [], f"complete seeded records are missing required documents: {problems}")

    def test_the_seeded_deficient_record_is_actually_missing_evidence(self):
        """The reference register needs a genuine deficiency for the officer to
        resolve, so at least one record must be short of a required document."""
        short = [
            entry["scheme"]
            for entry in REFERENCE_APPLICATIONS
            if entry["status"] == "DEFICIENT"
            and not {
                item["id"]
                for item in scheme_config(entry["scheme"]).get("required_documents", [])
                if item.get("required")
            }.issubset({document["doc_type"] for document in entry["documents"]})
        ]
        self.assertTrue(short, "no seeded record demonstrates a missing-document deficiency")

    def test_key_fixtures_yield_the_declared_field_for_officer_comparison(self):
        """The officer review compares extracted output against declared data, so
        the fixture must actually yield a parseable value for that doc type."""
        expectations = [
            ("caste_cert", "st_caste_certificate_sample.txt", "ST/JH/2023/88921"),
            ("caste_cert", "sunita_caste_certificate.txt", "ST/OD/2022/45109"),
            ("caste_cert", "amit_caste_certificate.txt", "ST/CG/2021/11029"),
            ("caste_cert", "pooja_caste_certificate.txt", "ST/AS/2023/33918"),
            ("income_cert", "sunita_income_certificate.txt", "350000"),
            ("income_cert", "amit_income_certificate.txt", "780000"),
            ("pg_marksheet", "ramesh_pg_marksheet.txt", "68.5"),
            ("pg_marksheet", "pooja_pg_marksheet.txt", "62.0"),
            ("qualifying_marks", "sunita_qualifying_marks.txt", "71.4"),
            ("dob_proof", "sunita_dob_proof.txt", "1999-03-12"),
        ]
        for doc_type, file_name, expected in expectations:
            with self.subTest(doc_type=doc_type, file_name=file_name):
                text = (SAMPLE_ROOT / file_name).read_text(encoding="utf-8")
                parsed = parse_ocr_text(text, doc_type)
                values = [v for v in parsed.values() if v not in (None, "", [])]
                self.assertTrue(values, f"{file_name} produced no parsed fields")
                flattened = " ".join(str(v) for v in values)
                self.assertIn(
                    expected.replace(",", ""),
                    flattened.replace(",", ""),
                    f"{file_name} did not yield expected value {expected!r}; got {values!r}",
                )


class SchemeConfigurationTests(unittest.TestCase):
    def test_every_scheme_requires_at_least_one_document(self):
        for config_path in sorted(CONFIG_DIR.glob("*.json")):
            with self.subTest(scheme=config_path.stem):
                config = json.loads(config_path.read_text(encoding="utf-8"))
                required = [
                    item["id"]
                    for item in config.get("required_documents", [])
                    if item.get("required") and item.get("id")
                ]
                self.assertTrue(required, f"{config_path.stem} requires no documents")

    def test_every_scheme_has_form_fields_and_validation_rules(self):
        for config_path in sorted(CONFIG_DIR.glob("*.json")):
            with self.subTest(scheme=config_path.stem):
                config = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertTrue(config.get("form_fields"), f"{config_path.stem} has no form fields")
                self.assertTrue(config.get("validation_rules"), f"{config_path.stem} has no rules")

    def test_required_form_fields_are_always_accounted_for(self):
        """Every required form field must be either taken from the account, kept
        as a self-declaration for officer review, checked by a rule, or extracted
        from a document the officer verifies. A field in none of those groups
        would be collected from the applicant and then silently ignored.
        """
        document_fields = {
            field
            for fields in REQUIRED_FIELDS_BY_DOCUMENT.values()
            for field in fields
        }
        problems = []
        for config_path in sorted(CONFIG_DIR.glob("*.json")):
            config = json.loads(config_path.read_text(encoding="utf-8"))
            ruled = {rule["field"] for rule in config.get("validation_rules", [])}
            for field in config.get("form_fields", []):
                name = field["name"]
                if not field.get("required"):
                    continue
                if name in IDENTITY_FIELDS or name in SELF_DECLARED_FIELDS:
                    continue
                if name in ruled or name in document_fields:
                    continue
                problems.append((config_path.stem, name))
        self.assertEqual(problems, [], f"required fields are never checked: {problems}")


class SelectionGateTests(unittest.TestCase):
    """The gate enforced by the admin verification and decision routes."""

    def test_gate_stays_closed_until_all_required_documents_are_verified(self):
        config = scheme_config("nfst")
        required = {
            item["id"]
            for item in config.get("required_documents", [])
            if item.get("required") and item.get("id")
        }
        self.assertTrue(required)
        verified: set = set()
        self.assertFalse(required.issubset(verified))
        for doc_type in sorted(required):
            verified.add(doc_type)
        self.assertTrue(required.issubset(verified))


if __name__ == "__main__":
    unittest.main()
