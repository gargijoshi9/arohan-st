import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Scheme, Applicant, Application, Document
from services.rule_engine import evaluate_application_rules

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMES_DIR = os.path.join(BASE_DIR, "data", "scheme_configs")

def seed_schemes(db: Session):
    """Seed all configured MoTA schemes from data/scheme_configs."""
    for filename in sorted(os.listdir(SCHEMES_DIR)):
        if not filename.lower().endswith(".json"):
            continue
        file_path = os.path.join(SCHEMES_DIR, filename)
        if not os.path.exists(file_path):
            continue
        
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        code = config["code"]
        existing = db.query(Scheme).filter(Scheme.code == code).first()
        
        eligibility = config.get("eligibility_rules", {})
        max_income = eligibility.get("max_annual_income")
        min_pct = eligibility.get("min_qualifying_percentage")
        degree_lvl = config.get("degree_level", "")
        
        if not existing:
            scheme = Scheme(
                code=code,
                name=config["name"],
                description=config["short_description"],
                degree_level=degree_lvl,
                max_income=max_income,
                min_percentage=min_pct,
                config_json=json.dumps(config)
            )
            db.add(scheme)
        else:
            existing.name = config["name"]
            existing.description = config["short_description"]
            existing.degree_level = degree_lvl
            existing.max_income = max_income
            existing.min_percentage = min_pct
            existing.config_json = json.dumps(config)

    db.commit()

def seed_demo_applications(db: Session):
    """Seed representative applications demonstrating high-confidence and flagged rule-engine checks."""
    if db.query(Application).count() > 0:
        return  # already seeded

    nfst = db.query(Scheme).filter(Scheme.code == "NFST").first()
    nos = db.query(Scheme).filter(Scheme.code == "NOS").first()
    if not nfst or not nos:
        return

    nfst_config = json.loads(nfst.config_json)
    nos_config = json.loads(nos.config_json)

    # Demo 1: Ramesh Chandra Munda - NFST, Fully Eligible (High Confidence)
    app1_data = {
        "full_name": "Ramesh Chandra Munda",
        "email": "ramesh.munda@example.edu",
        "phone": "9876543210",
        "category": "ST",
        "caste_certificate_no": "ST/JH/2023/88921",
        "course_enrolled": "Ph.D",
        "study_mode": "Regular / Full-time",
        "institution_category": "Central/State Government funded",
        "applicant_age": 29,
        "university_name": "Jawaharlal Nehru University, New Delhi",
        "research_topic": "Tribal Ethnobotany of Chota Nagpur Plateau",
        "admission_year": 2024,
        "pg_percentage": 68.5
    }
    app1_docs = [
        {"doc_type": "caste_cert", "file_name": "st_caste_cert_ramesh.pdf"},
        {"doc_type": "institution_proof", "file_name": "jnu_recognition.pdf"},
        {"doc_type": "admission_letter", "file_name": "jnu_phd_admission_letter.pdf"},
        {"doc_type": "pg_marksheet", "file_name": "msc_marksheet_68.5.pdf"},
        {"doc_type": "id_proof", "file_name": "aadhaar_card_masked.pdf"}
    ]
    eval1 = evaluate_application_rules("NFST", app1_data, nfst_config, app1_docs)
    
    applicant1 = Applicant(
        full_name=app1_data["full_name"],
        email=app1_data["email"],
        phone=app1_data["phone"],
        category="ST",
        caste_certificate_no=app1_data["caste_certificate_no"],
        annual_income=app1_data["annual_family_income"]
    )
    db.add(applicant1)
    db.commit()
    db.refresh(applicant1)

    application1 = Application(
        application_no="AROHAN-NFST-2024-81920",
        scheme_id=nfst.id,
        applicant_id=applicant1.id,
        declared_data=json.dumps(app1_data),
        confidence_score=eval1["confidence_score"],
        status="APPROVED",
        ai_evaluation=json.dumps(eval1),
        admin_remarks="All criteria met. Caste certificate verified against state portal stub.",
        created_at=datetime.utcnow() - timedelta(days=3)
    )
    db.add(application1)
    db.commit()
    db.refresh(application1)

    for d in app1_docs:
        db.add(Document(
            application_id=application1.id,
            doc_type=d["doc_type"],
            file_name=d["file_name"],
            file_path=f"/sample-documents/{d['file_name']}",
            status="VERIFIED"
        ))

    # Demo 2: Sunita Devi Soren - NOS, UK Masters, High Confidence
    app2_data = {
        "full_name": "Sunita Devi Soren",
        "email": "sunita.soren@example.com",
        "phone": "9811223344",
        "category": "ST",
        "caste_certificate_no": "ST/OD/2022/45109",
        "applicant_age": 27,
        "annual_family_income": 350000,
        "course_level": "Master’s",
        "qs_top_1000": "No",
        "one_child_self_certified": "Yes",
        "prior_award": "No",
        "admission_stage": "Already pursuing",
        "is_orphan": "No",
        "destination_country": "United Kingdom",
        "foreign_university": "University of Edinburgh",
        "foreign_course": "MSc in Ecological Economics",
        "has_unconditional_offer": "Yes",
        "qualifying_percentage": 71.4,
        "passport_number": "Z6543219"
    }
    app2_docs = [
        {"doc_type": "caste_cert", "file_name": "st_caste_cert_sunita.pdf"},
        {"doc_type": "income_cert", "file_name": "income_cert_sunita.pdf"},
        {"doc_type": "dob_proof", "file_name": "tenth_certificate.pdf"},
        {"doc_type": "qualifying_marks", "file_name": "bsc_honours_transcript.pdf"},
        {"doc_type": "one_child_declaration", "file_name": "one_child_declaration.pdf"},
        {"doc_type": "admission_proof", "file_name": "edinburgh_admission.pdf"},
        {"doc_type": "income_cert", "file_name": "income_cert_sunita.pdf"}
    ]
    eval2 = evaluate_application_rules("NOS", app2_data, nos_config, app2_docs)

    applicant2 = Applicant(
        full_name=app2_data["full_name"],
        email=app2_data["email"],
        phone=app2_data["phone"],
        category="ST",
        caste_certificate_no=app2_data["caste_certificate_no"],
        annual_income=app2_data["annual_family_income"]
    )
    db.add(applicant2)
    db.commit()
    db.refresh(applicant2)

    application2 = Application(
        application_no="AROHAN-NOS-2024-41092",
        scheme_id=nos.id,
        applicant_id=applicant2.id,
        declared_data=json.dumps(app2_data),
        confidence_score=eval2["confidence_score"],
        status="SUBMITTED",
        ai_evaluation=json.dumps(eval2),
        admin_remarks="",
        created_at=datetime.utcnow() - timedelta(hours=18)
    )
    db.add(application2)
    db.commit()
    db.refresh(application2)

    for d in app2_docs:
        db.add(Document(
            application_id=application2.id,
            doc_type=d["doc_type"],
            file_name=d["file_name"],
            file_path=f"/sample-documents/{d['file_name']}",
            status="UPLOADED"
        ))

    # Demo 3: Amit Tirkey - NOS, FLAGGED (Income > 6L and Percentage < 60%)
    app3_data = {
        "full_name": "Amit Tirkey",
        "email": "amit.tirkey@example.com",
        "phone": "9933445566",
        "category": "ST",
        "caste_certificate_no": "ST/CG/2021/11029",
        "applicant_age": 31,
        "annual_family_income": 780000,  # EXCEEDS 6L CAP!
        "course_level": "Master’s",
        "qs_top_1000": "No",
        "one_child_self_certified": "Yes",
        "prior_award": "No",
        "admission_stage": "Offer / preliminary offer",
        "is_orphan": "No",
        "destination_country": "Australia",
        "foreign_university": "University of Melbourne",
        "foreign_course": "Master of Environmental Science",
        "has_unconditional_offer": "No",  # CONDITIONAL OFFER!
        "qualifying_percentage": 54.5,   # BELOW 60% CAP!
        "passport_number": "T9988771"
    }
    app3_docs = [
        {"doc_type": "caste_cert", "file_name": "caste_cert_tirkey.pdf"},
        {"doc_type": "income_cert", "file_name": "income_cert_7.8L.pdf"}
    ]
    eval3 = evaluate_application_rules("NOS", app3_data, nos_config, app3_docs)

    applicant3 = Applicant(
        full_name=app3_data["full_name"],
        email=app3_data["email"],
        phone=app3_data["phone"],
        category="ST",
        caste_certificate_no=app3_data["caste_certificate_no"],
        annual_income=app3_data["annual_family_income"]
    )
    db.add(applicant3)
    db.commit()
    db.refresh(applicant3)

    application3 = Application(
        application_no="AROHAN-NOS-2024-19403",
        scheme_id=nos.id,
        applicant_id=applicant3.id,
        declared_data=json.dumps(app3_data),
        confidence_score=eval3["confidence_score"],
        status="DEFICIENT",
        ai_evaluation=json.dumps(eval3),
        admin_remarks="Flagged by Rule Engine: Income exceeds ₹6,00,000 threshold and degree percentage is below minimum 60%. Unconditional offer pending.",
        created_at=datetime.utcnow() - timedelta(days=1)
    )
    db.add(application3)
    db.commit()
    db.refresh(application3)

    for d in app3_docs:
        db.add(Document(
            application_id=application3.id,
            doc_type=d["doc_type"],
            file_name=d["file_name"],
            file_path=f"/sample-documents/{d['file_name']}",
            status="DEFICIENT"
        ))

    # Demo 4: Pooja Boro - NFST, Under Review
    app4_data = {
        "full_name": "Pooja Boro",
        "email": "pooja.boro@example.ac.in",
        "phone": "9864012345",
        "category": "ST",
        "caste_certificate_no": "ST/AS/2023/33918",
        "annual_family_income": 190000,
        "course_enrolled": "Ph.D",
        "university_name": "Gauhati University",
        "research_topic": "Bodo Linguistics and Cultural Heritage Documentation",
        "admission_year": 2024,
        "pg_percentage": 62.0
    }
    app4_docs = [
        {"doc_type": "caste_cert", "file_name": "st_caste_boro.pdf"},
        {"doc_type": "income_cert", "file_name": "income_boro_1.9L.pdf"},
        {"doc_type": "admission_letter", "file_name": "gu_admission_slip.pdf"},
        {"doc_type": "pg_marksheet", "file_name": "ma_linguistics_marksheet.pdf"}
    ]
    eval4 = evaluate_application_rules("NFST", app4_data, nfst_config, app4_docs)

    applicant4 = Applicant(
        full_name=app4_data["full_name"],
        email=app4_data["email"],
        phone=app4_data["phone"],
        category="ST",
        caste_certificate_no=app4_data["caste_certificate_no"],
        annual_income=app4_data["annual_family_income"]
    )
    db.add(applicant4)
    db.commit()
    db.refresh(applicant4)

    application4 = Application(
        application_no="AROHAN-NFST-2024-99201",
        scheme_id=nfst.id,
        applicant_id=applicant4.id,
        declared_data=json.dumps(app4_data),
        confidence_score=eval4["confidence_score"],
        status="UNDER_REVIEW",
        ai_evaluation=json.dumps(eval4),
        admin_remarks="",
        created_at=datetime.utcnow() - timedelta(hours=6)
    )
    db.add(application4)
    db.commit()
    db.refresh(application4)

    for d in app4_docs:
        db.add(Document(
            application_id=application4.id,
            doc_type=d["doc_type"],
            file_name=d["file_name"],
            file_path=f"/sample-documents/{d['file_name']}",
            status="UPLOADED"
        ))

    db.commit()
