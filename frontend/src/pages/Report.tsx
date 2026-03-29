import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getScanResult } from "../api/client";
import type { ScanResult, AnalyzerType, Finding } from "../types/scan";
import { ALL_ANALYZERS, ANALYZER_LABELS } from "../types/scan";
import Scorecard from "../components/Scorecard";
import AnalyzerSection from "../components/AnalyzerSection";
import { Button, EmptyState, PageIntro, Surface } from "../components/ui";

const SEVERITY_ORDER: Record<string, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

export default function Report() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!scanId) return;

    getScanResult(scanId)
      .then((result) => {
        if (result.status === "running") {
          navigate(`/scan/${scanId}`);
          return;
        }
        setScan(result);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [scanId, navigate]);

  if (loading) {
    return (
      <div className="empty-state empty-state-plain">
        <div className="spinner" />
        <p className="loading-copy">Loading report...</p>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <EmptyState
        title="Error"
        description={error || "Scan not found"}
        action={
          <Button variant="primary" onClick={() => navigate("/")}>
            Start New Scan
          </Button>
        }
        className="empty-state-centered"
      />
    );
  }

  if (scan.status === "failed") {
    return (
      <EmptyState
        title="Scan Failed"
        description={scan.error || "An unknown error occurred"}
        action={
          <Button variant="primary" onClick={() => navigate("/")}>
            Try Again
          </Button>
        }
        className="empty-state-centered"
      />
    );
  }

  // Group findings by category
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

  // Sort within each category by impact
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
    (analyzer) => findingsByCategory[analyzer].length === 0
  );
  const hasFindings = scan.findings.length > 0;
  const hasPartialFailure = Boolean(scan.error);
  const emptyStateTitle = hasPartialFailure
    ? "Scan completed with analyzer failures"
    : "No findings";
  const emptyStateDescription = hasPartialFailure
    ? "Some analyzers failed before they could return results, so this scan finished without any confirmed findings. Review the error details and try again after fixing the scan environment."
    : "Your codebase looks well-optimized. No issues were detected by any analyzer.";

  return (
    <div className="report-container">
      <PageIntro
        eyebrow="Optimization report"
        title="Review the best opportunities first."
        description="This report groups findings by analyzer, highlights the strongest wins, and keeps the source path visible without letting it dominate the page."
        className="report-header"
      >
        <div className="path-pill">{scan.project_path}</div>
      </PageIntro>

      {scan.error && hasFindings && scan.status === "completed" && (
        <div className="error-message">{scan.error}</div>
      )}

      {scan.scorecard && hasFindings && <Scorecard scorecard={scan.scorecard} />}

      {!hasFindings ? (
        <EmptyState
          title={emptyStateTitle}
          description={emptyStateDescription}
        />
      ) : (
        <>
          {categoriesWithFindings.map((analyzer) => (
            <AnalyzerSection
              key={analyzer}
              analyzer={analyzer}
              findings={findingsByCategory[analyzer]}
            />
          ))}

          {cleanCategories.length > 0 && (
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
          New Scan
        </Button>
      </div>
    </div>
  );
}
