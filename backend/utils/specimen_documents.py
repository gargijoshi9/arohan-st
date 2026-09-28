"""Generate specimen certificate PDFs for the recording presentation.

The AROHAN-ST platform does NOT verify the authenticity of uploaded evidence -
document verification is a human officer decision, and the rule engine only
checks the applicant's *declarations*. A real, government-issued caste
certificate is therefore never required for a recording.

What these files provide instead is professional-looking, clearly-marked
SPECIMEN documents for every document type a scheme can require. Each one is
repeatedly watermarked so nobody could mistake it for a real government record.

Output goes ONLY into ``docs/sample-documents/`` - the same folder the seeder
reads.

Run from ``backend/``:

    python -m utils.specimen_documents
"""

import json
import math
from pathlib import Path

import pymupdf

CONFIG_DIR = Path(__file__).resolve().parent.parent / "data" / "scheme_configs"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "sample-documents"

PAGE_W, PAGE_H = 595, 842  # A4 at 72 dpi
MARGIN = 72
FRAME = pymupdf.Rect(MARGIN, MARGIN, PAGE_W - MARGIN, PAGE_H - MARGIN)

# Human-readable title and the fields that make each specimen realistic.
SPECIMEN_BLUEPRINT = {
    "caste_cert": {
        "title": "Scheduled Tribe (ST) Certificate",
        "issued_by": "Issued by: District Collector / Sub-Divisional Officer",
        "lines": [
            "Certificate No: ST/ST/2026/00000",
            "Name: [Candidate Name]",
            "Father's / Mother's Name: [Parent Name]",
            "Date of Birth: [DD-MM-YYYY]",
            "Community: Scheduled Tribe (ST)",
            "Sub-caste: [Tribe Name]",
            "Permanent Address: [Village], [Block], [District], [State] - [PIN]",
            "Basis of verification: Revenue records and villagers' verification.",
            "This certificate is issued after due verification of the applicant.",
        ],
    },
    "income_cert": {
        "title": "Income Certificate",
        "issued_by": "Issued by: Tehsildar / Sub-Divisional Officer",
        "lines": [
            "Certificate No: IC/2026/00000",
            "Name of holder: [Candidate Name]",
            "Address: [Village], [District], [State] - [PIN]",
            "Gross annual income of the family: Rs. [0 - specify below]",
            "Source of income: Agriculture / Daily wages",
            "The income details above are certified on the basis of the records.",
        ],
    },
    "pg_marksheet": {
        "title": "Post-Graduate Degree Marks Statement",
        "issued_by": "Issued by: [University Examination Cell]",
        "lines": [
            "Student Name: [Candidate Name]",
            "Degree: Master of [Subject]",
            "Roll No: [XXXXXX]",
            "Total Marks: 700",
            "Marks Obtained: 455",
            "Percentage: 65.0%",
            "CGPA: 8.1 / 10",
            "Result: PASS",
        ],
    },
    "qualifying_marks": {
        "title": "Qualifying Degree Marks Statement",
        "issued_by": "Issued by: [University Examination Cell]",
        "lines": [
            "Student Name: [Candidate Name]",
            "Qualifying Degree: Bachelor of [Subject]",
            "Roll No: [XXXXXX]",
            "Marks Obtained: [xxxx] / [total]",
            "Percentage: [xx.x]%",
            "Result: PASS",
        ],
    },
    "marksheets": {
        "title": "Consolidated Marks Statement",
        "issued_by": "Issued by: [Examination Board / University]",
        "lines": [
            "Candidate Name: [Candidate Name]",
            "Examination: [Class / Degree - specify]",
            "Roll No: [XXXXXX]",
            "Overall Percentage: [xx.x]%",
            "Division: FIRST",
            "Result: PASS",
        ],
    },
    "dob_proof": {
        "title": "Date of Birth Proof / 10th Marksheet",
        "issued_by": "Issued by: [Board of Secondary Education]",
        "lines": [
            "Candidate Name: [Candidate Name]",
            "Father's / Mother's Name: [Parent Name]",
            "Date of Birth: 1999-03-12",
            "Roll No: [XXXXXX]",
            "School: [School Name]",
            "Place of Examination: [Centre], [State]",
        ],
    },
    "one_child_declaration": {
        "title": "One-Child Self-Declaration",
        "issued_by": "Candidate's sworn declaration",
        "lines": [
            "I, [Candidate Name], son / daughter of [Parent Name],",
            "resident of [Village], [District], [State], hereby declare that",
            "I am the ONLY child of my parents.",
            "I understand that false or suppressed information may lead to",
            "cancellation of the scholarship and recovery of amounts paid.",
            "Place: [City]",
            "Signature: [Candidate Signature]",
        ],
    },
    "admission_proof": {
        "title": "Foreign University Admission / Offer Letter",
        "issued_by": "Issued by: Admissions Office, [University Name]",
        "lines": [
            "Applicant Name: [Candidate Name]",
            "Admitted To: [Course Name and Level]",
            "Mode of Study: Full-time",
            "Course Commencement: [Month Year]",
            "Status: Conditional / Unconditional Offer",
            "University Reference: [OFFER-XXXX]",
        ],
    },
    "admission_letter": {
        "title": "Admission / Enrolment Letter",
        "issued_by": "Issued by: [Institution Registrar / Admissions Office]",
        "lines": [
            "Candidate Name: [Candidate Name]",
            "Admitted To: Doctor of Philosophy in [Subject]",
            "Programme Type: Full-time / Regular",
            "Enrolment No: [ENR-XXXX]",
            "Session: [Year]",
            "Date of Joining: [DD-MM-YYYY]",
        ],
    },
    "institution_proof": {
        "title": "Institution Recognition / Category Proof",
        "issued_by": "Issued by: [Institution Administrative Office]",
        "lines": [
            "This is to certify that [Institution Name] is a recognised",
            "higher-education institution covered under the Ministry's",
            "notification list for the scheme applied for.",
            "Institution Category: CENTRAL / STATE / DEEMED UNIVERSITY",
            "UGC / AICTE Approval No: [XXXXXX]",
        ],
    },
    "institution_course_proof": {
        "title": "Institution and Course Proof",
        "issued_by": "Issued by: [Institution]",
        "lines": [
            "Candidate Name: [Candidate Name]",
            "Course: [Course Name]",
            "Institution: [Institution Name]",
            "This confirms that [Institution Name] is notified under the",
            "eligible institute list and the course is FULL-TIME/REGULAR.",
        ],
    },
    "domicile_cert": {
        "title": "Domicile / Residence Certificate",
        "issued_by": "Issued by: Tehsildar / Sub-Divisional Officer",
        "lines": [
            "Certificate No: DC/2026/00000",
            "Name: [Candidate Name]",
            "Father's / Mother's Name: [Parent Name]",
            "Place of residence since [Year]",
            "Residence: [Village], [Block], [District], [State] - [PIN]",
            "The above person is certified to be a resident of this State.",
        ],
    },
    "school_enrolment": {
        "title": "School Enrolment and Class Certificate",
        "issued_by": "Issued by: Head Master / Head Mistress, [School Name]",
        "lines": [
            "Student Name: [Candidate Name]",
            "Father's / Mother's Name: [Parent Name]",
            "Class studying in: [Class and Section]",
            "Enrolment No: [XXXX]",
            "Medium of instruction: [Hindi / Local Language]",
            "Attendance: REGULAR",
        ],
    },
    "bank_aadhaar": {
        "title": "Bank Account and Aadhaar Proof",
        "issued_by": "Issued by: [Bank] and UIDAI-linked record",
        "lines": [
            "Account Holder: [Candidate Name]",
            "Bank Account Number: [XXXXXXXXXXXXXXXXXX]",
            "IFSC: [XXXX0000000]",
            "Branch: [Branch Name]",
            "This account is Aadhaar-linked and the holder's name matches",
            "the Aadhaar record as per banking guidelines.",
        ],
    },
    "disability_cert": {
        "title": "Disability Certificate",
        "issued_by": "Issued by: District Medical Board",
        "lines": [
            "Certificate No: [DC-XXXX]",
            "Name: [Candidate Name]",
            "Date of Examination: [DD-MM-YYYY]",
            "Nature of Disability: [As per examination]",
            "Degree of Disability: [XX]%",
            "This assessment is made under the relevant disability rules.",
        ],
    },
}


def _insert_centered(page: pymupdf.Page, text: str, y: float, fontsize: float, fontname: str = "tiro") -> None:
    twidth = pymupdf.get_text_length(text, fontname=fontname, fontsize=fontsize)
    page.insert_text((FRAME.x0 + (FRAME.width - twidth) / 2, y), text, fontsize=fontsize, fontname=fontname)


def _rotated_text(page: pymupdf.Page, at: tuple, text: str, fontsize: float,
                  degrees: float, color: tuple = (0.72, 0.72, 0.72)) -> None:
    rad = math.radians(degrees)
    matrix = pymupdf.Matrix(
        math.cos(rad), math.sin(rad), -math.sin(rad), math.cos(rad), 0, 0
    )
    writer = pymupdf.TextWriter(page.rect)
    writer.append(pymupdf.Point(*at), text, font=pymupdf.Font("hebo"), fontsize=fontsize)
    writer.write_text(page, morph=(pymupdf.Point(*at), matrix))


def _watermark(page: pymupdf.Page, text: str) -> None:
    page.draw_rect(FRAME, color=(0.55, 0.55, 0.55), width=2, overlay=True)
    for i, angle in enumerate([-35, 35, -35]):
        x = FRAME.x0 + 40
        y = FRAME.y0 + 90 + i * 250
        _rotated_text(page, (x, y), text, 56, angle)
    page.insert_textbox(
        pymupdf.Rect(FRAME.x0, PAGE_H - 58, FRAME.x1, PAGE_H - 34),
        "SPECIMEN - TRAINING / RECORDING MATERIAL. NOT A GOVERNMENT-ISSUED DOCUMENT.",
        fontname="hebo", fontsize=9, color=(0.85, 0.2, 0.2),
        align=pymupdf.TEXT_ALIGN_CENTER,
    )


def _build(doc_type: str, blueprint: dict) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    _watermark(page, "SPECIMEN - NOT A REAL DOCUMENT")
    page.insert_text((FRAME.x0, MARGIN + 34), "GOVERNMENT OF INDIA", fontsize=13, fontname="hebo")
    page.insert_text((FRAME.x0, MARGIN + 52), "Ministry of Tribal Affairs", fontsize=10, fontname="hebo")
    _insert_centered(page, blueprint["title"], MARGIN + 110, 20, fontname="hebo")
    page.insert_text((FRAME.x0, MARGIN + 150), "SPECIMEN ONLY - FOR THE RECORDING PRESENTATION", fontsize=9,
                     fontname="hebo", color=(0.85, 0.2, 0.2))
    page.insert_text((FRAME.x0, MARGIN + 185), blueprint["issued_by"], fontsize=10, fontname="tiro")
    y = MARGIN + 230
    for line in blueprint["lines"]:
        page.insert_text((FRAME.x0 + 18, y), line, fontsize=11, fontname="tiro")
        y += 26
    return doc.tobytes()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for doc_type, blueprint in sorted(SPECIMEN_BLUEPRINT.items()):
        filename = f"specimen_{doc_type}.pdf"
        content = _build(doc_type, blueprint)
        (OUTPUT_DIR / filename).write_bytes(content)
        written.append(filename)
    print(f"Wrote {len(written)} specimen PDFs to {OUTPUT_DIR}")
    for name in written:
        print(f"  - {name}")


if __name__ == "__main__":
    main()