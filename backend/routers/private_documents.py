"""Authorised retrieval of stored document files.

Uploaded documents live in MongoDB GridFS and are never exposed as a static
directory. Every request re-checks that the caller either owns the application
or is an officer, and the response is served from the database rather than from
a path the browser could guess.
"""

from pathlib import Path
from typing import Iterator
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pymongo.database import Database

from database import APPLICATIONS, DOCUMENTS, get_db
from security import Principal, require_principal
from services import storage

router = APIRouter(prefix="/private-documents", tags=["Private Documents"])

# Documents are at most 10 MB, so a single read is bounded and simple.
CHUNK_SIZE = 64 * 1024


def authorise_document(db: Database, document_id: int, principal: Principal) -> dict:
    """Return the document record, or refuse the request.

    Officers may read any document. An applicant may read only a document that
    belongs to one of their own applications.
    """
    document = db[DOCUMENTS].find_one({"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if principal.role == "admin":
        return document

    application = db[APPLICATIONS].find_one({"id": document["application_id"]})
    if not application or application.get("applicant_user_id") != principal.user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this document.")
    return document


@router.get("/{document_id:int}/file")
def get_private_document(
    document_id: int,
    principal: Principal = Depends(require_principal),
    db: Database = Depends(get_db),
):
    """Stream a stored document to its owner or to an officer."""
    document = authorise_document(db, document_id, principal)

    gridfs_id = document.get("gridfs_id")
    stream = storage.open_stream(db, gridfs_id)
    if stream is None:
        raise HTTPException(status_code=404, detail="The stored file for this document is no longer available.")

    def chunks() -> Iterator[bytes]:
        try:
            while True:
                block = stream.read(CHUNK_SIZE)
                if not block:
                    return
                yield block
        finally:
            stream.close()

    file_name = Path(document.get("file_name") or "document").name
    # Attached rather than inline, so a stored file cannot be rendered as active
    # content in the reader's browser. The name is quoted because it is
    # attacker-controlled and lands in a response header.
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name)}",
        # A document must never be interpreted as a page of this application.
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Cache-Control": "private, no-store",
    }
    return StreamingResponse(
        chunks(),
        media_type=storage.media_type_for(file_name),
        headers=headers,
    )
