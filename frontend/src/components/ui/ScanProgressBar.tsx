import { useState, useEffect } from "react";

interface Props {
  completed: number;
  total: number;
  remainingAnalyzers?: string[];
}

export default function ScanProgressBar({ completed, total, remainingAnalyzers = [] }: Props) {
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
      {remainingAnalyzers.length > 0 && (
        <ul className="scan-progress-remaining">
          {remainingAnalyzers.map((name) => (
            <li key={name} className="scan-progress-remaining-item">
              {name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
