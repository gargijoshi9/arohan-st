import os
import re
from typing import Any, Dict, List, Optional

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

try:
    from pdf2image import convert_from_path
except ImportError:  # pragma: no cover
    convert_from_path = None


def _normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in (text or "").splitlines() if line.strip())


def _extract_money_value(text: str) -> Optional[float]:
    lower = text.lower()
    if 'annual income' in lower or 'gross annual income' in lower or 'total annual income' in lower:
        patterns = [
            r'(?:Rs\.?|INR|₹)\s*[:]?\s*([0-9,]+(?:\.\d+)?)',
            r'(?:annual income|total annual income|gross annual income)\s*[:]?\s*(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.\d+)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                cleaned = match.group(1).replace(',', '').replace(' ', '')
                try:
                    return float(cleaned)
                except ValueError:
                    continue
    return None


def _extract_percentage(text: str) -> Optional[float]:
    match = re.search(r'(\d{2,3}(?:\.\d+)?)\s*%', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _extract_certificate_number(text: str) -> Optional[str]:
    patterns = [
        r'(?:Certificate\s*No|Caste\s*Certificate\s*No|Certificate\s*Ref|Cert(?:ificate)?\s*Ref)\s*[:#-]?\s*([A-Z0-9/\-]{4,})',
        r'(?:ST)\s*[/\-]?[A-Z]{2,}\s*[/\-]\s*\d{4}\s*[/\-]\s*\d{4,}',
        r'(?:ST|Scheduled Tribe|Caste)\s*[:#-]?\s*([A-Z0-9/\-]{4,})',
        r'([A-Z]{2,}/[A-Z0-9/\-]{4,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1) if match.lastindex else match.group(0)
            if value and value.lower() not in {'certificate', 'caste', 'st'}:
                return value.strip()
    return None


def _extract_passport_number(text: str) -> Optional[str]:
    match = re.search(r'(?:Passport|Passport\s*No|Passport\s*Number)\s*[:#-]?\s*([A-Z0-9]{6,12})', text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _detect_course(text: str) -> Optional[str]:
    lowered = text.lower()
    if 'integrated ph.d' in lowered or 'integrated phd' in lowered:
        return 'Integrated Ph.D'
    if 'ph.d' in lowered or 'phd' in lowered:
        return 'Ph.D'
    if 'm.phil' in lowered or 'mphil' in lowered:
        return 'M.Phil'
    if 'master' in lowered and 'science' in lowered:
        return 'Master\'s Degree'
    return None


def _detect_unconditional_offer(text: str) -> Optional[str]:
    lowered = text.lower()
    if 'unconditional' in lowered:
        return 'Yes'
    if 'conditional' in lowered:
        return 'No'
    return None


def _detect_category(text: str) -> Optional[str]:
    lowered = text.lower()
    if 'scheduled tribe' in lowered or 'st category' in lowered or 'st ' in lowered:
        return 'ST'
    return None


def _extract_university_name(text: str) -> Optional[str]:
    match = re.search(r'(?:University|Institute|College|Institution)\s*[:\-]?\s*([A-Z][A-Za-z0-9.,\- ()]+)', text)
    if match:
        return match.group(1).strip()
    return None


def _extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}:
        if Image is None or pytesseract is None:
            raise RuntimeError('OCR dependencies are missing for image processing.')
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)

    if ext == '.pdf':
        if convert_from_path is None or pytesseract is None:
            raise RuntimeError('OCR dependencies are missing for PDF processing.')
        pages = convert_from_path(file_path, 200)
        text_chunks = [pytesseract.image_to_string(page) for page in pages]
        return '\n'.join(text_chunks)

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def parse_ocr_text(text: str, doc_type: str) -> Dict[str, Any]:
    normalized = _normalize_text(text or '')
    parsed: Dict[str, Any] = {}

    if not normalized:
        return parsed

    category = _detect_category(normalized)
    if category:
        parsed['category'] = category

    certificate_no = _extract_certificate_number(normalized)
    if certificate_no:
        parsed['caste_certificate_no'] = certificate_no

    income_value = _extract_money_value(normalized)
    if income_value:
        parsed['annual_family_income'] = round(income_value, 2)

    percent = _extract_percentage(normalized)
    if percent is not None:
        parsed['qualifying_percentage'] = percent

    if doc_type in {'foreign_offer_letter', 'admission_letter', 'pg_marksheet', 'qualifying_degree'}:
        offer_status = _detect_unconditional_offer(normalized)
        if offer_status:
            parsed['has_unconditional_offer'] = offer_status

    passport_no = _extract_passport_number(normalized)
    if passport_no:
        parsed['passport_number'] = passport_no

    course = _detect_course(normalized)
    if course:
        parsed['course_enrolled'] = course

    uni_name = _extract_university_name(normalized)
    if uni_name:
        parsed['university_name'] = uni_name

    if 'doc_type' not in parsed:
        parsed['doc_type'] = doc_type

    return parsed


def process_document_ocr(file_path: str, doc_type: str, scheme_code: Optional[str] = None) -> Dict[str, Any]:
    try:
        extracted_text = _extract_text_from_file(file_path)
    except Exception as exc:  # pragma: no cover - runtime failure path
        return {
            'extracted_text': '',
            'parsed_fields': {},
            'ocr_status': 'FAILED',
            'ocr_confidence': 0.0,
            'failed_reason': str(exc),
        }

    cleaned_text = _normalize_text(extracted_text)
    if not cleaned_text:
        return {
            'extracted_text': '',
            'parsed_fields': {},
            'ocr_status': 'FAILED',
            'ocr_confidence': 0.0,
            'failed_reason': 'OCR produced no readable text.',
        }

    parsed_fields = parse_ocr_text(cleaned_text, doc_type)
    text_length = len(cleaned_text)
    confidence = min(0.98, max(0.55, text_length / 2500.0))

    if not parsed_fields:
        return {
            'extracted_text': cleaned_text,
            'parsed_fields': {},
            'ocr_status': 'PARTIAL',
            'ocr_confidence': round(confidence, 2),
            'failed_reason': 'Document text was extracted but no structured values could be confidently parsed.',
        }

    return {
        'extracted_text': cleaned_text,
        'parsed_fields': parsed_fields,
        'ocr_status': 'SUCCESS',
        'ocr_confidence': round(confidence, 2),
        'failed_reason': None,
    }
