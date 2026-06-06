import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { runDemo } from "../lib/api";
import { useSession } from "../lib/session";
import type { ChallengeInput, HumanVoteInput } from "../lib/types";
import { EvidenceBoard } from "../evidence-page/EvidenceBoard";

const defaultVote: HumanVoteInput = {
  voter_id: "juror-demo",
  stance: "no",
  confidence: 0.7,
  weight: 0.8,
  comment: "",
};

const defaultChallenge: ChallengeInput = {
  challenge_id: "challenge-demo",
  target_stance: "yes",
  summary: "",
  severity: 0.4,
  submitted_by: "juror-demo",
};

export function DebatePage() {
  const navigate = useNavigate();
  const { draft, result, setResult, setDraft } = useSession();
  const [vote, setVote] = useState<HumanVoteInput>(defaultVote);
  const [challenge, setChallenge] = useState<ChallengeInput>(defaultChallenge);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!draft || !result) {
    return (
      <section className="panel">
        <div className="placeholder">
          No active case yet. Go back to <Link to="/">Case Page</Link> and run the
          pipeline first.
        </div>
      </section>
    );
  }

  const currentDraft = draft;

  async function rerunDebate() {
    setLoading(true);
    setError(null);

    const nextDraft = {
      market_id: currentDraft.market_id,
      claim: currentDraft.claim,
      context: currentDraft.context,
      prior_yes: currentDraft.prior_yes,
      max_items_per_agent: currentDraft.max_items_per_agent,
      human_votes: vote.comment ? [vote] : [],
      challenges: challenge.summary ? [challenge] : [],
    };

    setDraft(nextDraft);

    try {
      const nextResult = await runDemo(nextDraft);
      setResult(nextResult);
      navigate("/resolution");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to rerun debate");
    } finally {
      setLoading(false);
    }
  }

  const { prosecutor_argument, defense_argument, bayesian_snapshot } = result.deliberation;

  return (
    <section className="panel-stack">
      <div className="split-layout">
        <article className="panel side-yes">
          <div className="panel-heading">
            <span className="panel-kicker">Prosecutor Agent</span>
            <h2>YES Case</h2>
            <p>{prosecutor_argument.summary}</p>
          </div>
          <p className="score-line">
            Confidence {Math.round(prosecutor_argument.confidence * 100)}%
          </p>
          <ul className="card-list">
            {prosecutor_argument.claims.map((claim) => (
              <li key={claim.statement}>
                <strong>{claim.statement}</strong>
                <span>Strength {claim.strength.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel side-no">
          <div className="panel-heading">
            <span className="panel-kicker">Defense Agent</span>
            <h2>NO Case</h2>
            <p>{defense_argument.summary}</p>
          </div>
          <p className="score-line">
            Confidence {Math.round(defense_argument.confidence * 100)}%
          </p>
          <ul className="card-list">
            {defense_argument.claims.map((claim) => (
              <li key={claim.statement}>
                <strong>{claim.statement}</strong>
                <span>Strength {claim.strength.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </article>
      </div>

      <div className="split-layout">
        <div className="panel">
          <div className="panel-heading">
            <span className="panel-kicker">Human Jury</span>
            <h2>Challenge the agents</h2>
            <p>
              Add one juror vote and one challenge, then rerun the pipeline to see
              how the verdict shifts.
            </p>
          </div>

          <div className="form-grid">
            <label>
              <span>Juror stance</span>
              <select
                value={vote.stance}
                onChange={(event) => setVote({ ...vote, stance: event.target.value as HumanVoteInput["stance"] })}
              >
                <option value="yes">YES</option>
                <option value="no">NO</option>
                <option value="neutral">Neutral</option>
              </select>
            </label>

            <label>
              <span>Juror confidence</span>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={vote.confidence}
                onChange={(event) => setVote({ ...vote, confidence: Number(event.target.value) })}
              />
            </label>

            <label className="full-span">
              <span>Juror comment</span>
              <textarea
                rows={3}
                value={vote.comment}
                onChange={(event) => setVote({ ...vote, comment: event.target.value })}
                placeholder="Explain why you agree or disagree with the current evidence balance."
              />
            </label>

            <label>
              <span>Challenge target</span>
              <select
                value={challenge.target_stance}
                onChange={(event) =>
                  setChallenge({
                    ...challenge,
                    target_stance: event.target.value as ChallengeInput["target_stance"],
                  })
                }
              >
                <option value="yes">Challenge YES</option>
                <option value="no">Challenge NO</option>
                <option value="neutral">Challenge both</option>
              </select>
            </label>

            <label>
              <span>Challenge severity</span>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={challenge.severity}
                onChange={(event) =>
                  setChallenge({ ...challenge, severity: Number(event.target.value) })
                }
              />
            </label>

            <label className="full-span">
              <span>Challenge summary</span>
              <textarea
                rows={3}
                value={challenge.summary}
                onChange={(event) => setChallenge({ ...challenge, summary: event.target.value })}
                placeholder="Point out a gap, ambiguity, or credibility problem in the evidence."
              />
            </label>

            <div className="full-span action-row">
              <button type="button" className="button-primary" onClick={rerunDebate} disabled={loading}>
                {loading ? "Re-running deliberation..." : "Apply Human Input"}
              </button>
              {error ? <p className="error-text">{error}</p> : null}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <span className="panel-kicker">Evidence Pool</span>
            <h2>Live record</h2>
            <p>
              Bayesian snapshot: YES probability{" "}
              {Math.round(bayesian_snapshot.posterior_yes * 100)}%, uncertainty{" "}
              {Math.round(bayesian_snapshot.confidence_interval * 100)}%.
            </p>
          </div>
          <EvidenceBoard evidencePool={result.evidence_pool} />
        </div>
      </div>
    </section>
  );
}
