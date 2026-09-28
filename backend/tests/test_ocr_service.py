import json
import unittest
from pathlib import Path

from services.ocr_service import (
    REQUIRED_FIELDS_BY_DOCUMENT,
    SUPPORTED_DOCUMENT_TYPES,
    parse_ocr_text,
    process_document_ocr,
)


def build_minimal_pdf() -> bytes:
    """Return a one-page PDF whose text layer is a caste certificate line."""
    text = "CASTE CERTIFICATE FOR SCHEDULED TRIBE (ST) Certificate No: ST/JH/2023/88921"
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    stream = f"BT /F1 12 Tf 40 780 Td ({escaped}) Tj ET".encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


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
        # Uploads arrive as bytes held in GridFS, so the extractor takes content
        # rather than a filesystem path.
        result = process_document_ocr(sample.read_bytes(), "caste_cert", "NFST", sample.name)
        self.assertEqual(result["ocr_status"], "SUCCESS")
        self.assertEqual(result["parsed_fields"]["caste_certificate_no"], "ST/JH/2023/88921")
        self.assertIn("CASTE CERTIFICATE", result["extracted_text"])
        self.assertEqual(result["extraction_method"], "Plain text extraction")
        self.assertIsNone(result["ocr_confidence"])

    def test_unrecognized_required_fields_are_partial_for_officer_review(self):
        result = process_document_ocr(
            b"A scanned-looking page with no income amount.", "income_cert", "NFST", "income.txt"
        )
        self.assertEqual(result["ocr_status"], "PARTIAL")
        self.assertEqual(result["parsed_fields"], {})
        self.assertTrue(result["failed_reason"])

    def test_pdf_bytes_are_read_through_pymupdf(self):
        pdf = build_minimal_pdf()
        result = process_document_ocr(pdf, "caste_cert", "NFST", "certificate.pdf")
        self.assertEqual(result["ocr_status"], "SUCCESS")
        self.assertIn("ST/JH/2023/88921", result["extracted_text"])

    def test_corrupt_bytes_fail_without_raising(self):
        result = process_document_ocr(b"not a real pdf", "caste_cert", "NFST", "broken.pdf")
        self.assertEqual(result["ocr_status"], "FAILED")
        self.assertTrue(result["failed_reason"])


if __name__ == "__main__":
    unittest.main()
