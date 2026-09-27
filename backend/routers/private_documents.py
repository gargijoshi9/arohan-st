import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Document
from security import Principal, require_principal

router = APIRouter(prefix="/private-documents", tags=["Private Documents"])
UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"
SAMPLE_ROOT = Path(__file__).resolve().parents[2] / "docs" / "sample-documents"


@router.get("/{document_id:int}/file")
def get_private_document(
    document_id: int,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    application = document.application
    if principal.role != "admin" and application.applicant.email.strip().lower() != principal.email:
        raise HTTPException(status_code=403, detail="You do not have access to this document.")
    if not document.file_path:
        raise HTTPException(status_code=404, detail="No uploaded file is available.")
    normalized_path = document.file_path.replace("\\", "/")
    if normalized_path.startswith("/sample-documents/"):
        stored_path = SAMPLE_ROOT.joinpath(*Path(normalized_path).parts[2:])
        allowed_root = SAMPLE_ROOT
    elif normalized_path.startswith("/uploads/"):
        stored_path = UPLOAD_ROOT.joinpath(*Path(normalized_path).parts[2:])
        allowed_root = UPLOAD_ROOT
    else:
        stored_path = Path(normalized_path)
        allowed_root = UPLOAD_ROOT
        if not stored_path.is_absolute():
            stored_path = UPLOAD_ROOT / stored_path
    resolved_path = stored_path.resolve()
    if not resolved_path.is_relative_to(allowed_root.resolve()) or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded file is not available.")
    return FileResponse(
        resolved_path,
        filename=Path(document.file_name).name,
        media_type=mimetypes.guess_type(document.file_name)[0] or "application/octet-stream",
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff"},
    )
