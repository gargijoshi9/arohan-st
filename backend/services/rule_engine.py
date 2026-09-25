from typing import Any, Dict, List, Optional


def evaluate_application_rules(
    scheme_code: str,
    declared_fields: Dict[str, Any],
    scheme_config: Dict[str, Any],
    documents: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Apply transparent, scheme-configured checks to declared application data.

    This is deterministic rules evaluation, not ML/OCR or document authentication.
    Each validation in a scheme config supports: required, equals, one_of, min,
    max, max_by_field, and except_if.
    """
    mismatches: List[Dict[str, Any]] = []
    passed_checks: List[str] = []
    checks = scheme_config.get("validation_rules", [])

    for rule in checks:
        field = rule["field"]
        label = rule.get("label", field.replace("_", " ").title())
        value = declared_fields.get(field)
        # A documented exception may waive the check when its condition is true.
        except_if = rule.get("except_if")
        if except_if and declared_fields.get(except_if.get("field")) == except_if.get("equals"):
            passed_checks.append(f"{label}: conditional exception recorded for officer verification.")
            continue
        if value is None or (isinstance(value, str) and not value.strip()):
            required_if = rule.get("required_if")
            conditional_required = not required_if or declared_fields.get(required_if.get("field")) == required_if.get("equals")
            if rule.get("required") or conditional_required:
                _add_mismatch(mismatches, rule, label, "Not provided", "Required application information is missing.")
            continue

        expected = rule.get("expected", "Must satisfy scheme criteria")
        rule_type = rule.get("type")
        try:
            if rule_type in ("min", "max", "max_by_field"):
                actual = float(value)
                if rule_type == "max_by_field":
                    limits = rule["limits"]
                    bound = limits.get(str(declared_fields.get(rule["selector_field"])))
                    if bound is None:
                        continue
                    passed = actual <= float(bound)
                    expected = f"Must be ≤ {bound} for selected {rule.get('selector_label', 'category')}"
                else:
                    bound = float(rule["value"])
                    passed = actual >= bound if rule_type == "min" else actual <= bound
                if not passed:
                    _add_mismatch(mismatches, rule, label, value, expected)
                else:
                    passed_checks.append(f"{label} satisfies scheme criteria.")
            elif rule_type == "equals":
                passed = str(value).strip().casefold() == str(rule["value"]).casefold()
                if not passed:
                    _add_mismatch(mismatches, rule, label, value, expected)
                else:
                    passed_checks.append(f"{label} satisfies scheme criteria.")
            elif rule_type == "one_of":
                options = rule["values"]
                passed = str(value).strip().casefold() in {str(item).casefold() for item in options}
                if not passed:
                    _add_mismatch(mismatches, rule, label, value, expected)
                else:
                    passed_checks.append(f"{label} satisfies scheme criteria.")
        except (TypeError, ValueError):
            _add_mismatch(mismatches, rule, label, value, "Provide a valid value for this field.")

    uploaded_doc_types = set()
    for doc in documents or []:
        if isinstance(doc, dict):
            uploaded_doc_types.add(doc.get("doc_type"))
        elif hasattr(doc, "doc_type"):
            uploaded_doc_types.add(doc.doc_type)

    for req_doc in scheme_config.get("required_documents", []):
        if req_doc.get("required") and req_doc.get("id") not in uploaded_doc_types:
            mismatches.append({
                "field": f"doc_{req_doc['id']}",
                "label": req_doc.get("name", req_doc["id"]),
                "declared_value": "Not uploaded",
                "expected_rule": "Mandatory document attachment",
                "severity": "ERROR",
                "description": f"Missing required document: {req_doc.get('name', req_doc['id'])}.",
            })

    has_errors = any(item["severity"] == "ERROR" for item in mismatches)
    summary = (
        f"Rule checks flagged {sum(item['severity'] == 'ERROR' for item in mismatches)} eligibility issue(s); officer review required."
        if has_errors else
        f"No configured eligibility rule failures found. {len(passed_checks)} checks passed; documents and claims still require official verification."
    )
    return {
        "pass_fail": not has_errors,
        # Legacy API/UI field. This is a rules status indicator, not calibrated confidence.
        "confidence_score": max(15.0, min(99.0, 98.0 - 20.0 * sum(item["severity"] == "ERROR" for item in mismatches) - 4.0 * sum(item["severity"] == "WARNING" for item in mismatches))),
        "mismatches": mismatches,
        "passed_checks": passed_checks,
        "summary": summary,
    }


def _add_mismatch(mismatches: List[Dict[str, Any]], rule: Dict[str, Any], label: str, value: Any, expected: str) -> None:
    mismatches.append({
        "field": rule["field"],
        "label": label,
        "declared_value": value,
        "expected_rule": expected,
        "severity": rule.get("severity", "ERROR"),
        "description": rule.get("description", f"{label} does not meet the configured scheme requirement."),
    })
