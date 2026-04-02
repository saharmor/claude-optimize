import { useCallback, useEffect, useRef, useState } from "react";
import confetti from "canvas-confetti";
import { retryPr, subscribeApplyStream } from "../api/client";
import type { Finding } from "../types/scan";
import { ANALYZER_LABELS } from "../types/scan";

interface Props {
  applyId: string;
  projectPath: string;
  findings: Finding[];
  onBack: () => void;
  onRetry: () => void;
  onShare: () => void;
  onApplySuccess?: () => void;
}

/** Fire a confetti celebration. Returns a cleanup function that stops the sustained shower early. */
function fireConfetti(): () => void {
  const duration = 3000;
  const end = Date.now() + duration;

  const colors = ["#2d6a4f", "#40916c", "#52b788", "#74c69d", "#b7e4c7", "#ffd166", "#ef476f"];

  // Big initial bursts from both sides
  confetti({ particleCount: 150, spread: 80, startVelocity: 55, origin: { x: 0, y: 0.6 }, angle: 60, colors });
  confetti({ particleCount: 150, spread: 80, startVelocity: 55, origin: { x: 1, y: 0.6 }, angle: 120, colors });

  // Center burst
  confetti({ particleCount: 100, spread: 100, startVelocity: 45, origin: { x: 0.5, y: 0.4 }, colors });

  // Sustained shower
  const interval = setInterval(() => {
    if (Date.now() > end) {
      clearInterval(interval);
      return;
    }

    confetti({
      particleCount: 40,
      spread: 70,
      startVelocity: 35,
      origin: { x: Math.random(), y: -0.1 },
      colors,
      ticks: 200,
      gravity: 1.2,
      scalar: 1.2,
    });
  }, 200);

  return () => clearInterval(interval);
}

export default function ApplyProgress({ applyId, projectPath, findings, onBack, onRetry, onShare, onApplySuccess }: Props) {
  const [outputLines, setOutputLines] = useState<string[]>([]);
  const [status, setStatus] = useState<"running" | "completed" | "failed">("running");
  const [error, setError] = useState<string | null>(null);
  const [logFadingOut, setLogFadingOut] = useState(false);
  const [logHidden, setLogHidden] = useState(false);
  const [creatingPr, setCreatingPr] = useState(false);
  const [prUrl, setPrUrl] = useState<string | null>(null);
  const [prError, setPrError] = useState<string | null>(null);
  const [retryingPr, setRetryingPr] = useState(false);
  // Per-finding progress: tracks status for each finding by index
  const [findingStatuses, setFindingStatuses] = useState<Record<number, "applying" | "done">>({});
  const logRef = useRef<HTMLDivElement>(null);
  const fadeTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const confettiFired = useRef(false);

  const handleRetryPr = useCallback(async () => {
    setRetryingPr(true);
    setPrError(null);
    try {
      const { pr_url } = await retryPr(applyId);
      setPrUrl(pr_url);
    } catch (err) {
      setPrError(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setRetryingPr(false);
    }
  }, [applyId]);

  useEffect(() => {
    return () => { if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current); };
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeApplyStream(
      applyId,
      (line) => {
        setOutputLines((prev) => [...prev, line]);
      },
      () => {
        setStatus("completed");
        onApplySuccess?.();
      },
      (err) => {
        setStatus("failed");
        setError(err);
      },
      () => {
        setCreatingPr(true);
      },
      (url) => {
        setCreatingPr(false);
        setPrUrl(url);
      },
      (err) => {
        setCreatingPr(false);
        setPrError(err);
      },
      (index, findingStatus) => {
        setFindingStatuses((prev) => ({ ...prev, [index]: findingStatus }));
      },
    );

    return unsubscribe;
  }, [applyId, onApplySuccess]);

  // Fire confetti when success card becomes visible, waiting for focus if needed
  const confettiCleanup = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => { confettiCleanup.current?.(); };
  }, []);

  useEffect(() => {
    if (status !== "completed" || !logHidden || confettiFired.current) return;

    const trigger = () => {
      if (confettiFired.current) return;
      confettiFired.current = true;
      confettiCleanup.current = fireConfetti();
    };

    if (document.hasFocus()) {
      trigger();
    } else {
      const onFocus = () => {
        trigger();
        window.removeEventListener("focus", onFocus);
      };
      window.addEventListener("focus", onFocus);
      return () => window.removeEventListener("focus", onFocus);
    }
  }, [status, logHidden]);

  // Fade out the log when status changes from running
  useEffect(() => {
    if (status === "running" || logHidden) return;
    // Nothing to fade — skip straight to hidden
    if (outputLines.length === 0) {
      setLogHidden(true);
      return;
    }
    if (!logFadingOut) {
      setLogFadingOut(true);
      fadeTimerRef.current = setTimeout(() => {
        setLogHidden(true);
        setLogFadingOut(false);
      }, 400);
    }
  }, [status, outputLines.length, logFadingOut, logHidden]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [outputLines]);

  const cursorUrl = `cursor://file${encodeURI(projectPath)}`;
  const vscodeUrl = `vscode://file${encodeURI(projectPath)}`;
  const started = outputLines.length > 0;
  const showLog = outputLines.length > 0 && !logHidden;

  return (
    <div className="apply-progress">
      {/* Status header */}
      <div className="apply-progress-header">
        {status === "running" && (
          <>
            <span className="spinner apply-progress-spinner" aria-hidden="true" />
            <h2 className="apply-progress-title">Applying optimizations...</h2>
          </>
        )}
        {status === "completed" && (
          <h2 className="apply-progress-title apply-progress-title-done apply-fade-in">
            Optimizations applied
          </h2>
        )}
        {status === "failed" && (
          <h2 className="apply-progress-title apply-progress-title-failed apply-fade-in">
            Apply failed
          </h2>
        )}
      </div>

      {/* Findings list */}
      {findings.length > 0 && (
        <div className="apply-findings-list">
          {findings.map((f, i) => {
            let rowStatus: "pending" | "applying" | "done" | "failed";
            if (status === "completed") {
              rowStatus = "done";
            } else if (status === "failed") {
              rowStatus = findingStatuses[i] === "done" ? "done" : "failed";
            } else if (findingStatuses[i]) {
              // Use per-finding status from backend events
              rowStatus = findingStatuses[i];
            } else if (started && i === 0 && !findingStatuses[0]) {
              // If output has started but no finding_progress events yet, show first as applying
              rowStatus = "applying";
            } else {
              rowStatus = "pending";
            }

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

      {/* Terminal output log — only while running */}
      {showLog && (
        <div className={`apply-output-log ${logFadingOut ? "apply-log-fade-out" : ""}`} ref={logRef}>
          {outputLines.map((line, i) => (
            <div key={i} className="apply-output-line">{line || "\u00A0"}</div>
          ))}
        </div>
      )}

      {/* Waiting state */}
      {status === "running" && outputLines.length === 0 && (
        <div className="apply-progress-waiting">
          <span className="spinner" aria-hidden="true" />
          <p>Waiting for Claude Code to apply fixes...</p>
        </div>
      )}

      {/* Failed state */}
      {status === "failed" && logHidden && (
        <div className="apply-error-detail apply-fade-in">
          {error && <p className="apply-error-message">{error}</p>}
          <div className="apply-error-help">
            <p className="apply-error-help-title">What you can do</p>
            <ul className="apply-error-help-list">
              <li>
                Check the terminal where the server is running for the full error output.
              </li>
              <li>
                Make sure <code>claude</code> CLI is installed and accessible. Run <code>claude --version</code> in your terminal.
              </li>
              <li>
                Verify the project path <code>{projectPath}</code> exists and is readable.
              </li>
              <li>
                Try applying fewer findings at once. Some combinations may conflict.
              </li>
            </ul>
          </div>
          <div className="apply-error-actions">
            <button type="button" className="btn btn-primary" onClick={onRetry}>
              Try again
            </button>
            <button type="button" className="btn btn-secondary" onClick={onBack}>
              ← Back to report
            </button>
          </div>
        </div>
      )}

      {/* Completed state */}
      {status === "completed" && logHidden && (
        <div className="apply-success-card surface apply-fade-in">
          <div className="apply-success-top">
            <p className="apply-success-heading">Changes are ready for review</p>

            {/* PR status */}
            {prUrl ? (
              <div className="apply-pr-status apply-pr-success">
                <span className="apply-pr-icon">&#10003;</span>
                <a href={prUrl} target="_blank" rel="noopener noreferrer" className="btn btn-primary apply-pr-link">
                  View Pull Request
                </a>
              </div>
            ) : prError ? (
              <div className="apply-pr-status apply-pr-warning">
                <p className="apply-pr-error-text">Could not create PR: {prError}</p>
                <p className="apply-pr-error-hint">Your changes are saved locally on the branch.</p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ marginTop: "0.5rem" }}
                  onClick={handleRetryPr}
                  disabled={retryingPr}
                >
                  {retryingPr ? (
                    <>
                      <span className="spinner" aria-hidden="true" style={{ width: 14, height: 14, marginRight: 6 }} />
                      Retrying...
                    </>
                  ) : (
                    "Retry PR Creation"
                  )}
                </button>
              </div>
            ) : creatingPr ? (
              <div className="apply-pr-status">
                <span className="spinner apply-pr-spinner" aria-hidden="true" />
                <span>Creating pull request...</span>
              </div>
            ) : null}

            {!prUrl && (
              <p className="apply-success-hint">
                Open the project in your editor to review and commit the changes.
              </p>
            )}
            <div className="apply-success-buttons">
              <a href={cursorUrl} className={prUrl ? "btn btn-secondary" : "btn btn-primary"}>
                Open in Cursor
              </a>
              <a href={vscodeUrl} className="btn btn-secondary">
                Open in VS Code
              </a>
            </div>
          </div>
          <div className="apply-share-section">
            <p className="apply-share-heading">Help other developers optimize their code</p>
            <p className="apply-share-description">
              Share your results so others can discover what they could improve.
            </p>
            <button type="button" className="btn btn-primary apply-share-btn" onClick={onShare}>
              Spread the Word
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
