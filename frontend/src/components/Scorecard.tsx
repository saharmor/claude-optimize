import type { Scorecard as ScorecardType } from "../types/scan";
import { ANALYZER_LABELS } from "../types/scan";

interface Props {
  scorecard: ScorecardType;
  onJumpToFinding?: (category: string, title: string) => void;
  onShare?: () => void;
}

export default function Scorecard({ scorecard, onJumpToFinding, onShare }: Props) {
  if (scorecard.top_wins.length === 0) {
    return null;
  }

  return (
    <section className="top-wins" aria-labelledby="top-wins-title">
      <div className="section-intro">
        <h2 id="top-wins-title" className="section-subtitle">
         Highest-impact findings
        </h2>
        {onShare && (
          <button type="button" className="top-wins-share-btn" onClick={onShare}>
            Share results
          </button>
        )}
      </div>

      {scorecard.top_wins.map((win) => (
        <div key={`${win.category}:${win.title}`} className="top-win-item">
          <div className="top-win-main">
            <div className="top-win-category">{ANALYZER_LABELS[win.category]}</div>
            <div className="top-win-title">{win.title}</div>
          </div>
          <div className="top-win-right">
            <div className="top-win-savings">{win.estimated_savings}</div>
            {onJumpToFinding && (
              <button
                type="button"
                className="top-win-jump-btn"
                onClick={() => onJumpToFinding(win.category, win.title)}
                title="Jump to finding"
              >
                View &rarr;
              </button>
            )}
          </div>
        </div>
      ))}
    </section>
  );
}
