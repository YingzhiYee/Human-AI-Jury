import type { EvidencePool } from "../lib/types";

function directionLabel(direction: EvidencePool["items"][number]["direction"]) {
  if (direction === "supports_yes") {
    return "Supports YES";
  }
  if (direction === "supports_no") {
    return "Supports NO";
  }
  return "Neutral";
}

export function EvidenceBoard({
  evidencePool,
  compact = false,
}: {
  evidencePool: EvidencePool;
  compact?: boolean;
}) {
  return (
    <div className="evidence-board">
      <div className="metric-row">
        <article className="metric-card">
          <span>YES weight</span>
          <strong>{evidencePool.yes_weight.toFixed(2)}</strong>
        </article>
        <article className="metric-card">
          <span>NO weight</span>
          <strong>{evidencePool.no_weight.toFixed(2)}</strong>
        </article>
        <article className="metric-card">
          <span>Total items</span>
          <strong>{evidencePool.total_items}</strong>
        </article>
      </div>

      <div className={compact ? "evidence-list compact" : "evidence-list"}>
        {evidencePool.items.map((item) => (
          <article key={item.id} className="evidence-card">
            <div className="evidence-card-top">
              <span className={`badge ${item.direction}`}>{directionLabel(item.direction)}</span>
              <span className="source-tag">{item.source_name}</span>
            </div>
            <h3>{item.title}</h3>
            <p>{item.summary}</p>
            <div className="evidence-meta">
              <span>confidence {item.confidence.toFixed(2)}</span>
              <span>relevance {item.relevance.toFixed(2)}</span>
              <span>weight {item.weight.toFixed(2)}</span>
            </div>
            <a href={item.url} target="_blank" rel="noreferrer">
              Open source
            </a>
          </article>
        ))}
      </div>
    </div>
  );
}
