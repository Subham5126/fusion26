"""Health-only local service. Analysis routes are reserved for T09."""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.health import router

app = FastAPI(title="OrbitTrace bootstrap", version="0.1.0")
app.include_router(router)


@app.exception_handler(HTTPException)
async def http_error(_request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": {
        "code": "not_found" if exc.status_code == 404 else "http_error",
        "message": "Route unavailable in bootstrap" if exc.status_code == 404 else "Request failed",
        "details": None,
    }})


@app.exception_handler(RequestValidationError)
async def validation_error(_request, _exc):
    return JSONResponse(status_code=422, content={"error": {
        "code": "invalid_input", "message": "Request does not match the contract", "details": None,
    }})
