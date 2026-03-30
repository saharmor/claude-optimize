import { useEffect, useRef, useState } from "react";
import { subscribeApplyStream } from "../api/client";
import type { Finding } from "../types/scan";
import { ANALYZER_LABELS } from "../types/scan";

interface Props {
  applyId: string;
  projectPath: string;
  findings: Finding[];
  onBack: () => void;
  onRetry: () => void;
  onShare: () => void;
}

export default function ApplyProgress({ applyId, projectPath, findings, onBack, onRetry, onShare }: Props) {
  const [outputLines, setOutputLines] = useState<string[]>([]);
  const [status, setStatus] = useState<"running" | "completed" | "failed">("running");
  const [error, setError] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unsubscribe = subscribeApplyStream(
      applyId,
      (line) => {
        setOutputLines((prev) => [...prev, line]);
      },
      () => {
        setStatus("completed");
      },
      (err) => {
        setStatus("failed");
        setError(err);
      }
    );

    return unsubscribe;
  }, [applyId]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [outputLines]);

  const cursorUrl = `cursor://file${encodeURI(projectPath)}`;
  const vscodeUrl = `vscode://file${encodeURI(projectPath)}`;
  const started = outputLines.length > 0;

  return (
    <div className="apply-progress">
      <div className="apply-progress-header">
        {status === "running" && (
          <>
            <span className="spinner apply-progress-spinner" aria-hidden="true" />
            <h2 className="apply-progress-title">Applying optimizations...</h2>
          </>
        )}
        {status === "completed" && (
          <h2 className="apply-progress-title apply-progress-title-done">
            Optimizations applied
          </h2>
        )}
        {status === "failed" && (
          <h2 className="apply-progress-title apply-progress-title-failed">
            Apply failed
          </h2>
        )}
      </div>

      {findings.length > 0 && (
        <div className="apply-findings-list">
          {findings.map((f, i) => {
            let rowStatus: "pending" | "applying" | "done" | "failed";
            if (status === "completed") rowStatus = "done";
            else if (status === "failed") rowStatus = "failed";
            else if (started) rowStatus = "applying";
            else rowStatus = "pending";

            return (
              <div key={i} className={`apply-finding-row apply-finding-row-${rowStatus}`}>
                <span className="apply-finding-status">
                  {rowStatus === "done" && <span className="apply-finding-icon-done">&#10003;</span>}
                  {rowStatus === "applying" && <span className="spinner apply-finding-spinner" aria-hidden="true" />}
                  {rowStatus === "failed" && <span className="apply-finding-icon-failed">&#10007;</span>}
                  {rowStatus === "pending" && <span className="apply-finding-icon-pending" />}
                </span>
                <div className="apply-finding-info">
                  <span className="apply-finding-title">{f.recommendation.title}</span>
                  <span className="apply-finding-category">{ANALYZER_LABELS[f.category]}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {outputLines.length > 0 && (
        <div className="apply-output-log" ref={logRef}>
          {outputLines.map((line, i) => (
            <div key={i} className="apply-output-line">{line || "\u00A0"}</div>
          ))}
        </div>
      )}

      {status === "running" && outputLines.length === 0 && (
        <div className="apply-progress-waiting">
          <span className="spinner" aria-hidden="true" />
          <p>Waiting for Claude Code to apply fixes...</p>
        </div>
      )}

      {status === "failed" && error && (
        <div className="apply-error-message">{error}</div>
      )}

      <div className="apply-progress-actions">
        {status === "completed" && (
          <div className="apply-complete-actions">
            <p className="apply-complete-hint">
              Open the project in your editor to review and commit the changes.
            </p>
            <div className="apply-complete-buttons">
              <a href={cursorUrl} className="apply-open-btn apply-open-btn-primary">
                Open in Cursor
              </a>
              <a href={vscodeUrl} className="apply-open-btn">
                Open in VS Code
              </a>
            </div>
            <div className="apply-share-cta">
              <p className="apply-share-text">
                Nice work! Help other developers discover what they could optimize.
              </p>
              <button type="button" className="apply-open-btn" onClick={onShare}>
                Spread the Word
              </button>
            </div>
          </div>
        )}
        {status === "failed" && (
          <button type="button" className="apply-retry-btn" onClick={onRetry}>
            Try again
          </button>
        )}
        <button type="button" className="apply-back-link" onClick={onBack}>
          &larr; Back to report
        </button>
      </div>
    </div>
  );
}
