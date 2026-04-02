import { useState, useEffect } from "react";

export interface AnalyzerGroupInfo {
  label: string;
  analyzers: { name: string; status: "pending" | "running" | "completed" | "failed" }[];
}

interface Props {
  completed: number;
  total: number;
  runningAnalyzers?: string[];
  groups?: AnalyzerGroupInfo[];
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function ScanProgressBar({ completed, total, runningAnalyzers = [], groups }: Props) {
  const realPercent = total > 0 ? Math.round((completed / total) * 100) : 0;
  const isDone = completed >= total;
  const anyRunning = runningAnalyzers.length > 0;

  // Fake progress: start at 5%, bump to 8% after 3s so it never looks stuck
  const [fakePercent, setFakePercent] = useState(5);
  useEffect(() => {
    if (realPercent > 0 || isDone) return;
    const timer = setTimeout(() => setFakePercent(8), 3000);
    return () => clearTimeout(timer);
  }, [realPercent, isDone]);

  const displayPercent = isDone ? 100 : realPercent === 0 ? fakePercent : realPercent;

  return (
    <div className="scan-progress">
      <div className="scan-progress-header">
        <span className="scan-progress-label">
          {isDone
            ? "All analyzers complete"
            : `${completed} of ${total} analyzers complete`}
        </span>
        <span className={`scan-progress-percent${isDone ? " done" : ""}`}>
          {displayPercent}%
        </span>
      </div>
      <div className="scan-progress-track">
        <div
          className={`scan-progress-fill${!isDone ? " active" : " done"}`}
          style={{ width: `${displayPercent}%` }}
        />
      </div>
      {!isDone && (
        <div className="scan-progress-status">
          <p className="scan-progress-running">
            <span className="spinner scan-progress-spinner" aria-hidden="true" />
            {anyRunning ? "Analyzing your project..." : "Starting analyzers..."}
          </p>

          <p className="scan-progress-duration-note">
            Analysis can take up to 10 minutes for large projects
            {"Notification" in window && Notification.permission === "default" && (
              <span> (approve notifications to get notified when ready)</span>
            )}
          </p>

          {groups && groups.length > 0 && (
            <div className="scan-progress-groups">
              {groups.map((group) => {
                const groupCompleted = group.analyzers.filter(
                  (a) => a.status === "completed"
                ).length;
                const groupTotal = group.analyzers.length;
                const groupDone = groupCompleted === groupTotal;
                return (
                  <div key={group.label} className={`scan-progress-group${groupDone ? " scan-progress-group--done" : ""}`}>
                    <div className="scan-progress-group-header">
                      <span className="scan-progress-group-label">{group.label}</span>
                      <span className="scan-progress-group-count">
                        {groupCompleted}/{groupTotal}
                      </span>
                    </div>
                    <div className="scan-progress-group-analyzers">
                      {group.analyzers.map((analyzer) => (
                        <span
                          key={analyzer.name}
                          className={`scan-progress-analyzer-item scan-progress-analyzer-item--${analyzer.status}`}
                        >
                          {analyzer.status === "completed" ? (
                            <span className="scan-progress-analyzer-check" aria-hidden="true">
                              <CheckIcon />
                            </span>
                          ) : (
                            <span
                              className={`scan-progress-analyzer-dot scan-progress-analyzer-dot--${analyzer.status}`}
                              aria-hidden="true"
                            />
                          )}
                          {analyzer.name}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
