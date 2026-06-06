"""System health and readiness routes for frontend/backend integration."""

from __future__ import annotations

from fastapi import APIRouter

from backend.settings import build_runtime_status

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/health")
def health() -> dict[str, object]:
    status = build_runtime_status()
    return {
        "status": "ok",
        "service": "human-ai-jury-api",
        "python_version": status["python_version"],
        "live_investigation_ready": status["live_investigation_ready"],
    }


@router.get("/readiness")
def readiness() -> dict[str, object]:
    status = build_runtime_status()
    return {
        "status": "ready" if status["live_investigation_ready"] else "degraded",
        "service": "human-ai-jury-api",
        **status,
        "routes": {
            "jury_default_case": "/api/jury/default-case",
            "jury_run": "/api/jury/run",
            "investigation_run": "/api/investigation/run",
        },
    }
