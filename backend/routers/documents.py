from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/documents", tags=["Documents"])
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Store an uploaded demo document and return its view URL."""
    original_name = Path(file.filename or "document").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload a PDF, PNG, JPG, JPEG, or TXT file.")

    content = await file.read(MAX_FILE_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIR / stored_name
    with destination.open("wb") as stream:
        stream.write(content)

    return {"file_name": original_name, "file_path": f"/uploads/{stored_name}"}
