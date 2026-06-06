import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchDefaultCase, runDemo } from "../lib/api";
import { useSession } from "../lib/session";
import type { DemoRunRequest } from "../lib/types";
import { EvidenceBoard } from "../evidence-page/EvidenceBoard";

const blankDraft: DemoRunRequest = {
  market_id: "pm_demo_001",
  claim: "",
  context: "",
  prior_yes: 0.5,
  max_items_per_agent: 4,
  human_votes: [],
  challenges: [],
};

export function CasePage() {
  const navigate = useNavigate();
  const { draft, setDraft, result, setResult } = useSession();
  const [form, setForm] = useState<DemoRunRequest>(draft ?? blankDraft);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (draft) {
      setForm(draft);
      return;
    }

    fetchDefaultCase()
      .then((defaultCase) => {
        setForm(defaultCase);
        setDraft(defaultCase);
      })
      .catch((reason) => {
        setError(reason instanceof Error ? reason.message : "Failed to load default case");
      });
  }, [draft, setDraft]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setDraft(form);

    try {
      const demoResult = await runDemo(form);
      setResult(demoResult);
      navigate("/debate");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Run failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel-stack">
      <div className="panel panel-form">
        <div className="panel-heading">
          <span className="panel-kicker">Case Intake</span>
          <h2>Define the disputed event</h2>
          <p>
            Start with the market claim, context, and prior belief. The run button
            triggers investigation plus the full deliberation engine.
          </p>
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            <span>Market ID</span>
            <input
              value={form.market_id}
              onChange={(event) => setForm({ ...form, market_id: event.target.value })}
            />
          </label>

          <label className="full-span">
            <span>Claim</span>
            <textarea
              rows={3}
              value={form.claim}
              onChange={(event) => setForm({ ...form, claim: event.target.value })}
            />
          </label>

          <label className="full-span">
            <span>Context / market rule</span>
            <textarea
              rows={4}
              value={form.context}
              onChange={(event) => setForm({ ...form, context: event.target.value })}
            />
          </label>

          <label>
            <span>Prior YES probability</span>
            <input
              type="number"
              min="0.01"
              max="0.99"
              step="0.01"
              value={form.prior_yes}
              onChange={(event) =>
                setForm({ ...form, prior_yes: Number(event.target.value) })
              }
            />
          </label>

          <label>
            <span>Max items / agent</span>
            <input
              type="number"
              min="1"
              max="20"
              step="1"
              value={form.max_items_per_agent}
              onChange={(event) =>
                setForm({ ...form, max_items_per_agent: Number(event.target.value) })
              }
            />
          </label>

          <div className="full-span action-row">
            <button type="submit" className="button-primary" disabled={loading}>
              {loading ? "Running jury pipeline..." : "Start Investigation"}
            </button>
            {error ? <p className="error-text">{error}</p> : null}
          </div>
        </form>
      </div>

      <div className="panel">
        <div className="panel-heading">
          <span className="panel-kicker">Current Snapshot</span>
          <h2>What the jury will work with</h2>
        </div>

        {result ? (
          <EvidenceBoard evidencePool={result.evidence_pool} compact />
        ) : (
          <div className="placeholder">
            Run the case once and the live evidence pool summary will appear here.
          </div>
        )}
      </div>
    </section>
  );
}
