from __future__ import annotations

import re


def refine_direction_label(claim: str, text: str, direction: str) -> str:
    normalized = direction.strip().lower()
    if normalized in {"supports_yes", "supports_no"}:
        return normalized

    inferred = _infer_direction_from_text(claim, text)
    return inferred or "neutral"


def _infer_direction_from_text(claim: str, text: str) -> str | None:
    claim_lower = claim.lower()
    text_lower = text.lower()

    numeric_direction = _infer_numeric_threshold_direction(claim_lower, text_lower)
    if numeric_direction:
        return numeric_direction

    if "pardon" in claim_lower:
        if any(
            phrase in text_lower
            for phrase in (
                "did not pardon",
                "didn't pardon",
                "has not pardoned",
                "refused to pardon",
                "no pardon",
            )
        ):
            return "supports_no"
        if any(
            phrase in text_lower
            for phrase in ("pardoned", "did pardon", "has pardoned")
        ):
            return "supports_yes"

    if "win" in claim_lower and "world cup" in claim_lower:
        if any(
            phrase in text_lower
            for phrase in ("unlikely", "eliminated", "knocked out", "runner-up")
        ):
            return "supports_no"
        if any(
            phrase in text_lower
            for phrase in ("will win", "favorites", "champion", "winners")
        ):
            return "supports_yes"

    return None


def _infer_numeric_threshold_direction(claim_lower: str, text_lower: str) -> str | None:
    threshold = _extract_claim_threshold(claim_lower)
    if threshold is None:
        return None

    values = _extract_numeric_values(text_lower)
    if not values:
        return None

    max_value = max(values)
    min_value = min(values)

    positive_cues = (
        "target",
        "forecast",
        "predict",
        "predicted",
        "bull case",
        "bullish",
        "reach",
        "hit",
        "trade at",
        "trade above",
        "above",
        "higher",
        "surge to",
        "rally to",
    )
    negative_cues = (
        "unlikely",
        "won't",
        "will not",
        "crash",
        "drop",
        "fall",
        "bottom",
        "bear case",
        "below",
        "under",
    )

    if any(cue in text_lower for cue in positive_cues) and max_value >= threshold * 0.95:
        return "supports_yes"
    if any(cue in text_lower for cue in negative_cues) and min_value < threshold * 0.90:
        return "supports_no"
    if max_value >= threshold * 1.05:
        return "supports_yes"
    if max_value < threshold * 0.75:
        return "supports_no"
    return None


def _extract_claim_threshold(claim_lower: str) -> float | None:
    if not any(
        cue in claim_lower
        for cue in ("above", "over", "reach", "hit", "trade at", "trade above")
    ):
        return None

    values = _extract_numeric_values(claim_lower)
    if not values:
        return None
    return max(values)


def _extract_numeric_values(text: str) -> list[float]:
    pattern = re.compile(r"\$?\b(\d[\d,]*(?:\.\d+)?)\s*([kmb])?\b", re.IGNORECASE)
    values: list[float] = []
    for number, suffix in pattern.findall(text):
        value = float(number.replace(",", ""))
        suffix_lower = suffix.lower()
        if suffix_lower == "k":
            value *= 1_000
        elif suffix_lower == "m":
            value *= 1_000_000
        elif suffix_lower == "b":
            value *= 1_000_000_000
        values.append(value)
    return values
