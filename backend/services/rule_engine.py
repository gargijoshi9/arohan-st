from typing import Dict, Any, List, Optional

def evaluate_application_rules(
    scheme_code: str,
    declared_fields: Dict[str, Any],
    scheme_config: Dict[str, Any],
    documents: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    AROHAN-ST AI Rule Engine:
    Compares declared applicant fields and document references against
    the scheme's JSON configuration criteria.
    Returns pass_fail status, confidence score (0-100), and structured mismatches.
    """
    eligibility = scheme_config.get("eligibility_rules", {})
    required_docs = scheme_config.get("required_documents", [])
    
    mismatches: List[Dict[str, Any]] = []
    passed_checks: List[str] = []
    
    # Base confidence score
    confidence = 98.0
    
    # 1. Social Category Verification (ST check)
    category = str(declared_fields.get("category", "")).strip().upper()
    target_category = eligibility.get("target_category", "ST")
    if category != target_category:
        mismatches.append({
            "field": "category",
            "label": "Social Category",
            "declared_value": category or "Not Provided",
            "expected_rule": f"Must belong to {target_category} (Scheduled Tribe)",
            "severity": "ERROR",
            "description": f"Ineligible category '{category}'. MoTA scheme exclusively reserves benefits for ST candidates."
        })
        confidence -= 35.0
    else:
        passed_checks.append("Verified Scheduled Tribe (ST) category eligibility.")

    # 1b. Caste Certificate Number format check
    caste_cert_no = str(declared_fields.get("caste_certificate_no", "")).strip()
    if not caste_cert_no or len(caste_cert_no) < 4:
        mismatches.append({
            "field": "caste_certificate_no",
            "label": "Caste Certificate Number",
            "declared_value": caste_cert_no or "None",
            "expected_rule": "Valid State/UT issued Certificate identifier",
            "severity": "WARNING",
            "description": "Missing or abnormally short ST certificate registration number."
        })
        confidence -= 10.0
    else:
        passed_checks.append(f"Caste certificate identifier '{caste_cert_no}' recorded.")

    # 2. Annual Family Income Check
    income_cap = eligibility.get("max_annual_income")
    declared_income_raw = declared_fields.get("annual_family_income")
    try:
        declared_income = float(declared_income_raw) if declared_income_raw is not None else 0.0
    except (ValueError, TypeError):
        declared_income = 0.0

    if income_cap is not None:
        if declared_income > income_cap:
            mismatches.append({
                "field": "annual_family_income",
                "label": "Annual Family Income",
                "declared_value": f"₹{declared_income:,.0f}",
                "expected_rule": f"Income must not exceed ₹{income_cap:,.0f} per annum",
                "severity": "ERROR",
                "description": f"Declared income ₹{declared_income:,.0f} exceeds the statutory threshold of ₹{income_cap:,.0f}."
            })
            confidence -= 30.0
        else:
            passed_checks.append(f"Annual income ₹{declared_income:,.0f} complies with ceiling (≤ ₹{income_cap:,.0f}).")

    # 3. Academic Percentage Check
    min_percentage = eligibility.get("min_qualifying_percentage")
    pct_field = "pg_percentage" if scheme_code == "NFST" else "qualifying_percentage"
    declared_pct_raw = declared_fields.get(pct_field)
    try:
        declared_pct = float(declared_pct_raw) if declared_pct_raw is not None else 0.0
    except (ValueError, TypeError):
        declared_pct = 0.0

    if min_percentage is not None:
        if declared_pct < min_percentage:
            mismatches.append({
                "field": pct_field,
                "label": "Qualifying Marks (%)",
                "declared_value": f"{declared_pct}%",
                "expected_rule": f"Minimum {min_percentage}% aggregate required",
                "severity": "ERROR",
                "description": f"Academic aggregate of {declared_pct}% is below minimum cutoff of {min_percentage}%."
            })
            confidence -= 25.0
        else:
            passed_checks.append(f"Academic aggregate of {declared_pct}% meets scheme threshold (≥ {min_percentage}%).")

    # 4. Age Limit Check (e.g. NOS max age = 35)
    max_age = eligibility.get("max_age")
    if max_age is not None:
        declared_age_raw = declared_fields.get("applicant_age")
        try:
            declared_age = int(declared_age_raw) if declared_age_raw is not None else 0
        except (ValueError, TypeError):
            declared_age = 0
        
        if declared_age > max_age:
            mismatches.append({
                "field": "applicant_age",
                "label": "Applicant Age",
                "declared_value": f"{declared_age} years",
                "expected_rule": f"Age must be ≤ {max_age} years as of selection year",
                "severity": "ERROR",
                "description": f"Applicant age of {declared_age} exceeds permissible age limit of {max_age}."
            })
            confidence -= 20.0
        elif declared_age > 0:
            passed_checks.append(f"Applicant age ({declared_age} yrs) within age limit (≤ {max_age} yrs).")

    # 5. Scheme-Specific Rules
    if scheme_code == "NOS":
        unconditional_offer = declared_fields.get("has_unconditional_offer")
        if unconditional_offer != "Yes":
            mismatches.append({
                "field": "has_unconditional_offer",
                "label": "Unconditional Admission Offer",
                "declared_value": unconditional_offer or "No",
                "expected_rule": "Confirmed unconditional offer letter required",
                "severity": "ERROR",
                "description": "Applicant does not have an unconditional admission offer from host foreign university."
            })
            confidence -= 20.0
        else:
            passed_checks.append("Unconditional foreign university admission offer confirmed.")

    if scheme_code == "NFST":
        course = declared_fields.get("course_enrolled")
        eligible_courses = eligibility.get("eligible_courses", ["M.Phil", "Ph.D", "Integrated Ph.D"])
        if course and course not in eligible_courses:
            mismatches.append({
                "field": "course_enrolled",
                "label": "Course Enrolled",
                "declared_value": course,
                "expected_rule": f"Must be one of: {', '.join(eligible_courses)}",
                "severity": "ERROR",
                "description": f"Course '{course}' is not supported under NFST fellowship."
            })
            confidence -= 20.0
        elif course:
            passed_checks.append(f"Course enrollment '{course}' is eligible for doctoral fellowship.")

    # 6. Document Upload Completeness Check
    uploaded_doc_types = set()
    if documents:
        for doc in documents:
            if isinstance(doc, dict):
                uploaded_doc_types.add(doc.get("doc_type"))
            elif hasattr(doc, "doc_type"):
                uploaded_doc_types.add(doc.doc_type)

    for req_doc in required_docs:
        doc_id = req_doc.get("id")
        if req_doc.get("required") and doc_id not in uploaded_doc_types:
            # Add warning mismatch for missing doc
            mismatches.append({
                "field": f"doc_{doc_id}",
                "label": req_doc.get("name"),
                "declared_value": "Not Uploaded",
                "expected_rule": "Mandatory document attachment",
                "severity": "WARNING",
                "description": f"Missing mandatory document: {req_doc.get('name')}."
            })
            confidence -= 8.0

    # Calculate final confidence score bounded between 15% and 99%
    confidence = max(15.0, min(99.0, confidence))
    has_error_mismatches = any(m["severity"] == "ERROR" for m in mismatches)
    pass_fail = not has_error_mismatches

    if pass_fail:
        summary = (
            f"Automated verification PASSED with {confidence:.1f}% confidence score. "
            f"All {len(passed_checks)} statutory criteria verified successfully."
        )
    else:
        error_count = sum(1 for m in mismatches if m["severity"] == "ERROR")
        summary = (
            f"Automated verification FLAGGED {error_count} critical discrepancy(ies). "
            f"Review queue confidence score reduced to {confidence:.1f}%."
        )

    return {
        "pass_fail": pass_fail,
        "confidence_score": round(confidence, 1),
        "mismatches": mismatches,
        "passed_checks": passed_checks,
        "summary": summary
    }
