import { useState, useEffect } from "react";

interface Props {
  completed: number;
  total: number;
  runningAnalyzers?: string[];
  pendingAnalyzers?: string[];
}

export default function ScanProgressBar({ completed, total, runningAnalyzers = [], pendingAnalyzers = [] }: Props) {
  const realPercent = total > 0 ? Math.round((completed / total) * 100) : 0;
  const isDone = completed >= total;

  // Fake progress: start at 5%, bump to 8% after 3s so it never looks stuck
  const [fakePercent, setFakePercent] = useState(5);
  useEffect(() => {
    if (realPercent > 0 || isDone) return;
    const timer = setTimeout(() => setFakePercent(8), 3000);
    return () => clearTimeout(timer);
  }, [realPercent, isDone]);

  const displayPercent = isDone ? 100 : Math.max(realPercent, realPercent === 0 ? fakePercent : realPercent);

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
          {runningAnalyzers.length > 0 && (
            <p className="scan-progress-running">
              <span className="spinner scan-progress-spinner" aria-hidden="true" />
              Running {runningAnalyzers.join(", ")}
              {pendingAnalyzers.length > 0 && (
                <span className="scan-progress-pending">
                  {" "}— up next: {pendingAnalyzers.join(", ")}
                </span>
              )}
            </p>
          )}
          {runningAnalyzers.length === 0 && pendingAnalyzers.length > 0 && (
            <p className="scan-progress-running">
              Starting analyzers...
            </p>
          )}
          <p className="scan-progress-duration-note">
            Analysis can take up to 10 minutes for large projects
            {"Notification" in window && Notification.permission === "default" && (
              <span> (approve notifications to get notified when ready)</span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}
