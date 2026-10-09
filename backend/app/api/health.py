from fastapi import APIRouter

from app.schemas.health import HealthResponse, Capabilities

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    caps = Capabilities(
        schemas=True,
        synthetic_generation=True,
        detection=True,
        tracking=True,
        trajectory=True,
        analysis_api=True,
        uploads=True,
        evaluation=False,
        exports=True
    )
    return HealthResponse(capabilities=caps)
