from __future__ import annotations

from backend.models import (
    AgentArgument,
    AggregationReport,
    BayesianSnapshot,
    CaseFile,
    Stance,
    evidence_weight,
)


def aggregate_deliberation(
    case_file: CaseFile,
    prosecutor_argument: AgentArgument,
    defense_argument: AgentArgument,
    bayesian_snapshot: BayesianSnapshot,
) -> AggregationReport:
    prosecutor_score = round(
        (prosecutor_argument.confidence * 0.45) + (bayesian_snapshot.posterior_yes * 0.55),
        3,
    )
    defense_score = round(
        (defense_argument.confidence * 0.45) + ((1 - bayesian_snapshot.posterior_yes) * 0.55),
        3,
    )

    score_gap = abs(prosecutor_score - defense_score)
    if score_gap < 0.05:
        leading_stance = Stance.NEUTRAL
    elif prosecutor_score > defense_score:
        leading_stance = Stance.YES
    else:
        leading_stance = Stance.NO

    conflict_level = round(min(1.0, bayesian_snapshot.disagreement + (0.05 - min(score_gap, 0.05))), 3)
    decisive_evidence_ids = _select_decisive_evidence(case_file, leading_stance)
    notes = _build_notes(
        bayesian_snapshot=bayesian_snapshot,
        prosecutor_score=prosecutor_score,
        defense_score=defense_score,
        leading_stance=leading_stance,
    )

    return AggregationReport(
        prosecutor_score=prosecutor_score,
        defense_score=defense_score,
        leading_stance=leading_stance,
        conflict_level=conflict_level,
        decisive_evidence_ids=decisive_evidence_ids,
        notes=notes,
    )


def _select_decisive_evidence(case_file: CaseFile, leading_stance: Stance) -> list[str]:
    if leading_stance == Stance.NEUTRAL:
        return []

    decisive = sorted(
        [item for item in case_file.evidence_pool if item.stance == leading_stance],
        key=evidence_weight,
        reverse=True,
    )
    return [item.evidence_id for item in decisive[:3]]


def _build_notes(
    bayesian_snapshot: BayesianSnapshot,
    prosecutor_score: float,
    defense_score: float,
    leading_stance: Stance,
) -> list[str]:
    notes = [
        f"Prosecutor composite score: {prosecutor_score}",
        f"Defense composite score: {defense_score}",
    ]
    if leading_stance == Stance.YES:
        notes.append("Combined argument quality and evidence weighting currently favor YES.")
    elif leading_stance == Stance.NO:
        notes.append("Combined argument quality and evidence weighting currently favor NO.")
    else:
        notes.append("Neither side established a decisive lead after aggregation.")

    if bayesian_snapshot.human_yes_strength > bayesian_snapshot.human_no_strength:
        notes.append("Human jury input slightly leans YES.")
    elif bayesian_snapshot.human_yes_strength < bayesian_snapshot.human_no_strength:
        notes.append("Human jury input slightly leans NO.")
    else:
        notes.append("Human jury input is balanced or absent.")

    return notes
