"""
FastAPI 路由 — Investigation Layer 对外 HTTP 接口

上游（Frontend / Deliberation Engine）调用此接口触发调查，获取 EvidencePool。
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..investigation.schema import InvestigationRequest, InvestigationResponse
from ..investigation.pipeline import run_investigation

router = APIRouter(prefix="/api/investigation", tags=["Investigation"])


@router.post("/run", response_model=InvestigationResponse)
def start_investigation(req: InvestigationRequest) -> InvestigationResponse:
    """
    触发 Investigation Layer，同步返回 EvidencePool。

    请求示例：
    POST /api/investigation/run
    {
      "market_id": "pm_001",
      "claim": "Trump will pardon Hunter Biden before Jan 20, 2025 inauguration",
      "context": "Polymarket disputed market",
      "max_items_per_agent": 5
    }

    响应示例：
    {
      "success": true,
      "market_id": "pm_001",
      "evidence_pool": {
        "market_id": "pm_001",
        "claim": "...",
        "items": [...],
        "yes_weight": 1.23,
        "no_weight": 0.87,
        "total_items": 18
      }
    }
    """
    try:
        pool = run_investigation(req)
        return InvestigationResponse(success=True, market_id=req.market_id, evidence_pool=pool)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "layer": "investigation"}
