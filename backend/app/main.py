import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analysis import router as analysis_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.health import router as health_router
from app.middleware.request_size import ScreenshotRequestSizeLimitMiddleware


def _get_cors_origins() -> list[str]:
    configured_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


app = FastAPI(
    title="NIRNAY API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    ScreenshotRequestSizeLimitMiddleware,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(evidence_router)
