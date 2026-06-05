from __future__ import annotations

import math

from backend.models import BayesianSnapshot, CaseFile, Stance, evidence_weight, vote_weight


def compute_bayesian_snapshot(case_file: CaseFile) -> BayesianSnapshot:
    prior_yes = case_file.prior_yes
    log_odds = math.log(prior_yes / (1 - prior_yes))

    evidence_yes_strength = 0.0
    evidence_no_strength = 0.0

    for evidence in case_file.evidence_pool:
        strength = evidence_weight(evidence)
        if evidence.stance == Stance.YES:
            evidence_yes_strength += strength
            log_odds += strength * 1.6
        elif evidence.stance == Stance.NO:
            evidence_no_strength += strength
            log_odds -= strength * 1.6

    human_yes_strength = 0.0
    human_no_strength = 0.0

    for vote in case_file.human_votes:
        strength = vote_weight(vote)
        if vote.stance == Stance.YES:
            human_yes_strength += strength
            log_odds += strength * 0.8
        elif vote.stance == Stance.NO:
            human_no_strength += strength
            log_odds -= strength * 0.8

    challenge_pressure = sum(item.severity for item in case_file.challenges)
    for challenge in case_file.challenges:
        if challenge.target_stance == Stance.YES:
            log_odds -= challenge.severity * 0.35
        elif challenge.target_stance == Stance.NO:
            log_odds += challenge.severity * 0.35

    posterior_yes = 1 / (1 + math.exp(-log_odds))
    disagreement = _compute_disagreement(
        evidence_yes_strength=evidence_yes_strength + human_yes_strength,
        evidence_no_strength=evidence_no_strength + human_no_strength,
    )
    confidence_interval = _compute_confidence_interval(
        evidence_count=len(case_file.evidence_pool),
        human_signal_count=len(case_file.human_votes) + len(case_file.challenges),
        disagreement=disagreement,
        challenge_pressure=challenge_pressure,
    )

    return BayesianSnapshot(
        prior_yes=round(prior_yes, 3),
        posterior_yes=round(posterior_yes, 3),
        evidence_yes_strength=round(evidence_yes_strength, 3),
        evidence_no_strength=round(evidence_no_strength, 3),
        human_yes_strength=round(human_yes_strength, 3),
        human_no_strength=round(human_no_strength, 3),
        challenge_pressure=round(challenge_pressure, 3),
        disagreement=round(disagreement, 3),
        confidence_interval=round(confidence_interval, 3),
    )


def _compute_disagreement(
    evidence_yes_strength: float,
    evidence_no_strength: float,
) -> float:
    total = evidence_yes_strength + evidence_no_strength
    if total == 0:
        return 1.0

    balance = min(evidence_yes_strength, evidence_no_strength) / max(
        evidence_yes_strength,
        evidence_no_strength,
    )
    return min(1.0, balance)


def _compute_confidence_interval(
    evidence_count: int,
    human_signal_count: int,
    disagreement: float,
    challenge_pressure: float,
) -> float:
    uncertainty = 0.22
    uncertainty -= min(0.10, evidence_count * 0.015)
    uncertainty -= min(0.04, human_signal_count * 0.008)
    uncertainty += disagreement * 0.10
    uncertainty += min(0.06, challenge_pressure * 0.03)
    return max(0.05, min(0.30, uncertainty))
