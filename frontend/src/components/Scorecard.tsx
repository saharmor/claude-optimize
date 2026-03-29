import type { Scorecard as ScorecardType } from "../types/scan";
import { ANALYZER_LABELS } from "../types/scan";
import { PageIntro, Pill, StatCard } from "./ui";

interface Props {
  scorecard: ScorecardType;
}

export default function Scorecard({ scorecard }: Props) {
  const categoryEntries = Object.entries(scorecard.by_category);

  return (
    <section className="scorecard-section">
      <PageIntro
        eyebrow="At a glance"
        title="What stands out in this scan"
        description="A compact summary of volume, impact, and category coverage before you dive into individual findings."
        size="subsection"
        className="section-intro"
      />

      <div className="scorecard">
        <StatCard value={scorecard.total_findings} label="Total findings" />
        <StatCard value={scorecard.by_impact.high ?? 0} label="High impact" />
        <StatCard value={categoryEntries.length} label="Active categories" />
        <StatCard
          value={scorecard.estimated_total_savings || "N/A"}
          label="Estimated savings"
          valueClassName="scorecard-value-text"
        />
      </div>

      {categoryEntries.length > 0 && (
        <div className="category-breakdown">
          {categoryEntries.map(([category, count]) => (
            <Pill key={category} tone="neutral" className="category-chip">
              <span className="category-chip-label">
                {ANALYZER_LABELS[category as keyof typeof ANALYZER_LABELS]}
              </span>
              <span className="category-chip-count">{count}</span>
            </Pill>
          ))}
        </div>
      )}

      {scorecard.top_wins.length > 0 && (
        <div className="top-wins">
          <PageIntro
            eyebrow="Top wins"
            title="Highest leverage changes"
            description="The strongest recommendations surfaced by the report builder."
            size="subsection"
            className="section-intro"
          />

          {scorecard.top_wins.map((win) => (
            <div key={`${win.category}:${win.title}`} className="top-win-item">
              <div className="top-win-main">
                <div className="top-win-category">
                  {ANALYZER_LABELS[win.category]}
                </div>
                <div className="top-win-title">{win.title}</div>
              </div>
              <div className="top-win-savings">{win.estimated_savings}</div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
