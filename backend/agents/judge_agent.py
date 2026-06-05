from __future__ import annotations

from backend.models import (
    AggregationReport,
    BayesianSnapshot,
    CaseFile,
    JudgeOpinion,
    Stance,
    Verdict,
    clamp,
)


class JudgeAgent:
    name = "Judge Agent"

    def deliberate(
        self,
        case_file: CaseFile,
        bayesian_snapshot: BayesianSnapshot,
        aggregation_report: AggregationReport,
    ) -> JudgeOpinion:
        probability_yes = bayesian_snapshot.posterior_yes
        if aggregation_report.leading_stance == Stance.YES and probability_yes >= 0.55:
            verdict = Verdict.YES
            winning_stance = Stance.YES
        elif aggregation_report.leading_stance == Stance.NO and probability_yes <= 0.45:
            verdict = Verdict.NO
            winning_stance = Stance.NO
        else:
            verdict = Verdict.INCONCLUSIVE
            winning_stance = Stance.NEUTRAL

        final_confidence = self._compute_final_confidence(
            bayesian_snapshot=bayesian_snapshot,
            aggregation_report=aggregation_report,
        )
        rationale = self._build_rationale(
            case_file=case_file,
            bayesian_snapshot=bayesian_snapshot,
            aggregation_report=aggregation_report,
            verdict=verdict,
        )
        decisive_points = self._build_decisive_points(
            bayesian_snapshot=bayesian_snapshot,
            aggregation_report=aggregation_report,
        )
        cautions = self._build_cautions(
            bayesian_snapshot=bayesian_snapshot,
            aggregation_report=aggregation_report,
        )

        return JudgeOpinion(
            verdict=verdict,
            winning_stance=winning_stance,
            probability_yes=round(probability_yes, 3),
            final_confidence=final_confidence,
            rationale=rationale,
            decisive_points=decisive_points,
            cautions=cautions,
        )

    def _compute_final_confidence(
        self,
        bayesian_snapshot: BayesianSnapshot,
        aggregation_report: AggregationReport,
    ) -> float:
        confidence = (
            1
            - bayesian_snapshot.confidence_interval
            - (aggregation_report.conflict_level * 0.20)
            - (bayesian_snapshot.challenge_pressure * 0.10)
        )
        return round(clamp(confidence, 0.05, 0.95), 3)

    def _build_rationale(
        self,
        case_file: CaseFile,
        bayesian_snapshot: BayesianSnapshot,
        aggregation_report: AggregationReport,
        verdict: Verdict,
    ) -> str:
        lead = aggregation_report.leading_stance.value.upper()
        probability = round(bayesian_snapshot.posterior_yes * 100, 1)
        return (
            f"{self.name} reviewed the adversarial arguments for '{case_file.question}' and found that "
            f"the current evidence balance leans {lead}. Bayesian aggregation estimates a YES probability "
            f"of {probability}%, leading to a {verdict.value} outcome."
        )

    def _build_decisive_points(
        self,
        bayesian_snapshot: BayesianSnapshot,
        aggregation_report: AggregationReport,
    ) -> list[str]:
        points = list(aggregation_report.notes)
        if bayesian_snapshot.evidence_yes_strength > bayesian_snapshot.evidence_no_strength:
            points.append("YES-side evidence currently carries more weighted credibility.")
        elif bayesian_snapshot.evidence_yes_strength < bayesian_snapshot.evidence_no_strength:
            points.append("NO-side evidence currently carries more weighted credibility.")
        else:
            points.append("Both sides have nearly balanced weighted evidence.")
        return points

    def _build_cautions(
        self,
        bayesian_snapshot: BayesianSnapshot,
        aggregation_report: AggregationReport,
    ) -> list[str]:
        cautions: list[str] = []
        if bayesian_snapshot.disagreement >= 0.6:
            cautions.append("High disagreement remains between credible evidence on both sides.")
        if bayesian_snapshot.challenge_pressure >= 0.4:
            cautions.append("Human challenges materially increase uncertainty in the current record.")
        if aggregation_report.leading_stance == Stance.NEUTRAL:
            cautions.append("No side achieved a decisive lead after aggregation.")
        return cautions
