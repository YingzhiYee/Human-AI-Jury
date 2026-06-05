from __future__ import annotations

from dataclasses import dataclass

from backend.models import (
    AgentArgument,
    CaseFile,
    Claim,
    Evidence,
    Stance,
    evidence_weight,
    opposite_stance,
)


@dataclass(slots=True)
class DeliberationAgent:
    name: str
    stance: Stance
    top_supporting_evidence: int = 3
    top_opposing_evidence: int = 2

    def deliberate(self, case_file: CaseFile) -> AgentArgument:
        supporting = self._select_evidence(case_file, self.stance, self.top_supporting_evidence)
        opposing = self._select_evidence(
            case_file,
            opposite_stance(self.stance),
            self.top_opposing_evidence,
        )
        claims = [self._build_claim(item) for item in supporting]
        confidence = self._compute_confidence(supporting, opposing)
        cited_evidence_ids = [item.evidence_id for item in supporting + opposing]

        return AgentArgument(
            agent_name=self.name,
            stance=self.stance,
            confidence=confidence,
            summary=self._build_summary(case_file, supporting, opposing),
            claims=claims,
            counterpoints=[self._build_counterpoint(item) for item in opposing],
            cited_evidence_ids=cited_evidence_ids,
            weaknesses=[self._build_weakness(item) for item in opposing],
        )

    def _select_evidence(
        self,
        case_file: CaseFile,
        stance: Stance,
        limit: int,
    ) -> list[Evidence]:
        ranked = sorted(
            [item for item in case_file.evidence_pool if item.stance == stance],
            key=evidence_weight,
            reverse=True,
        )
        return ranked[:limit]

    def _build_claim(self, evidence: Evidence) -> Claim:
        strength = round(evidence_weight(evidence), 3)
        statement = f"{evidence.title}: {evidence.summary}"
        return Claim(
            statement=statement,
            evidence_ids=[evidence.evidence_id],
            strength=strength,
        )

    def _build_counterpoint(self, evidence: Evidence) -> str:
        return f"Opposing evidence '{evidence.title}' could weaken this side because {evidence.summary}"

    def _build_weakness(self, evidence: Evidence) -> str:
        return f"Must address {evidence.source_type} evidence '{evidence.title}'."

    def _build_summary(
        self,
        case_file: CaseFile,
        supporting: list[Evidence],
        opposing: list[Evidence],
    ) -> str:
        if not supporting:
            return f"{self.name} found insufficient direct evidence to argue {self.stance.value.upper()} for '{case_file.question}'."

        top_support = supporting[0]
        summary = (
            f"{self.name} argues {self.stance.value.upper()} based on "
            f"{len(supporting)} primary evidence items, led by '{top_support.title}'."
        )
        if opposing:
            summary += f" The strongest challenge comes from '{opposing[0].title}'."
        return summary

    def _compute_confidence(
        self,
        supporting: list[Evidence],
        opposing: list[Evidence],
    ) -> float:
        support_score = sum(evidence_weight(item) for item in supporting)
        opposing_score = sum(evidence_weight(item) for item in opposing)
        raw_score = 0.5 + ((support_score - (opposing_score * 0.65)) / 4.0)
        return round(max(0.05, min(0.95, raw_score)), 3)
