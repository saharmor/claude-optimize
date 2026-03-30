import { useState, useEffect, useRef } from "react";
import type { Finding } from "../types/scan";
import CodeBlock from "./CodeBlock";

interface Props {
  finding: Finding;
  projectPath: string;
  focusKey?: string | null;
  isSelected?: boolean;
  onToggle?: () => void;
}

function buildEditorUrl(
  editor: "cursor" | "vscode",
  projectPath: string,
  file: string,
  lines: string
): string {
  const scheme = editor === "cursor" ? "cursor" : "vscode";
  const absolutePath = file.startsWith("/")
    ? file
    : `${projectPath}/${file}`;
  const line = lines ? lines.split("-")[0] : "1";
  return `${scheme}://file${encodeURI(absolutePath)}:${line}`;
}

export default function FindingCard({ finding, projectPath, focusKey, isSelected, onToggle }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [showMetricsHelp, setShowMetricsHelp] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showMetricsHelp) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowMetricsHelp(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [showMetricsHelp]);

  const findingKey = `${finding.category}:${finding.recommendation.title}`;
  const lastHandledFocusKey = useRef<string | null>(null);

  useEffect(() => {
    if (focusKey && focusKey === findingKey && lastHandledFocusKey.current !== focusKey) {
      lastHandledFocusKey.current = focusKey;
      setExpanded(true);
      const timer = setTimeout(() => {
        cardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [focusKey, findingKey]);

  // Reset handled key when focusKey changes to something else, allowing re-trigger
  useEffect(() => {
    if (focusKey !== findingKey) {
      lastHandledFocusKey.current = null;
    }
  }, [focusKey, findingKey]);


  return (
    <div className="finding-card" ref={cardRef}>
      <button
        type="button"
        className="finding-collapsed-row"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="finding-collapsed-left">
          {onToggle && (
            <div className="finding-checkbox-wrapper">
              <input
                type="checkbox"
                className="finding-checkbox"
                checked={!!isSelected}
                onChange={() => onToggle()}
                onClick={(e) => e.stopPropagation()}
                aria-label={`Select "${finding.recommendation.title}"`}
              />
            </div>
          )}
          <div className="finding-collapsed-left-text">
            <div className="finding-title">{finding.recommendation.title}</div>
            <div className="finding-collapsed-impact">
              <div className="finding-impact-row finding-impact-row--compact">
                <span className="finding-impact-item">
                  Cost saving <strong className={`impact-${finding.impact.cost_reduction}`}>{finding.impact.cost_reduction}</strong>
                </span>
                <span className="finding-impact-item">
                  Latency reduction <strong className={`impact-${finding.impact.latency_reduction}`}>{finding.impact.latency_reduction}</strong>
                </span>
                <span className="finding-impact-item">
                  Stability improvement <strong className={`impact-${finding.impact.reliability_improvement}`}>{finding.impact.reliability_improvement}</strong>
                </span>
                <span className="finding-impact-item">
                  Effort <strong className={`effort-${finding.effort}`}>{finding.effort}</strong>
                </span>
                <span className="finding-impact-item">
                  Confidence <strong className={`confidence-${finding.confidence}`}>{finding.confidence}</strong>
                </span>
                <span
                  role="button"
                  tabIndex={0}
                  className="metrics-help-btn"
                  onClick={(e) => { e.stopPropagation(); setShowMetricsHelp(true); }}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); e.preventDefault(); setShowMetricsHelp(true); } }}
                  aria-label="What do these metrics mean?"
                >
                  ?
                </span>
              </div>
              {finding.impact.estimated_savings_detail && (
                <p className="finding-savings finding-savings--compact">
                  {finding.impact.estimated_savings_detail}
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="finding-collapsed-right">
          <a
            className="finding-open-btn"
            href={buildEditorUrl("cursor", projectPath, finding.location.file, finding.location.lines)}
            onClick={(e) => e.stopPropagation()}
            title="Open in Cursor"
          >
            Open file
          </a>
          <span className={`chevron ${expanded ? "open" : ""}`} />
        </div>
      </button>

      {showMetricsHelp && (
        <div className="metrics-modal-backdrop" onClick={() => setShowMetricsHelp(false)} role="dialog" aria-modal="true" aria-labelledby="metrics-modal-title">
          <div className="metrics-modal" onClick={(e) => e.stopPropagation()}>
            <div className="metrics-modal-header">
              <h3 id="metrics-modal-title" className="metrics-modal-title">Understanding metrics</h3>
              <button
                type="button"
                className="metrics-modal-close"
                onClick={() => setShowMetricsHelp(false)}
              >
                &times;
              </button>
            </div>
            <dl className="metrics-modal-list">
              <div className="metrics-modal-item">
                <dt>Cost saving</dt>
                <dd>How much this change could reduce your API spend. <em>Higher is better.</em></dd>
              </div>
              <div className="metrics-modal-item">
                <dt>Latency reduction</dt>
                <dd>Expected reduction in response time and round-trips. <em>Higher is better.</em></dd>
              </div>
              <div className="metrics-modal-item">
                <dt>Stability improvement</dt>
                <dd>Improvement in output consistency: fewer retries and malformed responses. <em>Higher is better.</em></dd>
              </div>
              <div className="metrics-modal-item">
                <dt>Effort</dt>
                <dd>How much work is needed to implement this change. <em>Lower is better.</em></dd>
              </div>
              <div className="metrics-modal-item">
                <dt>Confidence</dt>
                <dd>How confident we are this recommendation applies correctly to your code. <em>Higher is better.</em></dd>
              </div>
            </dl>
          </div>
        </div>
      )}

      {expanded && (
        <div className="finding-expanded">
          <div className="finding-section">
            <div className="finding-section-label">Current code</div>
            <p className="finding-description">
              {finding.current_state.description}
            </p>
            <CodeBlock
              code={finding.current_state.code_snippet}
              language={finding.current_state.language}
            />
          </div>

          <div className="finding-section">
            <div className="finding-section-label">Recommendation</div>
            <p className="finding-description">
              {finding.recommendation.description}
            </p>
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
            {finding.suggested_fix.code_snippet && (
              <CodeBlock
                code={finding.suggested_fix.code_snippet}
                language={finding.suggested_fix.language}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
