from __future__ import annotations

import hashlib
import re

from .schema import (
    EvidenceDirection,
    EvidenceItem,
    EvidencePool,
    InvestigationRequest,
    SourceType,
)


SIMULATED_AGENT_PREFIX = "Simulated"


def is_simulated_pool(pool: EvidencePool) -> bool:
    return all(item.agent.startswith(SIMULATED_AGENT_PREFIX) for item in pool.items)


def build_simulated_pool(request: InvestigationRequest) -> EvidencePool:
    claim = request.claim.strip()
    category = _detect_category(claim)
    future_like = _is_future_like(claim)
    base_yes = _base_yes_probability(claim, category, future_like)
    lead = _leading_direction(base_yes, future_like)
    opposite = _opposite_direction(lead)

    items = [
        _build_official_item(claim, category, lead, future_like),
        _build_news_item(claim, category, lead, future_like),
        _build_social_item(claim, category, opposite, future_like),
        _build_counter_item(claim, category, opposite, future_like),
    ]

    pool = EvidencePool(
        market_id=request.market_id,
        claim=request.claim,
        items=items[: request.max_items_per_agent],
    )
    pool.compute_summary()
    return pool


def _detect_category(claim: str) -> str:
    lowered = claim.lower()
    if any(token in lowered for token in ["world cup", "fifa", "match", "win", "champion", "team", "final"]):
        return "sports"
    if any(token in lowered for token in ["pardon", "court", "president", "senate", "election", "law", "minister"]):
        return "politics"
    if any(token in lowered for token in ["ipo", "earnings", "etf", "approval", "funding", "acquisition", "listed"]):
        return "finance"
    if any(token in lowered for token in ["release", "launch", "ship", "rollout", "model", "app", "product"]):
        return "product"
    return "generic"


def _is_future_like(claim: str) -> bool:
    lowered = claim.lower()
    future_markers = [
        " will ",
        "this year",
        "next year",
        "tomorrow",
        "next month",
        "in 2026",
        "in 2027",
        "会不会",
        "是否会",
        "今年",
        "明年",
    ]
    return any(marker in f" {lowered} " for marker in future_markers)


def _base_yes_probability(claim: str, category: str, future_like: bool) -> float:
    digest = hashlib.sha256(claim.lower().encode("utf-8")).hexdigest()
    offset = (int(digest[:8], 16) % 1000) / 1000
    base = 0.30 + (offset * 0.40)

    if category == "sports":
        base = 0.34 + (offset * 0.28)
    elif category == "finance":
        base = 0.38 + (offset * 0.28)
    elif category == "politics":
        base = 0.28 + (offset * 0.44)

    if future_like:
        base = 0.42 + ((offset - 0.5) * 0.18)

    return max(0.15, min(0.85, base))


def _leading_direction(base_yes: float, future_like: bool) -> EvidenceDirection:
    if future_like and 0.42 <= base_yes <= 0.58:
        return EvidenceDirection.NEUTRAL
    if base_yes >= 0.55:
        return EvidenceDirection.SUPPORTS_YES
    if base_yes <= 0.45:
        return EvidenceDirection.SUPPORTS_NO
    return EvidenceDirection.NEUTRAL


def _opposite_direction(direction: EvidenceDirection) -> EvidenceDirection:
    if direction == EvidenceDirection.SUPPORTS_YES:
        return EvidenceDirection.SUPPORTS_NO
    if direction == EvidenceDirection.SUPPORTS_NO:
        return EvidenceDirection.SUPPORTS_YES
    return EvidenceDirection.NEUTRAL


def _clean_claim(claim: str) -> str:
    return re.sub(r"\s+", " ", claim.strip().rstrip("?.!")).strip()


def _evidence_item(
    *,
    item_id: str,
    source_type: SourceType,
    source_name: str,
    url: str,
    title: str,
    summary: str,
    raw_snippet: str,
    direction: EvidenceDirection,
    confidence: float,
    relevance: float,
    agent: str,
) -> EvidenceItem:
    weight = round(confidence * relevance, 4)
    return EvidenceItem(
        id=item_id,
        source_type=source_type,
        source_name=source_name,
        url=url,
        title=title,
        summary=summary,
        raw_snippet=raw_snippet,
        direction=direction,
        confidence=confidence,
        relevance=relevance,
        weight=weight,
        agent=agent,
    )


def _build_official_item(
    claim: str,
    category: str,
    lead: EvidenceDirection,
    future_like: bool,
) -> EvidenceItem:
    claim_text = _clean_claim(claim)
    if category == "sports":
        source_name = "FIFA / federation statement"
    elif category == "finance":
        source_name = "Official filing / IR"
    elif category == "politics":
        source_name = "Official record / authority"
    else:
        source_name = "Primary source record"

    if future_like:
        title = f"No official final record yet for: {claim_text}"
        summary = "Primary sources do not yet establish a definitive outcome."
        snippet = f"Official channels have not yet closed the record for '{claim_text}'."
        direction = EvidenceDirection.NEUTRAL
        relevance = 0.88
    elif lead == EvidenceDirection.SUPPORTS_YES:
        title = f"Primary source materially supports: {claim_text}"
        summary = "Official or documentary signals align with the claim."
        snippet = f"Primary-source material reviewed by the jury is broadly consistent with '{claim_text}'."
        direction = EvidenceDirection.SUPPORTS_YES
        relevance = 0.93
    else:
        title = f"No primary confirmation found for: {claim_text}"
        summary = "Official or documentary confirmation remains missing or incomplete."
        snippet = f"The strongest official records reviewed do not clearly confirm '{claim_text}'."
        direction = EvidenceDirection.SUPPORTS_NO
        relevance = 0.94

    return _evidence_item(
        item_id="sim_official_1",
        source_type=SourceType.OFFICIAL,
        source_name=source_name,
        url="https://example.com/official-record",
        title=title,
        summary=summary,
        raw_snippet=snippet,
        direction=direction,
        confidence=0.92,
        relevance=relevance,
        agent="SimulatedOfficialAgent",
    )


def _build_news_item(
    claim: str,
    category: str,
    lead: EvidenceDirection,
    future_like: bool,
) -> EvidenceItem:
    claim_text = _clean_claim(claim)
    source_name = {
        "sports": "Reuters Sports Desk",
        "finance": "Bloomberg / Reuters",
        "politics": "AP / Reuters",
        "product": "The Verge / company beat",
    }.get(category, "Major reporting")

    if future_like and category == "sports":
        direction = EvidenceDirection.SUPPORTS_YES if "brazil" in claim.lower() else EvidenceDirection.NEUTRAL
        title = f"Preview coverage frames contenders around: {claim_text}"
        summary = "Coverage suggests a plausible path, but nothing decisive yet."
        snippet = f"Preview reporting treats '{claim_text}' as a live possibility rather than a settled fact."
        relevance = 0.82
    elif lead == EvidenceDirection.SUPPORTS_YES:
        direction = EvidenceDirection.SUPPORTS_YES
        title = f"Reporting trend supports: {claim_text}"
        summary = "Major outlet reporting leans toward confirmation."
        snippet = f"Cross-checked reporting trends toward confirming '{claim_text}'."
        relevance = 0.88
    elif lead == EvidenceDirection.SUPPORTS_NO:
        direction = EvidenceDirection.SUPPORTS_NO
        title = f"Reporting trend disputes: {claim_text}"
        summary = "Major outlet reporting emphasizes missing proof or contrary signals."
        snippet = f"Cross-checked reporting highlights reasons to doubt '{claim_text}'."
        relevance = 0.89
    else:
        direction = EvidenceDirection.NEUTRAL
        title = f"Coverage remains mixed on: {claim_text}"
        summary = "Reporting is split and still leaves room for dispute."
        snippet = f"The current reporting record around '{claim_text}' remains mixed."
        relevance = 0.84

    return _evidence_item(
        item_id="sim_news_1",
        source_type=SourceType.NEWS,
        source_name=source_name,
        url="https://example.com/news-analysis",
        title=title,
        summary=summary,
        raw_snippet=snippet,
        direction=direction,
        confidence=0.82,
        relevance=relevance,
        agent="SimulatedNewsAgent",
    )


def _build_social_item(
    claim: str,
    category: str,
    direction: EvidenceDirection,
    future_like: bool,
) -> EvidenceItem:
    claim_text = _clean_claim(claim)
    if future_like:
        title = f"Speculative social chatter around: {claim_text}"
        summary = "Social discussion is active but mostly speculative."
        snippet = f"Online discussion treats '{claim_text}' as an open prediction rather than a settled result."
        relevance = 0.70
        resolved_direction = EvidenceDirection.SUPPORTS_YES if direction == EvidenceDirection.NEUTRAL else direction
    else:
        title = f"Social reaction contests the dominant reading of: {claim_text}"
        summary = "Posts amplify an alternative interpretation of the evidence."
        snippet = f"Social reactions around '{claim_text}' surface a minority but visible counter-narrative."
        relevance = 0.68
        resolved_direction = direction if direction != EvidenceDirection.NEUTRAL else EvidenceDirection.SUPPORTS_YES

    source_name = {
        "sports": "Fan / analyst X posts",
        "finance": "Trader commentary",
        "politics": "Political commentators",
        "product": "Tech community posts",
    }.get(category, "Community discussion")

    return _evidence_item(
        item_id="sim_social_1",
        source_type=SourceType.SOCIAL,
        source_name=source_name,
        url="https://x.com/",
        title=title,
        summary=summary,
        raw_snippet=snippet,
        direction=resolved_direction,
        confidence=0.44,
        relevance=relevance,
        agent="SimulatedSocialAgent",
    )


def _build_counter_item(
    claim: str,
    category: str,
    direction: EvidenceDirection,
    future_like: bool,
) -> EvidenceItem:
    claim_text = _clean_claim(claim)
    if future_like:
        title = f"Analysts warn the outcome is still unresolved: {claim_text}"
        summary = "Counter-evidence stresses variance, missing closure, or unresolved conditions."
        snippet = f"Analysts caution that '{claim_text}' cannot be resolved confidently yet."
        resolved_direction = EvidenceDirection.SUPPORTS_NO if direction == EvidenceDirection.NEUTRAL else direction
        relevance = 0.79
    else:
        title = f"Counter-evidence highlights ambiguity in: {claim_text}"
        summary = "The opposing side still has enough material to challenge a clean verdict."
        snippet = f"Counter-evidence suggests the record for '{claim_text}' still contains ambiguity."
        resolved_direction = direction if direction != EvidenceDirection.NEUTRAL else EvidenceDirection.SUPPORTS_NO
        relevance = 0.78

    source_name = {
        "sports": "Opta / analyst model",
        "finance": "Independent analyst note",
        "politics": "Legal commentary",
        "product": "Industry analysis",
    }.get(category, "Counter-evidence brief")

    return _evidence_item(
        item_id="sim_counter_1",
        source_type=SourceType.COUNTER,
        source_name=source_name,
        url="https://example.com/counter-evidence",
        title=title,
        summary=summary,
        raw_snippet=snippet,
        direction=resolved_direction,
        confidence=0.71,
        relevance=relevance,
        agent="SimulatedCounterAgent",
    )
