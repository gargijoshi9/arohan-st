"""Binary document storage backed by MongoDB GridFS.

Uploaded certificates and statements are applicant data, so they are kept in the
same database as the records that reference them rather than on the server's
local disk. A deployment therefore has one thing to back up, and a document
cannot be orphaned from its application record by a separate disk failure.

Only the `fs.files` metadata and the binary chunks are stored; the searchable
fields of a document (its type, workflow status and extraction result) live in
the `documents` collection and reference the GridFS id in `gridfs_id`.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Optional

from gridfs import GridFSBucket
from gridfs.errors import CorruptGridFile, FileExists, NoFile
from pymongo import DESCENDING
from pymongo.database import Database

from database import utcnow

BUCKET_NAME = "document_files"

# GridFS chunks are capped by BSON's 16 MB document limit. The upload router
# already rejects anything larger than 10 MB, and this is the second gate.
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024

# Only inert types are served inline. Active content such as SVG or HTML is
# deliberately absent so a crafted filename cannot make the browser execute a
# document in the reviewer's session.
_INLINE_SAFE_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".txt": "text/plain; charset=utf-8",
}


class DocumentStorageError(RuntimeError):
    """Raised when a document cannot be written to or read from GridFS."""


@dataclass(frozen=True)
class StoredFile:
    gridfs_id: Any
    length: int
    media_type: str


def bucket(db: Database) -> GridFSBucket:
    """A bucket bound to this request's database handle."""
    return GridFSBucket(db, bucket_name=BUCKET_NAME)


def media_type_for(file_name: str) -> str:
    """Content type used when serving a stored document.

    Unrecognised extensions are served as an attachment rather than guessed at,
    so the browser never renders a stored file as active content.
    """
    extension = Path(file_name or "").suffix.lower()
    if extension in _INLINE_SAFE_TYPES:
        return _INLINE_SAFE_TYPES[extension]
    return "application/octet-stream"


def store(
    db: Database,
    content: bytes,
    *,
    file_name: str,
    application_id: int,
    doc_type: str,
) -> StoredFile:
    """Write one document into GridFS and return its reference.

    `content` is written under a fresh ObjectId, so a replaced document never
    collides with the one it supersedes.
    """
    if not content:
        raise DocumentStorageError("Refusing to store an empty document.")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise DocumentStorageError(
            f"Document is {len(content)} bytes, which exceeds the {MAX_DOCUMENT_BYTES} byte limit."
        )

    safe_name = Path(file_name or "document").name[:255]
    storage = bucket(db)
    try:
        gridfs_id = storage.upload_from_stream(
            safe_name,
            content,
            metadata={
                "application_id": int(application_id),
                "doc_type": doc_type,
                "uploaded_at": utcnow(),
            },
        )
    except (FileExists, CorruptGridFile, OSError) as exc:
        raise DocumentStorageError("The document could not be saved.") from exc

    return StoredFile(
        gridfs_id=gridfs_id,
        length=len(content),
        media_type=media_type_for(safe_name),
    )


def discard(db: Database, gridfs_id: Any) -> None:
    """Delete a stored file, ignoring one that is already gone.

    Replacing a document must not fail because its previous copy is missing.
    """
    if gridfs_id is None:
        return
    try:
        bucket(db).delete(gridfs_id)
    except (NoFile, CorruptGridFile):
        return


def open_stream(db: Database, gridfs_id: Any) -> Optional[BinaryIO]:
    """Open a stored file for reading, or None when it is no longer available."""
    if gridfs_id is None:
        return None
    try:
        return bucket(db).open_download_stream(gridfs_id)
    except (NoFile, CorruptGridFile):
        return None


def file_metadata(db: Database, gridfs_id: Any) -> Optional[dict]:
    """Length and upload time of a stored file, for range and freshness checks."""
    if gridfs_id is None:
        return None
    record = db[f"{BUCKET_NAME}.files"].find_one({"_id": gridfs_id})
    if not record:
        return None
    return {"length": int(record.get("length", 0)), "upload_date": record.get("uploadDate")}


def exists(db: Database, gridfs_id: Any) -> bool:
    if gridfs_id is None:
        return False
    return db[f"{BUCKET_NAME}.files"].find_one({"_id": gridfs_id}, {"_id": 1}) is not None


def delete_orphans(db: Database, referenced_ids: set) -> int:
    """Remove files in the bucket that no document record points at.

    Used after a document is replaced or removed so a superseded upload does not
    linger in the database.
    """
    deleted = 0
    files = db[f"{BUCKET_NAME}.files"].find({}, {"_id": 1}).sort("uploadDate", DESCENDING)
    for record in files:
        if record["_id"] not in referenced_ids:
            discard(db, record["_id"])
            deleted += 1
    return deleted
