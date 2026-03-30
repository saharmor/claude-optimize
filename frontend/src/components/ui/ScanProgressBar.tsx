interface Props {
  completed: number;
  total: number;
  remainingAnalyzers?: string[];
}

export default function ScanProgressBar({ completed, total, remainingAnalyzers = [] }: Props) {
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  const isDone = completed >= total;

  return (
    <div className="scan-progress">
      <div className="scan-progress-header">
        <span className="scan-progress-label">
          {isDone
            ? "All analyzers complete"
            : `${completed} of ${total} analyzers complete`}
        </span>
        <span className={`scan-progress-percent${isDone ? " done" : ""}`}>
          {percent}%
        </span>
      </div>
      <div className="scan-progress-track">
        <div
          className={`scan-progress-fill${!isDone ? " active" : " done"}`}
          style={{ width: `${percent}%` }}
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
