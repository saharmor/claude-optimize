import { useState } from "react";
import type { Finding } from "../types/scan";
import CodeBlock from "./CodeBlock";
import { Pill } from "./ui";

interface Props {
  finding: Finding;
}

type Tab = "current" | "recommendation" | "fix";

const severityTone = {
  high: "accent",
  medium: "warning",
  low: "success",
} as const;

export default function FindingCard({ finding }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("current");

  return (
    <div className="finding-card">
      <div className="finding-header">
        <div className="finding-heading-group">
          <div className="finding-kicker">Finding</div>
          <div className="finding-title">{finding.recommendation.title}</div>
        </div>
        <div className="finding-badges">
          <Pill tone={severityTone[finding.impact.cost_reduction]} className="badge">
            Cost: {finding.impact.cost_reduction}
          </Pill>
          <Pill tone={severityTone[finding.confidence]} className="badge">
            {finding.confidence} confidence
          </Pill>
          <Pill tone={severityTone[finding.effort]} className="badge">
            {finding.effort} effort
          </Pill>
        </div>
      </div>

      <div className="finding-location">
        {finding.location.file}
        {finding.location.lines && `:${finding.location.lines}`}
        {finding.location.function && ` (${finding.location.function})`}
      </div>

      <div className="finding-tabs">
        <button
          type="button"
          className={`finding-tab ${activeTab === "current" ? "active" : ""}`}
          onClick={() => setActiveTab("current")}
        >
          Current State
        </button>
        <button
          type="button"
          className={`finding-tab ${activeTab === "recommendation" ? "active" : ""}`}
          onClick={() => setActiveTab("recommendation")}
        >
          Recommendation
        </button>
        <button
          type="button"
          className={`finding-tab ${activeTab === "fix" ? "active" : ""}`}
          onClick={() => setActiveTab("fix")}
        >
          Suggested Fix
        </button>
      </div>

      {activeTab === "current" && (
        <div className="finding-panel">
          <p className="finding-description">
            {finding.current_state.description}
          </p>
          <CodeBlock
            code={finding.current_state.code_snippet}
            language={finding.current_state.language}
          />
        </div>
      )}

      {activeTab === "recommendation" && (
        <div className="finding-panel">
          <p className="finding-description">
            {finding.recommendation.description}
          </p>

          <div className="impact-grid">
            <div className="impact-item">
              <div className="impact-label">Cost Reduction</div>
              <Pill tone={severityTone[finding.impact.cost_reduction]} className="badge">
                {finding.impact.cost_reduction}
              </Pill>
            </div>
            <div className="impact-item">
              <div className="impact-label">Latency Reduction</div>
              <Pill tone={severityTone[finding.impact.latency_reduction]} className="badge">
                {finding.impact.latency_reduction}
              </Pill>
            </div>
            <div className="impact-item">
              <div className="impact-label">Reliability</div>
              <Pill
                tone={severityTone[finding.impact.reliability_improvement]}
                className="badge"
              >
                {finding.impact.reliability_improvement}
              </Pill>
            </div>
          </div>

          {finding.impact.estimated_savings_detail && (
            <p className="finding-savings">
              {finding.impact.estimated_savings_detail}
            </p>
          )}

          {finding.recommendation.docs_url && (
            <a
              className="docs-link"
              href={finding.recommendation.docs_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Read the docs &rarr;
            </a>
          )}
        </div>
      )}

      {activeTab === "fix" && (
        <div className="finding-panel">
          <p className="finding-description">
            {finding.suggested_fix.description}
          </p>
          <CodeBlock
            code={finding.suggested_fix.code_snippet}
            language={finding.suggested_fix.language}
          />
        </div>
      )}
    </div>
  );
}
