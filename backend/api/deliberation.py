from __future__ import annotations

import json

from backend.agents.defense_agent import DefenseAgent
from backend.agents.judge_agent import JudgeAgent
from backend.agents.prosecutor_agent import ProsecutorAgent
from backend.models import CaseFile, DeliberationResult
from backend.resolution.aggregation import aggregate_deliberation
from backend.resolution.bayesian import compute_bayesian_snapshot
from backend.resolution.resolution_generation import generate_resolution


def run_deliberation(case_file: CaseFile) -> DeliberationResult:
    prosecutor_argument = ProsecutorAgent().deliberate(case_file)
    defense_argument = DefenseAgent().deliberate(case_file)
    bayesian_snapshot = compute_bayesian_snapshot(case_file)
    aggregation_report = aggregate_deliberation(
        case_file=case_file,
        prosecutor_argument=prosecutor_argument,
        defense_argument=defense_argument,
        bayesian_snapshot=bayesian_snapshot,
    )
    judge_opinion = JudgeAgent().deliberate(
        case_file=case_file,
        bayesian_snapshot=bayesian_snapshot,
        aggregation_report=aggregation_report,
    )
    resolution = generate_resolution(
        case_file=case_file,
        bayesian_snapshot=bayesian_snapshot,
        aggregation_report=aggregation_report,
        judge_opinion=judge_opinion,
    )

    return DeliberationResult(
        case_id=case_file.case_id,
        prosecutor_argument=prosecutor_argument,
        defense_argument=defense_argument,
        bayesian_snapshot=bayesian_snapshot,
        aggregation_report=aggregation_report,
        judge_opinion=judge_opinion,
        resolution=resolution,
    )


def run_deliberation_from_dict(payload: dict) -> DeliberationResult:
    return run_deliberation(CaseFile.from_dict(payload))


def build_demo_case() -> CaseFile:
    return CaseFile.from_dict(
        {
            "case_id": "case-trump-hunter-biden-pardon",
            "question": "Did Trump pardon Hunter Biden before January 20?",
            "market_rule": "Resolve YES only if there is credible evidence of a formal pardon before Jan 20.",
            "evidence_pool": [
                {
                    "evidence_id": "official-001",
                    "title": "No official pardon listed in White House release",
                    "summary": "The official release archive reviewed by investigators did not list a pardon for Hunter Biden.",
                    "source_type": "official",
                    "stance": "no",
                    "credibility": 0.95,
                    "relevance": 0.95,
                    "freshness": 0.8,
                },
                {
                    "evidence_id": "news-001",
                    "title": "Major outlet reports no documented pardon",
                    "summary": "A major news report states there is no documentary evidence of a formal pardon before Jan 20.",
                    "source_type": "news",
                    "stance": "no",
                    "credibility": 0.82,
                    "relevance": 0.88,
                    "freshness": 0.75,
                },
                {
                    "evidence_id": "social-001",
                    "title": "Social post claims secret pardon exists",
                    "summary": "A viral post claims a pardon was signed privately but provides no primary document.",
                    "source_type": "social",
                    "stance": "yes",
                    "credibility": 0.25,
                    "relevance": 0.65,
                    "freshness": 0.7,
                },
                {
                    "evidence_id": "counter-001",
                    "title": "Legal commentator notes lack of filing trail",
                    "summary": "A legal expert argues a valid pardon would normally leave a documentary trail that has not surfaced.",
                    "source_type": "analysis",
                    "stance": "no",
                    "credibility": 0.7,
                    "relevance": 0.78,
                    "freshness": 0.65,
                },
            ],
            "human_votes": [
                {
                    "voter_id": "juror-1",
                    "stance": "no",
                    "confidence": 0.8,
                    "weight": 0.7,
                    "comment": "Official source absence matters most.",
                },
                {
                    "voter_id": "juror-2",
                    "stance": "yes",
                    "confidence": 0.4,
                    "weight": 0.5,
                    "comment": "Social rumors deserve investigation but are weak.",
                },
            ],
            "challenges": [
                {
                    "challenge_id": "challenge-1",
                    "target_stance": "no",
                    "summary": "Absence of a public record is not absolute proof that no pardon exists.",
                    "severity": 0.35,
                    "submitted_by": "juror-3",
                }
            ],
        }
    )


def main() -> None:
    result = run_deliberation(build_demo_case())
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
