"""Public scheme catalogue. No authentication is required to browse schemes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from database import get_db
from schemas import SchemeRead
from services.repository import get_scheme_by_code, get_scheme_by_id, list_schemes, scheme_config

router = APIRouter(prefix="/schemes", tags=["Schemes"])


def to_response(scheme: dict) -> SchemeRead:
    return SchemeRead(
        id=scheme["id"],
        code=scheme["code"],
        name=scheme["name"],
        description=scheme.get("description"),
        degree_level=scheme.get("degree_level"),
        max_income=scheme.get("max_income"),
        min_percentage=scheme.get("min_percentage"),
        config=scheme_config(scheme),
    )


@router.get("", response_model=List[SchemeRead])
def get_all_schemes(db: Database = Depends(get_db)):
    """Every configured fellowship and scholarship scheme."""
    return [to_response(scheme) for scheme in list_schemes(db)]


@router.get("/code/{code}", response_model=SchemeRead)
def get_scheme_by_code_route(code: str, db: Database = Depends(get_db)):
    """Scheme detail and dynamic form configuration by internal code."""
    scheme = get_scheme_by_code(db, code)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{code}' not found")
    return to_response(scheme)


@router.get("/{scheme_id:int}", response_model=SchemeRead)
def get_scheme_by_id_route(scheme_id: int, db: Database = Depends(get_db)):
    """Scheme detail and dynamic form configuration by identifier.

    Declared after `/code/{code}` so the literal path is matched first.
    """
    scheme = get_scheme_by_id(db, scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return to_response(scheme)
