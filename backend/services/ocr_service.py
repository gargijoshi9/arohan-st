import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pymupdf
import pytesseract
from PIL import Image
from pytesseract import Output

SUPPORTED_DOCUMENT_TYPES = {
    "caste_cert",
    "income_cert",
    "pg_marksheet",
    "qualifying_degree",
    "qualifying_marks",
    "marksheets",
    "foreign_offer_letter",
    "admission_letter",
    "admission_proof",
    "dob_proof",
    "one_child_declaration",
    "domicile_cert",
    "school_enrolment",
    "institution_proof",
    "institution_course_proof",
    "pvtg_proof",
    "disability_cert",
    "passport",
    "bank_aadhaar",
    "id_proof",
}

REQUIRED_FIELDS_BY_DOCUMENT = {
    "caste_cert": {"caste_certificate_no"},
    "income_cert": {"annual_family_income"},
    "pg_marksheet": {"pg_percentage"},
    "qualifying_degree": {"qualifying_percentage"},
    "qualifying_marks": {"qualifying_percentage"},
    "marksheets": {"marks_percentage"},
    "foreign_offer_letter": {"has_unconditional_offer", "foreign_university", "course_level", "course_name"},
    "admission_letter": {"university_name", "course_enrolled", "course_name"},
    "admission_proof": {"has_unconditional_offer", "foreign_university", "course_level", "course_name"},
    "dob_proof": {"date_of_birth"},
    "one_child_declaration": {"one_child_self_certified"},
    "domicile_cert": {"domicile_state"},
    "school_enrolment": {"class_studying", "school_name", "eligible_school"},
    "institution_proof": {"institution_category", "university_name"},
    "institution_course_proof": {"course_name", "university_name"},
    "pvtg_proof": {"is_pvtg"},
    "disability_cert": {"disability_percentage"},
    "passport": {"passport_number"},
    "bank_aadhaar": {"bank_account_evidence_present"},
    "id_proof": {"full_name"},
}


def _normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in (text or "").splitlines() if line.strip())


def _tesseract_text_and_confidence(image: Image.Image) -> Tuple[str, Optional[float]]:
    language = os.environ.get("TESSERACT_LANG", "eng")
    configured_cmd = os.environ.get("TESSERACT_CMD")
    if configured_cmd:
        pytesseract.pytesseract.tesseract_cmd = configured_cmd
    elif not shutil.which("tesseract"):
        for candidate in (
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe",
        ):
            if candidate.is_file():
                pytesseract.pytesseract.tesseract_cmd = str(candidate)
                break

    data = pytesseract.image_to_data(image, lang=language, output_type=Output.DICT)
    confidences = []
    for word, confidence in zip(data["text"], data["conf"]):
        word = word.strip()
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            continue
        if word and confidence_value >= 0:
            confidences.append(confidence_value)

    text = pytesseract.image_to_string(image, lang=language)
    average_confidence = sum(confidences) / len(confidences) / 100 if confidences else None
    return text, average_confidence


def _extract_text_from_file(file_path: str) -> Tuple[str, str, Optional[float]]:
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".pdf":
        page_texts = []
        used_ocr = False
        confidences = []
        with pymupdf.open(file_path) as document:
            if document.page_count > 15:
                raise ValueError("PDFs may contain no more than 15 pages.")
            for page in document:
                page_text = page.get_text().strip()
                if len(page_text) >= 20:
                    page_texts.append(page_text)
                    continue

                pixmap = page.get_pixmap(dpi=250, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                page_text, confidence = _tesseract_text_and_confidence(image)
                page_texts.append(page_text)
                used_ocr = True
                if confidence is not None:
                    confidences.append(confidence)

        method = "Tesseract OCR" if used_ocr else "PDF text extraction"
        confidence = sum(confidences) / len(confidences) if confidences else None
        return "\n".join(page_texts), method, confidence

    if extension in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        with Image.open(file_path) as image:
            text, confidence = _tesseract_text_and_confidence(image.convert("RGB"))
        return text, "Tesseract OCR", confidence

    if extension == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="strict") as stream:
            return stream.read(), "Plain text extraction", None

    raise ValueError("Unsupported document format.")


def _extract_money_value(text: str) -> Optional[float]:
    patterns = [
        r"(?:total\s+annual\s+income|gross\s+annual\s+income|annual\s+income)[^\d₹]{0,20}(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.\d+)?)",
        r"(?:rs\.?|inr|₹)\s*([0-9,]+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _extract_percentage(text: str) -> Optional[float]:
    patterns = [
        r"(?:percentage|aggregate|marks|score)[^\d%]{0,24}(\d{1,3}(?:\.\d+)?)\s*%",
        r"(\d{1,3}(?:\.\d+)?)\s*%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                if 0 <= value <= 100:
                    return value
            except ValueError:
                continue
    return None


def _extract_certificate_number(text: str) -> Optional[str]:
    patterns = [
        r"(?:caste\s+)?certificate\s*(?:no\.?|number|ref(?:erence)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/\-]{3,})",
        r"\bST/[A-Z]{2,}/\d{4}/\d{4,}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return (match.group(1) if match.lastindex else match.group(0)).strip()
    return None


def _extract_passport_number(text: str) -> Optional[str]:
    match = re.search(
        r"(?:passport(?:\s*(?:no\.?|number))?)\s*[:#-]?\s*([A-Z][0-9]{7})\b",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1).upper() if match else None


def _extract_candidate_name(text: str) -> Optional[str]:
    match = re.search(
        r"(?:candidate|applicant|student|scholar)\s+name\s*[:\-]\s*([A-Z][A-Z .'-]{2,})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return " ".join(match.group(1).split()).title()
    return None


def _extract_date_of_birth(text: str) -> Optional[str]:
    match = re.search(
        r"(?:date\s+of\s+birth|dob|birth\s+date)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    from datetime import datetime

    raw_date = match.group(1)
    for date_format in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw_date, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _extract_labeled_value(text: str, labels: Tuple[str, ...]) -> Optional[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{label_pattern})\s*[:\-]\s*([^\n\r]{{2,100}})",
        text,
        flags=re.IGNORECASE,
    )
    return " ".join(match.group(1).split()).strip(" .") if match else None


def _extract_labeled_yes_no(text: str, labels: Tuple[str, ...]) -> Optional[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{label_pattern})\s*[:\-]\s*(yes|no|true|false)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return "Yes" if match.group(1).casefold() in {"yes", "true"} else "No"


def _extract_domicile_state(text: str) -> Optional[str]:
    states = (
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
        "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
        "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
        "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
        "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
    )
    for state in states:
        if re.search(rf"\b{re.escape(state)}\b", text, flags=re.IGNORECASE):
            return state
    return None


def _detect_unconditional_offer(text: str) -> Optional[str]:
    lowered = text.lower()
    if re.search(r"\b(unconditional|firm)\s+(?:admission\s+)?offer\b", lowered):
        return "Yes"
    if re.search(r"\b(conditional|provisional)\s+(?:admission\s+)?offer\b", lowered):
        return "No"
    return None


def _extract_institution_name(text: str) -> Optional[str]:
    patterns = (
        r"\b(?:The[ \t]+)?University[ \t]+of[ \t]+[A-Z][A-Za-z&.,' -]+",
        r"\b[A-Z][A-Za-z&.,'-]*(?:[ \t]+[A-Z][A-Za-z&.,'-]*){0,5}[ \t]+(?:University|Institute|College)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return None


def _extract_course_level(text: str, scheme_code: str) -> Optional[str]:
    lowered = text.lower()
    if scheme_code == "TOP_CLASS":
        if any(term in lowered for term in ("postgraduate", "post-graduate", "master", "m.sc", "msc", "m.a.", "mba")):
            return "Post-Graduate"
        if any(term in lowered for term in ("undergraduate", "bachelor", "b.sc", "bsc", "b.tech", "btech")):
            return "Graduate"
        return None
    if "post-doctoral" in lowered or "postdoctoral" in lowered:
        return "Post-Doctoral Research"
    if "m.phil" in lowered or "mphil" in lowered:
        if "ph.d" in lowered or "phd" in lowered or "doctor of philosophy" in lowered:
            return "M.Phil + Ph.D" if scheme_code == "NFST" else "Ph.D"
        return "M.Phil"
    if "ph.d" in lowered or "phd" in lowered or "doctor of philosophy" in lowered:
        return "Ph.D"
    if any(term in lowered for term in ("master", "msc", "m.sc", "m.a.", "mba")):
        return "Master’s" if scheme_code == "NOS" else "Master's Degree"
    return None


def _extract_disability_percentage(text: str) -> Optional[float]:
    match = re.search(
        r"(?:disability|benchmark disability|percentage of disability)[^\d%]{0,30}(\d{1,3}(?:\.\d+)?)\s*%",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    value = float(match.group(1))
    return value if 0 <= value <= 100 else None


def _calculate_age_on_july_first(date_of_birth: str, year: int) -> int:
    from datetime import date

    birth_date = date.fromisoformat(date_of_birth)
    reference_date = date(year, 7, 1)
    return reference_date.year - birth_date.year - (
        (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day)
    )


def parse_ocr_text(text: str, doc_type: str) -> Dict[str, Any]:
    normalized = _normalize_text(text)
    parsed: Dict[str, Any] = {}
    lowered = normalized.lower()
    candidate_name = _extract_candidate_name(normalized)
    if candidate_name:
        parsed["full_name"] = candidate_name

    if doc_type == "caste_cert":
        if "scheduled tribe" in lowered or re.search(r"\bST\b", normalized):
            parsed["category"] = "ST"
        certificate_number = _extract_certificate_number(normalized)
        if certificate_number:
            parsed["caste_certificate_no"] = certificate_number
    elif doc_type == "income_cert":
        income = _extract_money_value(normalized)
        if income is not None:
            parsed["annual_family_income"] = income
    elif doc_type in {"pg_marksheet", "qualifying_degree", "qualifying_marks", "marksheets"}:
        percentage = _extract_percentage(normalized)
        if percentage is not None:
            if doc_type == "pg_marksheet":
                parsed["pg_percentage"] = percentage
            elif doc_type in {"qualifying_degree", "qualifying_marks"}:
                parsed["qualifying_percentage"] = percentage
            else:
                parsed["marks_percentage"] = percentage
        degree = _extract_labeled_value(normalized, ("degree", "qualification", "course"))
        if degree:
            parsed["qualifying_degree"] = degree
    elif doc_type in {"foreign_offer_letter", "admission_letter", "admission_proof"}:
        offer_status = _detect_unconditional_offer(normalized)
        if offer_status:
            parsed["has_unconditional_offer"] = offer_status
        institution = _extract_institution_name(normalized)
        if institution:
            institution_field = "university_name" if doc_type == "admission_letter" else "foreign_university"
            parsed[institution_field] = institution
        course = _extract_labeled_value(normalized, ("programme of study", "program of study", "course", "programme", "program"))
        if course:
            parsed["course_enrolled" if doc_type == "admission_letter" else "course_name"] = course
        for field, labels in {
            "admitted_on_merit": ("admitted on merit", "merit admission"),
            "management_quota": ("management quota",),
            "notified_institution": ("notified institution", "institution on mota list"),
            "eligible_institution": ("eligible institution", "recognized institution", "recognised institution"),
            "recognized_course": ("recognized course", "recognised course"),
        }.items():
            answer = _extract_labeled_yes_no(normalized, labels)
            if answer:
                parsed[field] = answer
    elif doc_type == "dob_proof":
        date_of_birth = _extract_date_of_birth(normalized)
        if date_of_birth:
            parsed["date_of_birth"] = date_of_birth
    elif doc_type in {"one_child_declaration"}:
        if re.search(r"\b(only child|sole child|one child per family|single child)\b", lowered):
            parsed["one_child_self_certified"] = "Yes"
    elif doc_type == "domicile_cert":
        state = _extract_domicile_state(normalized)
        if state:
            parsed["domicile_state"] = state
    elif doc_type == "school_enrolment":
        class_studying = _extract_labeled_value(normalized, ("class", "grade", "standard"))
        if class_studying:
            class_match = re.search(r"\b(IX|X|[1-9]|1[0-2])\b", class_studying, flags=re.IGNORECASE)
            parsed["class_studying"] = class_match.group(1).upper() if class_match else class_studying
        school = _extract_labeled_value(normalized, ("school name", "name of school", "institution"))
        if school:
            parsed["school_name"] = school
        school_text = lowered
        if "government school" in school_text or "government recognized" in school_text or "government-recognized" in school_text:
            parsed["eligible_school"] = "Yes"
        school_answer = _extract_labeled_yes_no(normalized, ("eligible school", "government-recognized school", "recognized school", "recognised school"))
        if school_answer:
            parsed["eligible_school"] = school_answer
    elif doc_type in {"institution_proof", "institution_course_proof"}:
        institution = _extract_institution_name(normalized)
        if institution:
            parsed["university_name"] = institution
        course = _extract_labeled_value(normalized, ("course", "programme", "program"))
        if course:
            parsed["course_name"] = course
        institution_answers = {
            "notified_institution": ("notified institution", "institution on mota list"),
            "eligible_institution": ("eligible institution", "recognized institution", "recognised institution"),
            "recognized_course": ("recognized course", "recognised course"),
        }
        for field, labels in institution_answers.items():
            answer = _extract_labeled_yes_no(normalized, labels)
            if answer:
                parsed[field] = answer
    elif doc_type == "pvtg_proof":
        pvtg_answer = _extract_labeled_yes_no(normalized, ("PVTG", "particularly vulnerable tribal group"))
        if pvtg_answer:
            parsed["is_pvtg"] = pvtg_answer
        elif re.search(r"\b(particularly vulnerable tribal group|PVTG)\b", normalized, flags=re.IGNORECASE):
            parsed["is_pvtg"] = "Yes"
    elif doc_type == "disability_cert":
        disability_percentage = _extract_disability_percentage(normalized)
        if disability_percentage is not None:
            parsed["disability_percentage"] = disability_percentage
            parsed["is_divyangjan"] = "Yes" if disability_percentage >= 40 else "No"
    elif doc_type == "bank_aadhaar":
        if re.search(r"\b(bank|account|DBT|Aadhaar|IFSC)\b", normalized, flags=re.IGNORECASE):
            parsed["bank_account_evidence_present"] = "Yes"
    elif doc_type == "passport":
        passport_number = _extract_passport_number(normalized)
        if passport_number:
            parsed["passport_number"] = passport_number

    return parsed


def process_document_ocr(file_path: str, doc_type: str, scheme_code: Optional[str] = None) -> Dict[str, Any]:
    try:
        extracted_text, method, confidence = _extract_text_from_file(file_path)
    except (OSError, ValueError, RuntimeError, pymupdf.FileDataError) as exc:
        return {
            "extracted_text": "",
            "parsed_fields": {},
            "ocr_status": "FAILED",
            "ocr_confidence": None,
            "extraction_method": "Tesseract OCR",
            "failed_reason": str(exc),
        }

    cleaned_text = _normalize_text(extracted_text)
    parsed_fields = parse_ocr_text(cleaned_text, doc_type)
    if doc_type not in SUPPORTED_DOCUMENT_TYPES:
        return {
            "extracted_text": cleaned_text,
            "parsed_fields": parsed_fields,
            "ocr_status": "PARTIAL",
            "ocr_confidence": round(confidence, 3) if confidence is not None else None,
            "extraction_method": method,
            "failed_reason": "Text was extracted, but this document type does not have a configured field parser; officer review is required.",
        }
    if doc_type == "dob_proof" and parsed_fields.get("date_of_birth"):
        from datetime import datetime

        selected_year = datetime.now().year
        scheme_config_path = Path(__file__).resolve().parent.parent / "data" / "scheme_configs" / f"{(scheme_code or '').lower()}.json"
        if scheme_config_path.is_file():
            scheme_config = json.loads(scheme_config_path.read_text(encoding="utf-8"))
            selected_year = int(scheme_config.get("selection_year", selected_year))
        parsed_fields["applicant_age"] = _calculate_age_on_july_first(parsed_fields["date_of_birth"], selected_year)
    if doc_type in {"admission_proof", "foreign_offer_letter", "admission_letter", "institution_course_proof"}:
        normalized_scheme_code = (scheme_code or "").upper()
        course_level = _extract_course_level(cleaned_text, normalized_scheme_code)
        if course_level:
            if normalized_scheme_code == "NFST":
                parsed_fields["course_enrolled"] = course_level
            elif normalized_scheme_code in {"NOS", "TOP_CLASS"}:
                parsed_fields["course_level"] = course_level
    if doc_type == "institution_proof":
        lowered_text = cleaned_text.casefold()
        scheme_config_path = Path(__file__).resolve().parent.parent / "data" / "scheme_configs" / f"{(scheme_code or '').lower()}.json"
        if scheme_config_path.is_file():
            scheme_config = json.loads(scheme_config_path.read_text(encoding="utf-8"))
            institution_rule = next(
                (rule for rule in scheme_config.get("validation_rules", []) if rule.get("field") == "institution_category"),
                None,
            )
            if institution_rule:
                candidates = institution_rule.get("values", [])
                for candidate in candidates:
                    terms = [term.casefold() for term in re.split(r"[/+() ]+", candidate) if len(term) > 2]
                    if terms and any(term in lowered_text for term in terms):
                        parsed_fields["institution_category"] = candidate
                        break
    if not cleaned_text:
        status = "FAILED"
        failed_reason = "No readable text was found. Upload a clearer scan or PDF."
    elif not REQUIRED_FIELDS_BY_DOCUMENT.get(doc_type, set()).intersection(parsed_fields):
        status = "PARTIAL"
        failed_reason = "Text was extracted, but expected information for this document type was not detected."
    else:
        status = "SUCCESS"
        failed_reason = None

    return {
        "extracted_text": cleaned_text,
        "parsed_fields": parsed_fields,
        "ocr_status": status,
        "ocr_confidence": round(confidence, 3) if confidence is not None else None,
        "extraction_method": method,
        "failed_reason": failed_reason,
    }
