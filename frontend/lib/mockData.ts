import type {
  AgentArgument,
  BayesianSnapshot,
  DemoRunRequest,
  DemoRunResponse,
  EvidenceItem,
  Stance,
} from "./types";

export const defaultDemoCase: DemoRunRequest = {
  market_id: "pm_demo_001",
  claim: "Did Trump pardon Hunter Biden before January 20?",
  context:
    "Resolve YES only if credible official or documentary evidence of a pardon exists before Jan 20.",
  prior_yes: 0.5,
  max_items_per_agent: 4,
  human_votes: [],
  challenges: [],
};

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function hashClaim(claim: string) {
  let hash = 0;
  for (let index = 0; index < claim.length; index += 1) {
    hash = (hash * 31 + claim.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function detectCategory(claim: string) {
  const lowered = claim.toLowerCase();
  if (["world cup", "fifa", "match", "win", "champion", "team", "final"].some((token) => lowered.includes(token))) {
    return "sports";
  }
  if (["pardon", "court", "president", "senate", "election", "law", "minister"].some((token) => lowered.includes(token))) {
    return "politics";
  }
  if (["ipo", "earnings", "etf", "approval", "funding", "acquisition", "listed"].some((token) => lowered.includes(token))) {
    return "finance";
  }
  if (["release", "launch", "ship", "rollout", "model", "app", "product"].some((token) => lowered.includes(token))) {
    return "product";
  }
  return "generic";
}

function isFutureLike(claim: string) {
  const lowered = ` ${claim.toLowerCase()} `;
  return [" will ", "this year", "next year", "tomorrow", "今年", "明年", "会不会", "是否会", "in 2026", "in 2027"].some(
    (token) => lowered.includes(token),
  );
}

function baseYesProbability(claim: string, category: string, futureLike: boolean) {
  const offset = (hashClaim(claim) % 1000) / 1000;
  let base = 0.3 + offset * 0.4;

  if (category === "sports") {
    base = 0.34 + offset * 0.28;
  } else if (category === "finance") {
    base = 0.38 + offset * 0.28;
  } else if (category === "politics") {
    base = 0.28 + offset * 0.44;
  }

  if (futureLike) {
    base = 0.42 + (offset - 0.5) * 0.18;
  }

  return clamp(base, 0.15, 0.85);
}

function leadingStance(probabilityYes: number, futureLike: boolean): Stance {
  if (futureLike && probabilityYes >= 0.42 && probabilityYes <= 0.58) {
    return "neutral";
  }
  if (probabilityYes >= 0.55) {
    return "yes";
  }
  if (probabilityYes <= 0.45) {
    return "no";
  }
  return "neutral";
}

function oppositeStance(stance: Stance): Stance {
  if (stance === "yes") return "no";
  if (stance === "no") return "yes";
  return "neutral";
}

function cleanClaim(claim: string) {
  return claim.trim().replace(/[?.!]+$/u, "");
}

function evidenceWeight(item: EvidenceItem) {
  return item.weight;
}

function makeEvidence(
  id: string,
  sourceType: EvidenceItem["source_type"],
  sourceName: string,
  url: string,
  title: string,
  summary: string,
  rawSnippet: string,
  direction: EvidenceItem["direction"],
  confidence: number,
  relevance: number,
  agent: string,
): EvidenceItem {
  return {
    id,
    source_type: sourceType,
    source_name: sourceName,
    url,
    title,
    summary,
    raw_snippet: rawSnippet,
    direction,
    confidence,
    relevance,
    weight: Number((confidence * relevance).toFixed(4)),
    published_at: null,
    agent,
  };
}

function buildEvidenceItems(payload: DemoRunRequest): EvidenceItem[] {
  const claim = cleanClaim(payload.claim);
  const category = detectCategory(claim);
  const futureLike = isFutureLike(claim);
  const lead = leadingStance(baseYesProbability(claim, category, futureLike), futureLike);
  const opposite = oppositeStance(lead);

  const officialSource =
    category === "sports"
      ? "FIFA / federation statement"
      : category === "finance"
        ? "Official filing / IR"
        : category === "politics"
          ? "Official record / authority"
          : "Primary source record";

  const officialDirection =
    futureLike ? "neutral" : lead === "yes" ? "supports_yes" : "supports_no";
  const officialTitle =
    futureLike
      ? `No official final record yet for: ${claim}`
      : lead === "yes"
        ? `Primary source materially supports: ${claim}`
        : `No primary confirmation found for: ${claim}`;
  const officialSummary =
    futureLike
      ? "Primary sources do not yet establish a definitive outcome."
      : lead === "yes"
        ? "Official or documentary signals align with the claim."
        : "Official or documentary confirmation remains missing or incomplete.";

  const newsDirection =
    futureLike && category === "sports"
      ? claim.toLowerCase().includes("brazil")
        ? "supports_yes"
        : "neutral"
      : lead === "yes"
        ? "supports_yes"
        : lead === "no"
          ? "supports_no"
          : "neutral";
  const newsTitle =
    futureLike && category === "sports"
      ? `Preview coverage frames contenders around: ${claim}`
      : lead === "yes"
        ? `Reporting trend supports: ${claim}`
        : lead === "no"
          ? `Reporting trend disputes: ${claim}`
          : `Coverage remains mixed on: ${claim}`;
  const newsSummary =
    futureLike && category === "sports"
      ? "Coverage suggests a plausible path, but nothing decisive yet."
      : lead === "yes"
        ? "Major outlet reporting leans toward confirmation."
        : lead === "no"
          ? "Major outlet reporting emphasizes missing proof or contrary signals."
          : "Reporting is split and still leaves room for dispute.";

  const socialLead = futureLike ? (opposite === "neutral" ? "yes" : opposite) : opposite === "neutral" ? "yes" : opposite;
  const counterLead = futureLike ? (opposite === "neutral" ? "no" : opposite) : opposite === "neutral" ? "no" : opposite;

  return [
    makeEvidence(
      "sim_official_1",
      "official",
      officialSource,
      "https://example.com/official-record",
      officialTitle,
      officialSummary,
      `Primary-source review for "${claim}" is being used as the highest-trust record.`,
      officialDirection,
      0.92,
      futureLike ? 0.88 : lead === "yes" ? 0.93 : 0.94,
      "SimulatedOfficialAgent",
    ),
    makeEvidence(
      "sim_news_1",
      "news",
      category === "sports" ? "Reuters Sports Desk" : category === "finance" ? "Bloomberg / Reuters" : category === "politics" ? "AP / Reuters" : "Major reporting",
      "https://example.com/news-analysis",
      newsTitle,
      newsSummary,
      `Reporting around "${claim}" remains part of the jury record.`,
      newsDirection,
      0.82,
      futureLike && category === "sports" ? 0.82 : lead === "neutral" ? 0.84 : 0.89,
      "SimulatedNewsAgent",
    ),
    makeEvidence(
      "sim_social_1",
      "social",
      category === "sports" ? "Fan / analyst X posts" : category === "finance" ? "Trader commentary" : category === "politics" ? "Political commentators" : "Community discussion",
      "https://x.com/",
      futureLike ? `Speculative social chatter around: ${claim}` : `Social reaction contests the dominant reading of: ${claim}`,
      futureLike
        ? "Social discussion is active but mostly speculative."
        : "Posts amplify an alternative interpretation of the evidence.",
      `Online chatter around "${claim}" is visible, but lower-trust than documentary evidence.`,
      socialLead === "yes" ? "supports_yes" : socialLead === "no" ? "supports_no" : "neutral",
      0.44,
      futureLike ? 0.7 : 0.68,
      "SimulatedSocialAgent",
    ),
    makeEvidence(
      "sim_counter_1",
      "counter",
      category === "sports" ? "Opta / analyst model" : category === "finance" ? "Independent analyst note" : category === "politics" ? "Legal commentary" : "Counter-evidence brief",
      "https://example.com/counter-evidence",
      futureLike ? `Analysts warn the outcome is still unresolved: ${claim}` : `Counter-evidence highlights ambiguity in: ${claim}`,
      futureLike
        ? "Counter-evidence stresses variance, missing closure, or unresolved conditions."
        : "The opposing side still has enough material to challenge a clean verdict.",
      `Analyst pushback means "${claim}" is still contestable.`,
      counterLead === "yes" ? "supports_yes" : counterLead === "no" ? "supports_no" : "neutral",
      0.71,
      futureLike ? 0.79 : 0.78,
      "SimulatedCounterAgent",
    ),
  ];
}

function buildArgument(
  agentName: string,
  stance: Stance,
  items: EvidenceItem[],
): AgentArgument {
  const supportingDirection = stance === "yes" ? "supports_yes" : "supports_no";
  const opposingDirection = stance === "yes" ? "supports_no" : "supports_yes";
  const supporting = items
    .filter((item) => item.direction === supportingDirection)
    .sort((left, right) => evidenceWeight(right) - evidenceWeight(left));
  const opposing = items
    .filter((item) => item.direction === opposingDirection)
    .sort((left, right) => evidenceWeight(right) - evidenceWeight(left));

  const supportScore = supporting.reduce((sum, item) => sum + evidenceWeight(item), 0);
  const opposingScore = opposing.reduce((sum, item) => sum + evidenceWeight(item), 0);
  const confidence = clamp(0.5 + (supportScore - opposingScore * 0.65) / 4, 0.05, 0.95);

  return {
    agent_name: agentName,
    stance,
    confidence: Number(confidence.toFixed(3)),
    summary:
      supporting.length > 0
        ? `${agentName} argues ${stance.toUpperCase()} using ${supporting.length} stronger evidence items.`
        : `${agentName} found limited direct evidence for ${stance.toUpperCase()}.`,
    claims: supporting.map((item) => ({
      statement: `${item.title}: ${item.summary}`,
      evidence_ids: [item.id],
      strength: Number(item.weight.toFixed(2)),
    })),
    counterpoints: opposing.map(
      (item) => `Opposing evidence '${item.title}' challenges this side because ${item.summary}`,
    ),
    cited_evidence_ids: [...supporting, ...opposing].map((item) => item.id),
    weaknesses: opposing.map((item) => `Must answer '${item.title}'.`),
  };
}

function buildBayesianSnapshot(payload: DemoRunRequest, items: EvidenceItem[]): BayesianSnapshot {
  const evidenceYes = items
    .filter((item) => item.direction === "supports_yes")
    .reduce((sum, item) => sum + item.weight, 0);
  const evidenceNo = items
    .filter((item) => item.direction === "supports_no")
    .reduce((sum, item) => sum + item.weight, 0);
  const humanYes = payload.human_votes
    .filter((vote) => vote.stance === "yes")
    .reduce((sum, vote) => sum + vote.confidence * vote.weight, 0);
  const humanNo = payload.human_votes
    .filter((vote) => vote.stance === "no")
    .reduce((sum, vote) => sum + vote.confidence * vote.weight, 0);
  const challengePressure = payload.challenges.reduce((sum, challenge) => sum + challenge.severity, 0);
  const total = evidenceYes + evidenceNo + humanYes + humanNo;
  const posteriorYes = total > 0 ? (evidenceYes + humanYes + payload.prior_yes) / (total + 1) : payload.prior_yes;
  const disagreement =
    total > 0 ? Math.min(evidenceYes + humanYes, evidenceNo + humanNo) / Math.max(evidenceYes + humanYes, evidenceNo + humanNo, 0.01) : 1;
  const confidenceInterval = clamp(0.22 - items.length * 0.015 + disagreement * 0.1 + challengePressure * 0.03, 0.05, 0.3);

  return {
    prior_yes: Number(payload.prior_yes.toFixed(3)),
    posterior_yes: Number(posteriorYes.toFixed(3)),
    evidence_yes_strength: Number(evidenceYes.toFixed(3)),
    evidence_no_strength: Number(evidenceNo.toFixed(3)),
    human_yes_strength: Number(humanYes.toFixed(3)),
    human_no_strength: Number(humanNo.toFixed(3)),
    challenge_pressure: Number(challengePressure.toFixed(3)),
    disagreement: Number(disagreement.toFixed(3)),
    confidence_interval: Number(confidenceInterval.toFixed(3)),
  };
}

export function buildMockRunResponse(payload: DemoRunRequest): DemoRunResponse {
  const items = buildEvidenceItems(payload);
  const evidenceYes = items
    .filter((item) => item.direction === "supports_yes")
    .reduce((sum, item) => sum + item.weight, 0);
  const evidenceNo = items
    .filter((item) => item.direction === "supports_no")
    .reduce((sum, item) => sum + item.weight, 0);
  const prosecutor = buildArgument("Prosecutor Agent", "yes", items);
  const defense = buildArgument("Defense Agent", "no", items);
  const bayesian = buildBayesianSnapshot(payload, items);
  const scoreYes = prosecutor.confidence * 0.45 + bayesian.posterior_yes * 0.55;
  const scoreNo = defense.confidence * 0.45 + (1 - bayesian.posterior_yes) * 0.55;
  const leading = scoreYes > scoreNo + 0.05 ? "yes" : scoreNo > scoreYes + 0.05 ? "no" : "neutral";
  const verdict =
    leading === "yes" && bayesian.posterior_yes >= 0.55
      ? "YES"
      : leading === "no" && bayesian.posterior_yes <= 0.45
        ? "NO"
        : "INCONCLUSIVE";
  const finalConfidence = clamp(
    1 - bayesian.confidence_interval - Math.abs(scoreYes - scoreNo) * 0.1 - bayesian.challenge_pressure * 0.1,
    0.05,
    0.95,
  );

  const summary =
    verdict === "INCONCLUSIVE"
      ? `INCONCLUSIVE with ${Math.round(bayesian.posterior_yes * 100)}% YES probability and +/- ${Math.round(bayesian.confidence_interval * 100)}% uncertainty.`
      : `${verdict} with ${Math.round(bayesian.posterior_yes * 100)}% YES probability and +/- ${Math.round(bayesian.confidence_interval * 100)}% uncertainty.`;

  const canonicalJson = JSON.stringify(
    {
      caseId: payload.market_id,
      question: payload.claim,
      verdict,
      probabilityYes: bayesian.posterior_yes,
      confidenceInterval: bayesian.confidence_interval,
      finalConfidence,
      decisiveEvidenceIds: items
        .sort((left, right) => right.weight - left.weight)
        .slice(0, 3)
        .map((item) => item.id),
    },
    null,
    0,
  );

  return {
    mode: "simulated-local",
    notices: [
      "Frontend is using local simulated evidence because the backend API was unavailable.",
      "This run is claim-aware and dynamic, but it is still simulation mode rather than live external evidence mode.",
    ],
    case: payload,
    evidence_pool: {
      market_id: payload.market_id,
      claim: payload.claim,
      items,
      yes_weight: Number(evidenceYes.toFixed(2)),
      no_weight: Number(evidenceNo.toFixed(2)),
      total_items: items.length,
    },
    deliberation: {
      case_id: payload.market_id,
      prosecutor_argument: prosecutor,
      defense_argument: defense,
      bayesian_snapshot: bayesian,
      aggregation_report: {
        prosecutor_score: Number(scoreYes.toFixed(3)),
        defense_score: Number(scoreNo.toFixed(3)),
        leading_stance: leading,
        conflict_level: Number(
          clamp(bayesian.disagreement + (0.05 - Math.min(Math.abs(scoreYes - scoreNo), 0.05)), 0, 1).toFixed(3),
        ),
        decisive_evidence_ids: items
          .sort((left, right) => right.weight - left.weight)
          .slice(0, 3)
          .map((item) => item.id),
        notes: [
          `Prosecutor composite score: ${scoreYes.toFixed(3)}`,
          `Defense composite score: ${scoreNo.toFixed(3)}`,
          leading === "neutral"
            ? "Neither side established a decisive lead after aggregation."
            : `Combined argument quality and evidence weighting currently favor ${leading.toUpperCase()}.`,
        ],
      },
      judge_opinion: {
        verdict,
        winning_stance: verdict === "YES" ? "yes" : verdict === "NO" ? "no" : "neutral",
        probability_yes: bayesian.posterior_yes,
        final_confidence: Number(finalConfidence.toFixed(3)),
        rationale:
          verdict === "INCONCLUSIVE"
            ? `The current record for '${payload.claim}' remains contested, so the jury cannot issue a decisive verdict yet.`
            : `The current record for '${payload.claim}' leans ${verdict}, based on the weighted balance of documentary, reporting, social, and counter evidence.`,
        decisive_points: items
          .sort((left, right) => right.weight - left.weight)
          .slice(0, 3)
          .map((item) => `${item.title}: ${item.summary}`),
        cautions:
          verdict === "INCONCLUSIVE"
            ? ["More primary evidence is needed before resolving this market confidently."]
            : ["This run is simulated because live backend evidence was unavailable."],
      },
      resolution: {
        case_id: payload.market_id,
        question: payload.claim,
        verdict,
        probability_yes: bayesian.posterior_yes,
        confidence_interval: bayesian.confidence_interval,
        final_confidence: Number(finalConfidence.toFixed(3)),
        summary,
        rationale:
          verdict === "INCONCLUSIVE"
            ? "The case remains open because the available signals are mixed or premature."
            : `The jury currently resolves this case as ${verdict}.`,
        decisive_evidence_ids: items
          .sort((left, right) => right.weight - left.weight)
          .slice(0, 3)
          .map((item) => item.id),
        audit_trail: [
          `Evidence YES strength: ${evidenceYes.toFixed(3)}`,
          `Evidence NO strength: ${evidenceNo.toFixed(3)}`,
          `Human YES strength: ${bayesian.human_yes_strength}`,
          `Human NO strength: ${bayesian.human_no_strength}`,
          `Challenge pressure: ${bayesian.challenge_pressure}`,
        ],
      },
    },
    storage_payload: {
      case_id: payload.market_id,
      verdict,
      confidence_bps: Math.round(finalConfidence * 10000),
      metadata_uri: "",
      canonical_json: canonicalJson,
      contract_function: "storeResolution",
    },
  };
}
