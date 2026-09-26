import json
import tempfile
import unittest
from pathlib import Path

from services.ocr_service import (
    REQUIRED_FIELDS_BY_DOCUMENT,
    SUPPORTED_DOCUMENT_TYPES,
    parse_ocr_text,
    process_document_ocr,
)


class OCRServiceTests(unittest.TestCase):
    def test_every_required_scheme_document_has_an_ocr_profile(self):
        config_dir = Path(__file__).resolve().parents[1] / "data" / "scheme_configs"
        required_types = set()
        for config_path in config_dir.glob("*.json"):
            config = json.loads(config_path.read_text(encoding="utf-8"))
            required_types.update(
                item["id"] for item in config.get("required_documents", [])
                if item.get("required")
            )
        self.assertEqual(required_types - SUPPORTED_DOCUMENT_TYPES, set())

    def test_supported_document_profiles_parse_their_expected_fields(self):
        samples = {
            "caste_cert": ("CASTE CERTIFICATE FOR SCHEDULED TRIBE (ST)\nCertificate No: ST/JH/2023/88921", "caste_certificate_no"),
            "income_cert": ("Total Annual Income: INR 2,80,000", "annual_family_income"),
            "pg_marksheet": ("Aggregate percentage: 68.5%", "pg_percentage"),
            "qualifying_degree": ("Qualifying Degree\nMarks: 71%", "qualifying_percentage"),
            "qualifying_marks": ("Qualifying Degree\nMarks: 71%", "qualifying_percentage"),
            "marksheets": ("Academic Marksheet\nAggregate percentage: 72%", "marks_percentage"),
            "foreign_offer_letter": ("UNCONDITIONAL OFFER\nThe University of Edinburgh\nCourse: MSc", "has_unconditional_offer"),
            "admission_letter": ("Admission to Ph.D program\nJawaharlal Nehru University\nProgramme of Study: Doctor of Philosophy", "course_enrolled"),
            "admission_proof": ("UNCONDITIONAL OFFER\nUniversity of Edinburgh\nProgramme of Study: MSc", "has_unconditional_offer"),
            "dob_proof": ("Date of Birth: 15/08/2004", "date_of_birth"),
            "one_child_declaration": ("I hereby declare I am the only child in my family.", "one_child_self_certified"),
            "domicile_cert": ("Domicile certificate\nState: Jharkhand", "domicile_state"),
            "school_enrolment": ("School Name: Government High School\nClass: IX\nRecognized school: Yes", "class_studying"),
            "institution_proof": ("Central/State Government funded University\nUniversity of Example", "university_name"),
            "institution_course_proof": ("University of Example\nCourse: B.Sc", "course_name"),
            "pvtg_proof": ("PVTG: Yes", "is_pvtg"),
            "disability_cert": ("Disability: 45%", "disability_percentage"),
            "passport": ("Passport Number: Z6543219", "passport_number"),
            "bank_aadhaar": ("Bank account details; IFSC and DBT account linkage", "bank_account_evidence_present"),
            "id_proof": ("Applicant Name: Ramesh Chandra Munda", "full_name"),
        }
        self.assertEqual(set(samples), set(REQUIRED_FIELDS_BY_DOCUMENT))
        for doc_type, (text, expected_field) in samples.items():
            with self.subTest(doc_type=doc_type):
                fields = parse_ocr_text(text, doc_type)
                self.assertIn(expected_field, fields)

    def test_sample_certificate_text_is_extracted_and_parsed(self):
        sample = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "sample-documents"
            / "st_caste_certificate_sample.txt"
        )
        result = process_document_ocr(str(sample), "caste_cert", "NFST")
        self.assertEqual(result["ocr_status"], "SUCCESS")
        self.assertEqual(result["parsed_fields"]["caste_certificate_no"], "ST/JH/2023/88921")
        self.assertIn("CASTE CERTIFICATE", result["extracted_text"])
        self.assertEqual(result["extraction_method"], "Plain text extraction")
        self.assertIsNone(result["ocr_confidence"])

    def test_unrecognized_required_fields_are_partial_for_officer_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            document = Path(temp_dir) / "income.txt"
            document.write_text("A scanned-looking page with no income amount.", encoding="utf-8")
            result = process_document_ocr(str(document), "income_cert")
        self.assertEqual(result["ocr_status"], "PARTIAL")
        self.assertEqual(result["parsed_fields"], {})
        self.assertTrue(result["failed_reason"])


if __name__ == "__main__":
    unittest.main()
