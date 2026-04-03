import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getScanHistory, type ScanHistoryItem } from "../api/client";

function formatDuration(ms: number | null): string {
  if (ms === null) return "-";
  if (ms < 1000) return `${ms}ms`;
  const secs = Math.round(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = secs % 60;
  return `${mins}m ${remSecs}s`;
}

function formatTime(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString();
}

function statusBadge(status: string) {
  const cls =
    status === "completed"
      ? "history-badge history-badge-success"
      : status === "failed"
        ? "history-badge history-badge-error"
        : "history-badge history-badge-running";
  return <span className={cls}>{status}</span>;
}

function projectLabel(path: string, repoName: string | null): string {
  if (repoName) return repoName;
  const parts = path.replace(/\/$/, "").split("/");
  return parts[parts.length - 1] || path;
}

export default function History() {
  const navigate = useNavigate();
  const [scans, setScans] = useState<ScanHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getScanHistory();
      setScans(res.scans);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="history-container">
      <header className="page-header-block">
        <button className="back-button" onClick={() => navigate("/")}>
          &larr; Back
        </button>
        <h1 className="page-title">Run History</h1>
        <p className="page-lede">
          {total > 0
            ? `${total} audit${total !== 1 ? "s" : ""} across your projects.`
            : "Past audits across all projects."}
        </p>
      </header>

      {loading && <p className="history-loading">Loading...</p>}
      {error && <p className="history-error">{error}</p>}

      {!loading && !error && (
        <div className="history-list">
          {scans.length === 0 ? (
            <p className="history-empty">No audits yet. Run your first audit from the home page.</p>
          ) : (
            scans.map((scan) => (
              <button
                key={scan.scan_id}
                className="history-card"
                onClick={() => navigate(`/report/${scan.scan_id}`)}
              >
                <div className="history-card-header">
                  <span className="history-card-project">
                    {projectLabel(scan.project_path, scan.repo_name)}
                  </span>
                  {statusBadge(scan.status)}
                  {scan.scan_mode === "demo" && (
                    <span className="history-badge history-badge-demo">demo</span>
                  )}
                </div>

                {scan.project_summary?.one_liner && (
                  <div className="history-card-meta">
                    <span className="history-card-summary">{scan.project_summary.one_liner}</span>
                  </div>
                )}

                <div className="history-card-stats">
                  <span>{scan.findings_count} finding{scan.findings_count !== 1 ? "s" : ""}</span>
                  <span>{formatDuration(scan.duration_ms)}</span>
                  {scan.git_branch && <span className="history-card-branch">{scan.git_branch}</span>}
                  <span className="history-card-time">{formatTime(scan.started_at)}</span>
                </div>

                {scan.apply && (
                  <div className="history-card-apply">
                    {scan.apply.status === "completed" && (
                      <span className="history-badge history-badge-applied">
                        {scan.apply.selection_count} applied
                      </span>
                    )}
                    {scan.apply.status === "running" && (
                      <span className="history-badge history-badge-running">applying...</span>
                    )}
                    {scan.apply.status === "failed" && (
                      <span className="history-badge history-badge-error">apply failed</span>
                    )}
                    {scan.apply.pr_url && (
                      <a
                        href={scan.apply.pr_url}
                        target="_blank"
                        rel="noreferrer"
                        className="history-card-pr-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        View PR
                      </a>
                    )}
                    {scan.apply.pr_error && !scan.apply.pr_url && (
                      <span className="history-card-pr-error">PR failed</span>
                    )}
                  </div>
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
