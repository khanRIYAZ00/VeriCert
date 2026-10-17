import os
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image
from pypdf import PdfReader

STORAGE_ROOT = Path(os.getenv("VERICERT_STORAGE_PATH", "storage/templates"))
ALLOWED_MIME = {"image/png", "image/jpeg", "application/pdf"}
MAX_UPLOAD_BYTES = 12 * 1024 * 1024


def _validate_file_signature(path: Path, content_type: str) -> None:
    with path.open("rb") as file:
        header = file.read(512)

    if content_type == "image/png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("PNG signature mismatch")
    if content_type == "image/jpeg" and not (header.startswith(b"\xff\xd8\xff") and b"JFIF" in header[:32] or b"Exif" in header[:32]):
        raise ValueError("JPEG signature mismatch")
    if content_type == "application/pdf" and not header.startswith(b"%PDF"):
        raise ValueError("PDF signature mismatch")


def save_template_artwork(upload: UploadFile) -> tuple[str, str, float, float]:
    if upload.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Upload a PNG, JPEG, or one-page PDF")
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    suffix = {"image/png": ".png", "image/jpeg": ".jpg", "application/pdf": ".pdf"}[upload.content_type]
    key = f"{uuid.uuid4().hex}{suffix}"
    target = STORAGE_ROOT / key
    with target.open("wb") as destination:
        shutil.copyfileobj(upload.file, destination)
    if target.stat().st_size > MAX_UPLOAD_BYTES:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Template artwork exceeds 12 MB")
    try:
        _validate_file_signature(target, upload.content_type)
        if upload.content_type == "application/pdf":
            reader = PdfReader(str(target))
            if len(reader.pages) != 1:
                raise ValueError("PDF must contain exactly one page")
            box = reader.pages[0].mediabox
            width, height = float(box.width), float(box.height)
        else:
            with Image.open(target) as image:
                width, height = float(image.width), float(image.height)
    except Exception as error:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Invalid template artwork: {error}")
    return key, upload.content_type, width, height


def template_path(key: str) -> Path:
    return STORAGE_ROOT / Path(key).name
