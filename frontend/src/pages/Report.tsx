import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getScanResult, subscribeScanStream } from "../api/client";
import type { ScanResult, AnalyzerType, AnalyzerStatus, Finding } from "../types/scan";
import { ALL_ANALYZERS, ANALYZER_LABELS } from "../types/scan";
import { getFindingKey } from "../utils/findingKey";
import { generatePrompt } from "../utils/generatePrompt";
import Scorecard from "../components/Scorecard";
import AnalyzerSection from "../components/AnalyzerSection";
import SelectionBar from "../components/SelectionBar";
import PromptModal from "../components/PromptModal";
import { Button, EmptyState, ScanProgressBar, Surface } from "../components/ui";

const SEVERITY_ORDER: Record<string, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

function formatProjectName(projectPath: string): string {
  const folderName = projectPath.split(/[\\/]/).filter(Boolean).pop() ?? projectPath;
  const words = folderName.split(/[_-]+/).filter(Boolean);

  if (words.length === 0) {
    return folderName;
  }

  return words
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function isAnalyzerType(value: unknown): value is AnalyzerType {
  return typeof value === "string" && ALL_ANALYZERS.includes(value as AnalyzerType);
}

function isStatusValue(value: unknown): value is AnalyzerStatus {
  return (
    value === "pending" ||
    value === "running" ||
    value === "completed" ||
    value === "failed"
  );
}

export default function Report() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [streamError, setStreamError] = useState("");
  const [streamComplete, setStreamComplete] = useState(false);
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const handleJumpToFinding = useCallback((category: string, title: string) => {
    setFocusKey(`${category}:${title}`);
  }, []);

  const toggleFinding = useCallback((key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedKeys(new Set());
  }, []);

  const handleGeneratePrompt = useCallback(() => {
    setShowPromptModal(true);
  }, []);

  useEffect(() => {
    if (!scanId) return;

    let cancelled = false;

    const refreshScan = async () => {
      try {
        const result = await getScanResult(scanId);
        if (cancelled) {
          return;
        }

        setScan(result);
        setError("");
        const summaryDone =
          result.project_summary_status === "completed" ||
          result.project_summary_status === "failed";
        setStreamComplete(
          (result.status === "completed" || result.status === "failed") && summaryDone
        );
      } catch (err) {
        if (cancelled) {
          return;
        }
        setError(
          err instanceof Error ? err.message : "Failed to fetch optimization audit result"
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void refreshScan();

    const unsubscribe = subscribeScanStream(
      scanId,
      (event, data) => {
        if (cancelled) {
          return;
        }

        const analyzer = data.analyzer;

        if (
          event === "analyzer_status" &&
          isAnalyzerType(analyzer) &&
          isStatusValue(data.status)
        ) {
          setScan((prev) =>
            prev
              ? {
                  ...prev,
                  analyzer_statuses: {
                    ...prev.analyzer_statuses,
                    [analyzer]: data.status,
                  },
                }
              : prev
          );
          return;
        }

        if (event === "analyzer_complete" && isAnalyzerType(analyzer)) {
          setScan((prev) =>
            prev
              ? {
                  ...prev,
                  analyzer_statuses: {
                    ...prev.analyzer_statuses,
                    [analyzer]: "completed",
                  },
                }
              : prev
          );
          void refreshScan();
          return;
        }

        if (event === "analyzer_failed" && isAnalyzerType(analyzer)) {
          const analyzerError =
            typeof data.error === "string" ? data.error : "Analyzer failed";
          setScan((prev) =>
            prev
              ? {
                  ...prev,
                  analyzer_statuses: {
                    ...prev.analyzer_statuses,
                    [analyzer]: "failed",
                  },
                  analyzer_errors: {
                    ...prev.analyzer_errors,
                    [analyzer]: analyzerError,
                  },
                }
              : prev
          );
          void refreshScan();
          return;
        }

        const summaryStatus = data.status;
        if (event === "project_summary_status" && isStatusValue(summaryStatus)) {
          setScan((prev) =>
            prev
              ? {
                  ...prev,
                  project_summary_status: summaryStatus,
                }
              : prev
          );
          return;
        }

        const oneLiner = data.one_liner;
        const description = data.description;
        if (
          event === "project_summary_complete" &&
          typeof oneLiner === "string" &&
          typeof description === "string"
        ) {
          setScan((prev) =>
            prev
              ? {
                  ...prev,
                  project_summary_status: "completed",
                  project_summary: {
                    one_liner: oneLiner,
                    description,
                  },
                  project_summary_error: null,
                }
              : prev
          );
          return;
        }

        if (event === "project_summary_failed") {
          const summaryError = typeof data.error === "string" ? data.error : "";
          setScan((prev) =>
            prev
              ? {
                  ...prev,
                  project_summary_status: "failed",
                  project_summary_error: summaryError,
                }
              : prev
          );
          return;
        }

        if (event === "scan_complete" || event === "stream_complete") {
          void refreshScan();
        }
      },
      () => {
        if (!cancelled) {
          setStreamComplete(true);
        }
      },
      (message) => {
        if (!cancelled) {
          setStreamError(message);
        }
      }
    );

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [scanId]);

  if (loading) {
    return (
      <div className="empty-state empty-state-plain">
        <div className="spinner" />
        <p className="loading-copy">Loading optimization audit...</p>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <EmptyState
        title="Error"
        description={error || "Optimization audit not found"}
        action={
          <Button variant="primary" onClick={() => navigate("/")}>
            Start New Audit
          </Button>
        }
        className="empty-state-centered"
      />
    );
  }

  const findingsByCategory: Record<AnalyzerType, Finding[]> = {
    prompt_engineering: [],
    prompt_caching: [],
    batching: [],
    tool_use: [],
    structured_outputs: [],
  };

  for (const finding of scan.findings) {
    if (findingsByCategory[finding.category]) {
      findingsByCategory[finding.category].push(finding);
    }
  }

  for (const category of Object.keys(findingsByCategory) as AnalyzerType[]) {
    findingsByCategory[category].sort(
      (a, b) =>
        (SEVERITY_ORDER[a.impact.cost_reduction] ?? 2) -
        (SEVERITY_ORDER[b.impact.cost_reduction] ?? 2)
    );
  }

  const categoriesWithFindings = ALL_ANALYZERS.filter(
    (analyzer) => findingsByCategory[analyzer].length > 0
  );
  const cleanCategories = ALL_ANALYZERS.filter(
    (analyzer) =>
      scan.analyzer_statuses[analyzer] === "completed" &&
      findingsByCategory[analyzer].length === 0
  );
  const hasFindings = scan.findings.length > 0;
  const completedCount = Object.values(scan.analyzer_statuses).filter(
    (status) => status === "completed"
  ).length;
  const failedCount = Object.values(scan.analyzer_statuses).filter(
    (status) => status === "failed"
  ).length;
  const auditRunning = scan.status === "running";
  const summaryRunning =
    scan.project_summary_status === "pending" || scan.project_summary_status === "running";
  const showLiveStatus = !streamComplete && (auditRunning || summaryRunning);
  const hasPartialFailure = Boolean(scan.error) && scan.status === "completed";
  const projectName = formatProjectName(scan.project_path);
  const emptyStateTitle =
    scan.status === "failed"
      ? "Optimization audit failed"
      : hasPartialFailure
        ? "Optimization audit completed with analyzer failures"
        : "No findings";
  const emptyStateDescription =
    scan.status === "failed"
      ? scan.error || "An unknown error occurred"
      : hasPartialFailure
        ? "Some analyzers failed before they could return results, so this optimization audit finished without any confirmed findings. Review the error details and try again after fixing the project setup."
        : "Your codebase looks well-optimized. No issues were detected in this optimization audit.";
  const projectSummary = scan.project_summary;
  const showSummaryLoading = summaryRunning && !projectSummary;

  return (
    <div className="report-container">
      <header className="page-header-block report-project-header">
        <h1 className="page-title">{projectName}</h1>
        {projectSummary && (
          <>
            <p className="report-project-one-liner">{projectSummary.one_liner}</p>
            <p className="page-lede report-project-description">
              {projectSummary.description}
            </p>
          </>
        )}
        {showSummaryLoading && (
          <p className="report-project-loading">
            <span className="spinner report-project-spinner" aria-hidden="true" />
            <span>Analyzing project to generate description</span>
            <span className="report-project-loading-dots">...</span>
          </p>
        )}
      </header>

      {scan.error && hasFindings && scan.status === "completed" && (
        <div className="error-message">{scan.error}</div>
      )}

      {showLiveStatus && (
        <ScanProgressBar
          completed={completedCount}
          total={ALL_ANALYZERS.length}
          remainingAnalyzers={ALL_ANALYZERS.filter(
            (a) => scan.analyzer_statuses[a] === "pending" || scan.analyzer_statuses[a] === "running"
          ).map((a) => ANALYZER_LABELS[a])}
        />
      )}

      {streamError && <div className="error-message">{streamError}</div>}

      {scan.scorecard && hasFindings && <Scorecard scorecard={scan.scorecard} onJumpToFinding={handleJumpToFinding} />}

      {!hasFindings ? (
        auditRunning ? (
          <Surface className="report-placeholder">
            <h2 className="section-subtitle">Findings will appear here</h2>
            <p className="section-copy">
              Claude is still analyzing the project. This page updates automatically as
              each analyzer finishes.
            </p>
          </Surface>
        ) : (
          <EmptyState title={emptyStateTitle} description={emptyStateDescription} />
        )
      ) : (
        <>
          {!bannerDismissed && selectedKeys.size === 0 && (
            <div className="selection-banner">
              <span className="selection-banner-text">
                Select findings below to generate a handoff prompt for your coding agent
              </span>
              <button
                type="button"
                className="selection-banner-dismiss"
                onClick={() => setBannerDismissed(true)}
                aria-label="Dismiss"
              >
                &times;
              </button>
            </div>
          )}

          {categoriesWithFindings.map((analyzer, index) => (
            <AnalyzerSection
              key={analyzer}
              analyzer={analyzer}
              findings={findingsByCategory[analyzer]}
              projectPath={scan.project_path}
              focusKey={focusKey}
              selectedKeys={selectedKeys}
              onToggleFinding={toggleFinding}
              showCheckboxHint={index === 0 && !bannerDismissed && selectedKeys.size === 0}
            />
          ))}

          {scan.status === "completed" && failedCount === 0 && cleanCategories.length > 0 && (
            <Surface tone="muted" className="muted-summary">
              <p className="eyebrow">No issues detected</p>
              <p className="muted-summary-copy">
                {cleanCategories.map((analyzer) => ANALYZER_LABELS[analyzer]).join(", ")}
              </p>
            </Surface>
          )}
        </>
      )}

      <div className="report-actions">
        <Button variant="primary" onClick={() => navigate("/")}>
          New Audit
        </Button>
      </div>

      <SelectionBar
        count={selectedKeys.size}
        onGeneratePrompt={handleGeneratePrompt}
        onClear={clearSelection}
      />

      {showPromptModal && (
        <PromptModal
          promptText={generatePrompt(
            scan.project_path,
            scan.project_summary?.one_liner ?? null,
            scan.findings.filter((f) => selectedKeys.has(getFindingKey(f)))
          )}
          onClose={() => setShowPromptModal(false)}
        />
      )}
    </div>
  );
}
