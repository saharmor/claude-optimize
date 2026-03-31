import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getScanResult, startApply, subscribeScanStream } from "../api/client";
import type { ScanResult, AnalyzerType, AnalyzerStatus, Finding } from "../types/scan";
import { ALL_ANALYZERS, ANALYZER_LABELS } from "../types/scan";
import { getFindingKey } from "../utils/findingKey";
import { generatePrompt } from "../utils/generatePrompt";
import { getAppliedFindings, markFindingsApplied } from "../utils/appliedFindings";
import Scorecard from "../components/Scorecard";
import AnalyzerSection from "../components/AnalyzerSection";
import SelectionBar from "../components/SelectionBar";
import PromptModal from "../components/PromptModal";
import ApplyConfirmModal from "../components/ApplyConfirmModal";
import ApplyProgress from "../components/ApplyProgress";
import ShareModal from "../components/ShareModal";
import { Button, EmptyState, ScanProgressBar } from "../components/ui";

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
  const [applyState, setApplyState] = useState<null | "confirm" | "running" | "completed" | "failed">(null);
  const [applyId, setApplyId] = useState<string | null>(null);
  const [showShareModal, setShowShareModal] = useState(false);
  const [progressFadingOut, setProgressFadingOut] = useState(false);
  const [progressVisible, setProgressVisible] = useState(false);
  const [appliedKeys, setAppliedKeys] = useState<Set<string>>(new Set());

  // Load applied findings from localStorage when scan is available
  useEffect(() => {
    if (scanId) {
      setAppliedKeys(getAppliedFindings(scanId));
    }
  }, [scanId]);

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

  const handleApply = useCallback(() => {
    setApplyState("confirm");
  }, []);

  const getSelectedPrompt = useCallback(() => {
    if (!scan) return "";
    return generatePrompt(
      scan.project_path,
      scan.project_summary?.one_liner ?? null,
      scan.findings.filter((f) => selectedKeys.has(getFindingKey(f)))
    );
  }, [scan, selectedKeys]);

  const handleApplyRun = useCallback(async () => {
    if (!scan) return;
    setApplyState("running");
    try {
      const { apply_id } = await startApply(getSelectedPrompt(), scan.project_path);
      setApplyId(apply_id);
    } catch {
      setApplyState(null);
      setError("Failed to start apply job. Please try again.");
    }
  }, [scan, getSelectedPrompt]);

  const handleApplySuccess = useCallback(() => {
    if (!scanId) return;
    const keys = [...selectedKeys];
    markFindingsApplied(scanId, keys);
    setAppliedKeys((prev) => {
      const next = new Set(prev);
      for (const k of keys) next.add(k);
      return next;
    });
  }, [scanId, selectedKeys]);

  const handleApplyBack = useCallback(() => {
    // Deselect any findings that were successfully applied
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      for (const k of appliedKeys) next.delete(k);
      return next;
    });
    setApplyState(null);
    setApplyId(null);
  }, [appliedKeys]);

  const handleApplyRetry = useCallback(() => {
    setApplyState("confirm");
    setApplyId(null);
  }, []);

  // Manage progress bar fade-out when scan finishes
  const fadeTimerRef = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    if (!scan) return;
    const isLive = scan.status === "running" ||
      scan.project_summary_status === "pending" ||
      scan.project_summary_status === "running";

    if (isLive && !progressVisible) {
      setProgressVisible(true);
      setProgressFadingOut(false);
    } else if (!isLive && progressVisible && !progressFadingOut) {
      setProgressFadingOut(true);
      fadeTimerRef.current = setTimeout(() => {
        setProgressVisible(false);
        setProgressFadingOut(false);
      }, 500);
    }
  }, [scan, progressVisible, progressFadingOut]);
  useEffect(() => () => { if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current); }, []);

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
          const note = typeof data.note === "string" ? data.note : undefined;
          setScan((prev) =>
            prev
              ? {
                  ...prev,
                  analyzer_statuses: {
                    ...prev.analyzer_statuses,
                    [analyzer]: "completed",
                  },
                  ...(note
                    ? { analyzer_notes: { ...prev.analyzer_notes, [analyzer]: note } }
                    : {}),
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
          <Button variant="primary" onClick={() => { navigate("/"); window.scrollTo(0, 0); }}>
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
    model_upgrade: [],
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

  const completedAnalyzers = ALL_ANALYZERS.filter(
    (analyzer) => scan.analyzer_statuses[analyzer] === "completed"
  ).sort((a, b) => findingsByCategory[b].length - findingsByCategory[a].length);
  const cleanCategories = completedAnalyzers.filter(
    (analyzer) => findingsByCategory[analyzer].length === 0
  );
  const hasFindings = scan.findings.length > 0;
  const completedCount = Object.values(scan.analyzer_statuses).filter(
    (status) => status === "completed"
  ).length;
  const auditRunning = scan.status === "running";
  const noClaudeUsage = scan.no_claude_usage === true;
  const summaryRunning =
    scan.project_summary_status === "pending" || scan.project_summary_status === "running";
  const hasPartialFailure = Boolean(scan.error) && scan.status === "completed";
  const projectName = formatProjectName(scan.project_path);
  const failedAnalyzers = ALL_ANALYZERS.filter(
    (a) => scan.analyzer_statuses[a] === "failed"
  );
  // Group failed analyzers by their error message so we don't repeat the same error 6 times
  const errorGroups: { error: string; analyzers: string[] }[] = [];
  for (const a of failedAnalyzers) {
    const err = scan.analyzer_errors[a] || "Unknown error";
    const existing = errorGroups.find((g) => g.error === err);
    if (existing) {
      existing.analyzers.push(ANALYZER_LABELS[a]);
    } else {
      errorGroups.push({ error: err, analyzers: [ANALYZER_LABELS[a]] });
    }
  }

  const allSameError = errorGroups.length === 1 && failedAnalyzers.length === ALL_ANALYZERS.length;
  const emptyStateTitle =
    scan.status === "failed"
      ? "Optimization audit failed"
      : hasPartialFailure
        ? "Optimization audit completed with analyzer failures"
        : "No findings";
  const emptyStateDescription =
    scan.status === "failed"
      ? allSameError
        ? `All analyzers failed with the same error.`
        : scan.error || "An unknown error occurred"
      : hasPartialFailure
        ? "Some analyzers failed before they could return results, so this optimization audit finished without any confirmed findings. Review the error details and try again after fixing the project setup."
        : "Your codebase looks well-optimized. No issues were detected in this optimization audit.";
  const projectSummary = scan.project_summary;
  const showSummaryLoading = summaryRunning && !projectSummary;

  const selectedFindings = scan.findings.filter((f) => selectedKeys.has(getFindingKey(f)));

  if (applyState && applyState !== "confirm" && applyId) {
    return (
      <>
        <div className="report-container">
          <header className="page-header-block report-project-header">
            <button className="back-button" onClick={handleApplyBack}>
              ← Back to report
            </button>
            <h1 className="page-title">{projectName}</h1>
            {projectSummary && (
              <>
                <p className="report-project-one-liner">{projectSummary.one_liner}</p>
                <p className="page-lede report-project-description">
                  {projectSummary.description}
                </p>
              </>
            )}
          </header>
          <ApplyProgress
            applyId={applyId}
            projectPath={scan.project_path}
            findings={selectedFindings}
            onBack={handleApplyBack}
            onRetry={handleApplyRetry}
            onShare={() => setShowShareModal(true)}
            onApplySuccess={handleApplySuccess}
          />
        </div>
        {showShareModal && (
          <ShareModal
            scan={scan}
            projectName={projectName}
            onClose={() => setShowShareModal(false)}
          />
        )}
      </>
    );
  }

  return (
    <div className="report-container">
      <header className="page-header-block report-project-header">
        <button
          className="back-button"
          onClick={() => { navigate("/"); window.scrollTo(0, 0); }}
        >
          ← Back
        </button>
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
            <span>Analyzing project to generate description...</span>
          </p>
        )}
      </header>

      {noClaudeUsage ? (
        <EmptyState
          className="fade-in-up"
          title="No Claude API usage detected"
          description="This project doesn't appear to use the Anthropic Claude API. The audit analyzes Claude API calls for optimization opportunities and won't produce findings for projects using other LLM providers."
        />
      ) : (
        <>
          {scan.error && hasFindings && scan.status === "completed" && (
            <div className="error-message">
              <p>{scan.error}</p>
              {errorGroups.length > 0 && (
                <ul className="analyzer-errors-inline">
                  {errorGroups.map((group, i) => (
                    <li key={i}>
                      <strong>
                        {group.analyzers.length === ALL_ANALYZERS.length
                          ? "All analyzers"
                          : group.analyzers.join(", ")}
                        :
                      </strong>{" "}
                      {group.error}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {progressVisible && (
            <div className={progressFadingOut ? "fade-out" : ""}>
              <ScanProgressBar
                completed={completedCount}
                total={ALL_ANALYZERS.length}
                remainingAnalyzers={ALL_ANALYZERS.filter(
                  (a) => scan.analyzer_statuses[a] === "pending" || scan.analyzer_statuses[a] === "running"
                ).map((a) => ANALYZER_LABELS[a])}
              />
            </div>
          )}

          {streamError && <div className="error-message">{streamError}</div>}

          {scan.scorecard && hasFindings && (
            <Scorecard
              scorecard={scan.scorecard}
              onJumpToFinding={handleJumpToFinding}
              onShare={streamComplete ? () => setShowShareModal(true) : undefined}
            />
          )}

          {hasFindings && (
            <p className="selection-helper-text">
              Review the findings and select the ones you want to fix
            </p>
          )}

          {completedAnalyzers.map((analyzer) => (
            <AnalyzerSection
              key={analyzer}
              analyzer={analyzer}
              findings={findingsByCategory[analyzer]}
              projectPath={scan.project_path}
              focusKey={focusKey}
              selectedKeys={selectedKeys}
              appliedKeys={appliedKeys}
              onToggleFinding={toggleFinding}
            />
          ))}

          {!hasFindings && !auditRunning && (cleanCategories.length === 0 || errorGroups.length > 0) && (
            <>
              <EmptyState title={emptyStateTitle} description={emptyStateDescription} />
              {errorGroups.length > 0 && (
                <div className="analyzer-errors-detail">
                  <h3 className="analyzer-errors-heading">Error details</h3>
                  <ul className="analyzer-errors-list">
                    {errorGroups.map((group, i) => (
                      <li key={i} className="analyzer-error-item">
                        <strong>
                          {group.analyzers.length === ALL_ANALYZERS.length
                            ? "All analyzers"
                            : group.analyzers.join(", ")}
                        </strong>
                        <span className="analyzer-error-text">{group.error}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="analyzer-errors-help">
                    <p className="analyzer-errors-help-title">Troubleshooting</p>
                    <ul className="analyzer-errors-help-list">
                      {errorGroups.some((g) => g.error.includes("No such file or directory")) && (
                        <li>
                          The <code>claude</code> CLI was not found. Install it
                          with <code>npm install -g @anthropic-ai/claude-code</code> and
                          make sure it's in your PATH.
                        </li>
                      )}
                      {errorGroups.some((g) => g.error.includes("timed out")) && (
                        <li>
                          One or more analyzers timed out. Try increasing the
                          timeout or scanning a smaller project.
                        </li>
                      )}
                      {errorGroups.some((g) => g.error.includes("permission")) && (
                        <li>
                          Permission error. Set the <code>CLAUDE_OPTIMIZE_SKIP_PERMISSIONS=true</code> environment
                          variable before starting the server.
                        </li>
                      )}
                      <li>
                        Verify the CLI works by running <code>claude --version</code> in
                        your terminal, then restart the server.
                      </li>
                    </ul>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}

      <div className="report-actions">
        {hasFindings && streamComplete && (
          <Button variant="secondary" onClick={() => setShowShareModal(true)}>
            Share Results
          </Button>
        )}
        <Button variant="primary" onClick={() => { navigate("/"); window.scrollTo(0, 0); }}>
          New Audit
        </Button>
      </div>

      <SelectionBar
        count={selectedKeys.size}
        onGeneratePrompt={handleGeneratePrompt}
        onApply={handleApply}
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

      {applyState === "confirm" && (
        <ApplyConfirmModal
          findingCount={selectedKeys.size}
          onRun={handleApplyRun}
          onCancel={() => setApplyState(null)}
        />
      )}

      {showShareModal && (
        <ShareModal
          scan={scan}
          projectName={projectName}
          onClose={() => setShowShareModal(false)}
        />
      )}
    </div>
  );
}
