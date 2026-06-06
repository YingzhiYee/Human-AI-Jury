"""Public jury routes used by the frontend."""

from __future__ import annotations

from fastapi import APIRouter

from .demo_routes import DemoRunRequest, get_default_case, run_demo

router = APIRouter(prefix="/api/jury", tags=["Jury"])


@router.get("/default-case")
def get_jury_default_case() -> dict:
    return get_default_case()


@router.post("/run")
def run_jury(request: DemoRunRequest) -> dict:
    return run_demo(request)
