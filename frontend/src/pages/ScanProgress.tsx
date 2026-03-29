import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getScanResult, subscribeScanStream } from "../api/client";
import type { AnalyzerType, AnalyzerStatus } from "../types/scan";
import { ALL_ANALYZERS, ANALYZER_LABELS, ANALYZER_ICONS } from "../types/scan";
import { PageIntro, StatCard, Surface } from "../components/ui";

function isAnalyzerType(value: unknown): value is AnalyzerType {
  return typeof value === "string" && ALL_ANALYZERS.includes(value as AnalyzerType);
}

export default function ScanProgress() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [statuses, setStatuses] = useState<Record<AnalyzerType, AnalyzerStatus>>(
    () =>
      Object.fromEntries(ALL_ANALYZERS.map((a) => [a, "pending"])) as Record<
        AnalyzerType,
        AnalyzerStatus
      >
  );
  const [findingCounts, setFindingCounts] = useState<Record<string, number>>({});
  const [streamError, setStreamError] = useState("");
  const completedCount = Object.values(statuses).filter(
    (status) => status === "completed"
  ).length;
  const failedCount = Object.values(statuses).filter(
    (status) => status === "failed"
  ).length;

  useEffect(() => {
    if (!scanId) return;

    const unsubscribe = subscribeScanStream(
      scanId,
      (event, data) => {
        const analyzer = data.analyzer;
        if (event === "analyzer_status" && isAnalyzerType(analyzer)) {
          const status = data.status;
          if (typeof status !== "string") {
            return;
          }
          setStatuses((prev) => ({
            ...prev,
            [analyzer]: status as AnalyzerStatus,
          }));
        }
        if (event === "analyzer_complete" && isAnalyzerType(analyzer)) {
          const findingCount = data.finding_count;
          setStatuses((prev) => ({
            ...prev,
            [analyzer]: "completed",
          }));
          if (typeof findingCount === "number") {
            setFindingCounts((prev) => ({
              ...prev,
              [analyzer]: findingCount,
            }));
          }
        }
        if (event === "analyzer_failed" && isAnalyzerType(analyzer)) {
          setStatuses((prev) => ({
            ...prev,
            [analyzer]: "failed",
          }));
        }
      },
      async () => {
        // Wait briefly for final state, then navigate to report
        await new Promise((r) => setTimeout(r, 1000));
        navigate(`/report/${scanId}`);
      },
      (message) => {
        setStreamError(message);
      }
    );

    // Also poll initial state
    getScanResult(scanId)
      .then((scan) => {
        if (scan.status === "completed" || scan.status === "failed") {
          navigate(`/report/${scanId}`);
        } else {
          setStatuses(scan.analyzer_statuses);
        }
      })
      .catch(() => {
        setStreamError("Could not load the initial scan state.");
      });

    return unsubscribe;
  }, [scanId, navigate]);

  return (
    <section className="progress-layout">
      <PageIntro
        eyebrow="Live scan"
        title="Analyzing your codebase"
        description="Claude Code is walking the project, reading the relevant files, and assembling a report in parallel."
        size="section"
      />

      <div className="progress-summary-grid">
        <StatCard value={completedCount} label="Completed analyzers" />
        <StatCard value={ALL_ANALYZERS.length} label="Total analyzers" />
        <StatCard value={failedCount} label="Failures" />
      </div>

      <Surface className="analyzer-list-surface">
        {ALL_ANALYZERS.map((analyzer) => {
          const status = statuses[analyzer];
          const count = findingCounts[analyzer];
          const isRunning = status === "running";

          return (
            <div key={analyzer} className={`analyzer-row ${status}`}>
              <div className={`analyzer-icon ${isRunning ? "running" : ""}`}>
                {isRunning ? (
                  <span className="spinner analyzer-spinner" aria-hidden="true" />
                ) : (
                  <span className="analyzer-icon-label">
                    {ANALYZER_ICONS[analyzer]}
                  </span>
                )}
              </div>
              <div className="analyzer-info">
                <div className="analyzer-name">
                  {ANALYZER_LABELS[analyzer]}
                </div>
                <div className="analyzer-status-text">
                  {status === "pending" && "Waiting..."}
                  {status === "running" && "Analyzing..."}
                  {status === "completed" &&
                    `${count ?? "?"} finding${count !== 1 ? "s" : ""} ready`}
                  {status === "failed" && "Failed"}
                </div>
              </div>
            </div>
          );
        })}
      </Surface>

      {streamError && <div className="error-message">{streamError}</div>}
    </section>
  );
}
