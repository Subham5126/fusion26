"""Local candidate analysis service with bounded uploads and in-memory jobs."""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.upload import UploadBudgetMiddleware
from app.core.deployment import cors_origins
from starlette.exceptions import HTTPException

from app.api.health import router as health_router
from app.api.analyze import router as analyze_router
from app.api.jobs import router as jobs_router

app = FastAPI(title="OrbitTrace local prototype", version="0.1.0")
app.add_middleware(UploadBudgetMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(),
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(jobs_router)


@app.exception_handler(HTTPException)
async def http_error(_request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": {
        "code": "not_found" if exc.status_code == 404 else (exc.detail.get("code", "http_error") if isinstance(exc.detail, dict) else "http_error"),
        "message": exc.detail.get("message", "Request failed") if isinstance(exc.detail, dict) else str(exc.detail),
        "details": None,
    }})


@app.exception_handler(RequestValidationError)
async def validation_error(_request, _exc):
    return JSONResponse(status_code=422, content={"error": {
        "code": "invalid_input", "message": "Request does not match the contract", "details": None,
    }})
