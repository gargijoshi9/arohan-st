import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Scheme
from schemas import SchemeRead

router = APIRouter(prefix="/schemes", tags=["Schemes"])

@router.get("", response_model=List[SchemeRead])
def get_all_schemes(db: Session = Depends(get_db)):
    """Fetch all available MoTA scholarship and fellowship schemes."""
    schemes = db.query(Scheme).all()
    result = []
    for s in schemes:
        config_data = json.loads(s.config_json) if s.config_json else {}
        result.append(SchemeRead(
            id=s.id,
            code=s.code,
            name=s.name,
            description=s.description,
            degree_level=s.degree_level,
            max_income=s.max_income,
            min_percentage=s.min_percentage,
            config=config_data
        ))
    return result

@router.get("/{scheme_id}", response_model=SchemeRead)
def get_scheme_by_id(scheme_id: int, db: Session = Depends(get_db)):
    """Get scheme details and dynamic form definition by ID."""
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    config_data = json.loads(scheme.config_json) if scheme.config_json else {}
    return SchemeRead(
        id=scheme.id,
        code=scheme.code,
        name=scheme.name,
        description=scheme.description,
        degree_level=scheme.degree_level,
        max_income=scheme.max_income,
        min_percentage=scheme.min_percentage,
        config=config_data
    )

@router.get("/code/{code}", response_model=SchemeRead)
def get_scheme_by_code(code: str, db: Session = Depends(get_db)):
    """Get scheme details and dynamic form definition by code (NFST or NOS)."""
    scheme = db.query(Scheme).filter(Scheme.code == code.upper()).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{code}' not found")
    config_data = json.loads(scheme.config_json) if scheme.config_json else {}
    return SchemeRead(
        id=scheme.id,
        code=scheme.code,
        name=scheme.name,
        description=scheme.description,
        degree_level=scheme.degree_level,
        max_income=scheme.max_income,
        min_percentage=scheme.min_percentage,
        config=config_data
    )
