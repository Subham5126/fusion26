"""Encoded request and decoded image bounds applied before scientific inference."""
from io import BytesIO
from pathlib import Path
import warnings
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException
from starlette.responses import JSONResponse
from astrotrace.preprocessing.images import decode_png

FILE_BYTES = 10*1024*1024
TOTAL_BYTES = 50*1024*1024
REQUEST_BYTES = TOTAL_BYTES + 1024*1024  # bounded multipart framing/manifest allowance

class UploadBudgetExceeded(HTTPException):
    def __init__(self):
        super().__init__(413, "Upload request exceeds the bounded request budget")

class UploadBudgetMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/analyze/upload":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = REQUEST_BYTES + 1
        async def reject():
            response = JSONResponse(status_code=413, content={"error": {"code": "upload_too_large",
                "message": "Upload request exceeds the bounded request budget.", "details": None}})
            await response(scope, receive, send)
        if declared > REQUEST_BYTES:
            return await reject()
        size = 0
        async def bounded_receive():
            nonlocal size
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > REQUEST_BYTES:
                    raise UploadBudgetExceeded()
            return message
        try:
            await self.app(scope, bounded_receive, send)
        except UploadBudgetExceeded:
            await reject()

async def read_bounded_file(upload, remaining):
    chunks, size = [], 0
    while True:
        chunk = await upload.read(64*1024)
        if not chunk:
            break
        size += len(chunk)
        if size > FILE_BYTES or size > remaining:
            raise HTTPException(413, "Image or aggregate file bytes exceed upload limits")
        chunks.append(chunk)
    if not size:
        raise HTTPException(422, "Empty image file")
    return b"".join(chunks)

def decode_upload(content, upload, meta):
    extension = Path(upload.filename or "").suffix.lower()
    if extension not in (".png", ".jpg", ".jpeg") or upload.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(422, "Only PNG and JPEG image files are accepted")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format not in ("PNG", "JPEG") or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Expected a single PNG or JPEG image")
                expected = "PNG" if extension == ".png" else "JPEG"
                if image.format != expected or upload.content_type != ("image/png" if expected == "PNG" else "image/jpeg"):
                    raise ValueError("File signature, extension and media type disagree")
                if image.width*image.height > 4_000_000:
                    raise ValueError("Decoded image exceeds 4 megapixels")
                if image.size != (meta.width_px, meta.height_px):
                    raise ValueError("Image dimensions do not match manifest")
                if image.getexif().get(274, 1) != 1:
                    raise ValueError("Rotated EXIF images require explicit coordinate conversion; orientation 1 is required")
                if image.format == "PNG":
                    return decode_png(content, expected_size=image.size)
                if image.mode != "L":
                    raise ValueError("This telescope profile requires grayscale images")
                image.load()
                pixels = np.asarray(image).copy()
                pixels.setflags(write=False)
                return pixels
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(422, f"Invalid image: {exc}") from exc
