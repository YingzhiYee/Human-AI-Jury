from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Stance(StrEnum):
    YES = "yes"
    NO = "no"
    NEUTRAL = "neutral"


class Verdict(StrEnum):
    YES = "YES"
    NO = "NO"
    INCONCLUSIVE = "INCONCLUSIVE"


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def normalize_stance(value: str | Stance) -> Stance:
    if isinstance(value, Stance):
        return value

    normalized = value.strip().lower()
    if normalized == "yes":
        return Stance.YES
    if normalized == "no":
        return Stance.NO
    return Stance.NEUTRAL


def opposite_stance(stance: Stance) -> Stance:
    if stance == Stance.YES:
        return Stance.NO
    if stance == Stance.NO:
        return Stance.YES
    return Stance.NEUTRAL


def evidence_weight(evidence: "Evidence") -> float:
    return round(
        clamp(
            (evidence.credibility * 0.45)
            + (evidence.relevance * 0.45)
            + (evidence.freshness * 0.10),
            0.0,
            1.0,
        ),
        4,
    )


def vote_weight(vote: "HumanVote") -> float:
    return round(clamp(vote.weight * vote.confidence, 0.0, 1.0), 4)


@dataclass(slots=True)
class Evidence:
    evidence_id: str
    title: str
    summary: str
    source_type: str
    stance: Stance
    credibility: float
    relevance: float
    url: str | None = None
    freshness: float = 0.5
    submitted_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Evidence":
        return cls(
            evidence_id=payload["evidence_id"],
            title=payload["title"],
            summary=payload["summary"],
            source_type=payload["source_type"],
            stance=normalize_stance(payload.get("stance", "neutral")),
            credibility=clamp(float(payload.get("credibility", 0.5)), 0.0, 1.0),
            relevance=clamp(float(payload.get("relevance", 0.5)), 0.0, 1.0),
            url=payload.get("url"),
            freshness=clamp(float(payload.get("freshness", 0.5)), 0.0, 1.0),
            submitted_by=payload.get("submitted_by"),
            metadata=payload.get("metadata", {}),
        )


@dataclass(slots=True)
class HumanVote:
    voter_id: str
    stance: Stance
    confidence: float
    weight: float = 1.0
    comment: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HumanVote":
        return cls(
            voter_id=payload["voter_id"],
            stance=normalize_stance(payload.get("stance", "neutral")),
            confidence=clamp(float(payload.get("confidence", 0.5)), 0.0, 1.0),
            weight=clamp(float(payload.get("weight", 1.0)), 0.0, 1.0),
            comment=payload.get("comment", ""),
        )


@dataclass(slots=True)
class Challenge:
    challenge_id: str
    target_stance: Stance
    summary: str
    severity: float = 0.5
    submitted_by: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Challenge":
        return cls(
            challenge_id=payload["challenge_id"],
            target_stance=normalize_stance(payload.get("target_stance", "neutral")),
            summary=payload["summary"],
            severity=clamp(float(payload.get("severity", 0.5)), 0.0, 1.0),
            submitted_by=payload.get("submitted_by"),
        )


@dataclass(slots=True)
class CaseFile:
    case_id: str
    question: str
    market_rule: str = ""
    description: str = ""
    prior_yes: float = 0.5
    evidence_pool: list[Evidence] = field(default_factory=list)
    human_votes: list[HumanVote] = field(default_factory=list)
    challenges: list[Challenge] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CaseFile":
        return cls(
            case_id=payload["case_id"],
            question=payload["question"],
            market_rule=payload.get("market_rule", ""),
            description=payload.get("description", ""),
            prior_yes=clamp(float(payload.get("prior_yes", 0.5)), 0.01, 0.99),
            evidence_pool=[
                Evidence.from_dict(item) for item in payload.get("evidence_pool", [])
            ],
            human_votes=[
                HumanVote.from_dict(item) for item in payload.get("human_votes", [])
            ],
            challenges=[
                Challenge.from_dict(item) for item in payload.get("challenges", [])
            ],
        )


@dataclass(slots=True)
class Claim:
    statement: str
    evidence_ids: list[str]
    strength: float


@dataclass(slots=True)
class AgentArgument:
    agent_name: str
    stance: Stance
    confidence: float
    summary: str
    claims: list[Claim]
    counterpoints: list[str]
    cited_evidence_ids: list[str]
    weaknesses: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BayesianSnapshot:
    prior_yes: float
    posterior_yes: float
    evidence_yes_strength: float
    evidence_no_strength: float
    human_yes_strength: float
    human_no_strength: float
    challenge_pressure: float
    disagreement: float
    confidence_interval: float


@dataclass(slots=True)
class AggregationReport:
    prosecutor_score: float
    defense_score: float
    leading_stance: Stance
    conflict_level: float
    decisive_evidence_ids: list[str]
    notes: list[str]


@dataclass(slots=True)
class JudgeOpinion:
    verdict: Verdict
    winning_stance: Stance
    probability_yes: float
    final_confidence: float
    rationale: str
    decisive_points: list[str]
    cautions: list[str]


@dataclass(slots=True)
class Resolution:
    case_id: str
    question: str
    verdict: Verdict
    probability_yes: float
    confidence_interval: float
    final_confidence: float
    summary: str
    rationale: str
    decisive_evidence_ids: list[str]
    audit_trail: list[str]


@dataclass(slots=True)
class DeliberationResult:
    case_id: str
    prosecutor_argument: AgentArgument
    defense_argument: AgentArgument
    bayesian_snapshot: BayesianSnapshot
    aggregation_report: AggregationReport
    judge_opinion: JudgeOpinion
    resolution: Resolution

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


def _serialize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    return value
