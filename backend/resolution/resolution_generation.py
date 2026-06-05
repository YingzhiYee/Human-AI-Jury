from __future__ import annotations

from backend.models import (
    AggregationReport,
    BayesianSnapshot,
    CaseFile,
    JudgeOpinion,
    Resolution,
)


def generate_resolution(
    case_file: CaseFile,
    bayesian_snapshot: BayesianSnapshot,
    aggregation_report: AggregationReport,
    judge_opinion: JudgeOpinion,
) -> Resolution:
    summary = (
        f"{judge_opinion.verdict.value} with {round(judge_opinion.probability_yes * 100, 1)}% "
        f"YES probability and +/- {round(bayesian_snapshot.confidence_interval * 100, 1)}% uncertainty."
    )

    audit_trail = [
        f"Evidence YES strength: {bayesian_snapshot.evidence_yes_strength}",
        f"Evidence NO strength: {bayesian_snapshot.evidence_no_strength}",
        f"Human YES strength: {bayesian_snapshot.human_yes_strength}",
        f"Human NO strength: {bayesian_snapshot.human_no_strength}",
        f"Challenge pressure: {bayesian_snapshot.challenge_pressure}",
        *aggregation_report.notes,
        *judge_opinion.cautions,
    ]

    return Resolution(
        case_id=case_file.case_id,
        question=case_file.question,
        verdict=judge_opinion.verdict,
        probability_yes=judge_opinion.probability_yes,
        confidence_interval=bayesian_snapshot.confidence_interval,
        final_confidence=judge_opinion.final_confidence,
        summary=summary,
        rationale=judge_opinion.rationale,
        decisive_evidence_ids=aggregation_report.decisive_evidence_ids,
        audit_trail=audit_trail,
    )
