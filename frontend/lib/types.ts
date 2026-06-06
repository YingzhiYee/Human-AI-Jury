export type Stance = "yes" | "no" | "neutral";

export interface HumanVoteInput {
  voter_id: string;
  stance: Stance;
  confidence: number;
  weight: number;
  comment: string;
}

export interface ChallengeInput {
  challenge_id: string;
  target_stance: Stance;
  summary: string;
  severity: number;
  submitted_by?: string;
}

export interface DemoRunRequest {
  market_id: string;
  claim: string;
  context: string;
  prior_yes: number;
  max_items_per_agent: number;
  human_votes: HumanVoteInput[];
  challenges: ChallengeInput[];
}

export interface EvidenceItem {
  id: string;
  source_type: string;
  source_name: string;
  url: string;
  title: string;
  summary: string;
  raw_snippet: string;
  direction: "supports_yes" | "supports_no" | "neutral";
  confidence: number;
  relevance: number;
  weight: number;
  published_at?: string | null;
  agent: string;
}

export interface EvidencePool {
  market_id: string;
  claim: string;
  items: EvidenceItem[];
  yes_weight: number;
  no_weight: number;
  total_items: number;
}

export interface Claim {
  statement: string;
  evidence_ids: string[];
  strength: number;
}

export interface AgentArgument {
  agent_name: string;
  stance: Stance;
  confidence: number;
  summary: string;
  claims: Claim[];
  counterpoints: string[];
  cited_evidence_ids: string[];
  weaknesses: string[];
}

export interface BayesianSnapshot {
  prior_yes: number;
  posterior_yes: number;
  evidence_yes_strength: number;
  evidence_no_strength: number;
  human_yes_strength: number;
  human_no_strength: number;
  challenge_pressure: number;
  disagreement: number;
  confidence_interval: number;
}

export interface AggregationReport {
  prosecutor_score: number;
  defense_score: number;
  leading_stance: Stance;
  conflict_level: number;
  decisive_evidence_ids: string[];
  notes: string[];
}

export interface JudgeOpinion {
  verdict: "YES" | "NO" | "INCONCLUSIVE";
  winning_stance: Stance;
  probability_yes: number;
  final_confidence: number;
  rationale: string;
  decisive_points: string[];
  cautions: string[];
}

export interface Resolution {
  case_id: string;
  question: string;
  verdict: "YES" | "NO" | "INCONCLUSIVE";
  probability_yes: number;
  confidence_interval: number;
  final_confidence: number;
  summary: string;
  rationale: string;
  decisive_evidence_ids: string[];
  audit_trail: string[];
}

export interface Deliberation {
  case_id: string;
  prosecutor_argument: AgentArgument;
  defense_argument: AgentArgument;
  bayesian_snapshot: BayesianSnapshot;
  aggregation_report: AggregationReport;
  judge_opinion: JudgeOpinion;
  resolution: Resolution;
}

export interface StoragePayload {
  case_id: string;
  verdict: string;
  confidence_bps: number;
  metadata_uri: string;
  canonical_json: string;
  contract_function: string;
}

export interface DemoRunResponse {
  case: DemoRunRequest;
  evidence_pool: EvidencePool;
  deliberation: Deliberation;
  storage_payload: StoragePayload;
}
