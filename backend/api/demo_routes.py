from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.deliberation import run_deliberation
from backend.investigation.simulated_pool import build_simulated_pool, is_simulated_pool
from backend.investigation.schema import EvidenceDirection, EvidencePool, InvestigationRequest
from backend.models import CaseFile, Challenge, Evidence, HumanVote

router = APIRouter(prefix="/api/demo", tags=["Demo"])


class HumanVoteInput(BaseModel):
    voter_id: str
    stance: Literal["yes", "no", "neutral"] = "neutral"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    comment: str = ""


class ChallengeInput(BaseModel):
    challenge_id: str
    target_stance: Literal["yes", "no", "neutral"] = "neutral"
    summary: str
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    submitted_by: str | None = None


class DemoRunRequest(BaseModel):
    market_id: str = "pm_demo_001"
    claim: str = "Did Trump pardon Hunter Biden before January 20?"
    context: str = "Prediction market dispute demo"
    prior_yes: float = Field(default=0.5, ge=0.01, le=0.99)
    max_items_per_agent: int = Field(default=4, ge=1, le=20)
    human_votes: list[HumanVoteInput] = Field(default_factory=list)
    challenges: list[ChallengeInput] = Field(default_factory=list)


def _direction_to_stance(direction: EvidenceDirection) -> str:
    if direction == EvidenceDirection.SUPPORTS_YES:
        return "yes"
    if direction == EvidenceDirection.SUPPORTS_NO:
        return "no"
    return "neutral"


def _build_case_file(request: DemoRunRequest, pool: EvidencePool) -> CaseFile:
    evidence = [
        Evidence.from_dict(
            {
                "evidence_id": item.id,
                "title": item.title,
                "summary": item.summary,
                "source_type": item.source_type.value,
                "stance": _direction_to_stance(item.direction),
                "credibility": item.confidence,
                "relevance": item.relevance,
                "url": item.url,
                "freshness": 0.7,
                "submitted_by": item.agent or item.source_name,
                "metadata": {
                    "source_name": item.source_name,
                    "raw_snippet": item.raw_snippet,
                    "published_at": item.published_at,
                    "weight": item.weight,
                },
            }
        )
        for item in pool.items
    ]

    human_votes = [HumanVote.from_dict(item.model_dump()) for item in request.human_votes]
    challenges = [Challenge.from_dict(item.model_dump()) for item in request.challenges]

    return CaseFile(
        case_id=request.market_id,
        question=request.claim,
        market_rule=request.context,
        description="Frontend demo flow from investigation to verdict",
        prior_yes=request.prior_yes,
        evidence_pool=evidence,
        human_votes=human_votes,
        challenges=challenges,
    )


def _build_storage_payload(case_file: CaseFile, deliberation_result: dict[str, Any]) -> dict[str, Any]:
    resolution = deliberation_result["resolution"]
    canonical_metadata = {
        "caseId": case_file.case_id,
        "question": case_file.question,
        "verdict": resolution["verdict"],
        "probabilityYes": resolution["probability_yes"],
        "confidenceInterval": resolution["confidence_interval"],
        "finalConfidence": resolution["final_confidence"],
        "decisiveEvidenceIds": resolution["decisive_evidence_ids"],
        "auditTrail": resolution["audit_trail"],
    }
    canonical_json = json.dumps(
        canonical_metadata,
        sort_keys=True,
        separators=(",", ":"),
    )

    return {
        "case_id": case_file.case_id,
        "verdict": resolution["verdict"],
        "confidence_bps": int(round(float(resolution["final_confidence"]) * 10_000)),
        "metadata_uri": "",
        "canonical_json": canonical_json,
        "contract_function": "storeResolution",
    }


@router.get("/default-case")
def get_default_case() -> dict[str, Any]:
    return DemoRunRequest().model_dump()


@router.post("/run")
def run_demo(request: DemoRunRequest) -> dict[str, Any]:
    notices: list[str] = []
    try:
        investigation_request = InvestigationRequest(
            market_id=request.market_id,
            claim=request.claim,
            context=request.context,
            max_items_per_agent=request.max_items_per_agent,
        )
        try:
            from backend.investigation.pipeline import run_investigation

            evidence_pool = run_investigation(investigation_request)
        except Exception as exc:
            notices.append(f"Live investigation unavailable, using simulated evidence: {exc}")
            evidence_pool = build_simulated_pool(investigation_request)

        case_file = _build_case_file(request, evidence_pool)
        deliberation = run_deliberation(case_file).to_dict()
        mode = "simulated" if is_simulated_pool(evidence_pool) else "live"
        if mode == "simulated" and not notices:
            notices.append("Simulated evidence mode is active because live external data was unavailable.")
        if mode == "live" and not any(item.source_type == "social" for item in evidence_pool.items):
            notices.append(
                "No social/X evidence was included in this live run. xAPI may have returned no matches, or the social provider may be unavailable or limited."
            )

        return {
            "mode": mode,
            "notices": notices,
            "case": request.model_dump(),
            "evidence_pool": evidence_pool.model_dump(),
            "deliberation": deliberation,
            "storage_payload": _build_storage_payload(case_file, deliberation),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
