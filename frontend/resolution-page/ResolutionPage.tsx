import { Link } from "react-router-dom";

import { useSession } from "../lib/session";
import { WalletPanel } from "../wallet/WalletPanel";

export function ResolutionPage() {
  const { result } = useSession();

  if (!result) {
    return (
      <section className="panel">
        <div className="placeholder">
          No verdict yet. Start from the <Link to="/">Case Page</Link>.
        </div>
      </section>
    );
  }

  const { resolution, judge_opinion } = result.deliberation;

  return (
    <section className="panel-stack">
      <div className="split-layout">
        <article className="panel verdict-panel">
          <div className="panel-heading">
            <span className="panel-kicker">Judge Agent</span>
            <h2>{resolution.verdict}</h2>
            <p>{resolution.summary}</p>
          </div>
          <div className="verdict-grid">
            <div>
              <span>YES probability</span>
              <strong>{Math.round(resolution.probability_yes * 100)}%</strong>
            </div>
            <div>
              <span>Uncertainty</span>
              <strong>{Math.round(resolution.confidence_interval * 100)}%</strong>
            </div>
            <div>
              <span>Final confidence</span>
              <strong>{Math.round(resolution.final_confidence * 100)}%</strong>
            </div>
          </div>
          <p className="rationale-block">{judge_opinion.rationale}</p>
        </article>

        <WalletPanel />
      </div>

      <div className="split-layout">
        <article className="panel">
          <div className="panel-heading">
            <span className="panel-kicker">Decisive Evidence</span>
            <h2>Why the jury ruled this way</h2>
          </div>
          <ul className="card-list">
            {judge_opinion.decisive_points.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <span className="panel-kicker">Audit Trail</span>
            <h2>Transparent storage payload</h2>
          </div>
          <pre className="json-block">{result.storage_payload.canonical_json}</pre>
        </article>
      </div>
    </section>
  );
}
