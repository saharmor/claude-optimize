import type { ApplyResult, RecentProject, ScanResult } from "../types/scan";

function formatApiErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (!item || typeof item !== "object") {
          return null;
        }

        const record = item as { loc?: unknown; msg?: unknown };
        const location = Array.isArray(record.loc)
          ? record.loc.map(String).join(".")
          : "";
        const message = typeof record.msg === "string" ? record.msg : "";
        if (!message) {
          return null;
        }

        return location ? `${location}: ${message}` : message;
      })
      .filter((message): message is string => Boolean(message));

    if (messages.length > 0) {
      return messages.join("; ");
    }
  }

  if (detail && typeof detail === "object") {
    const record = detail as { message?: unknown; detail?: unknown };
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message;
    }
    if (typeof record.detail === "string" && record.detail.trim()) {
      return record.detail;
    }
  }

  return fallback;
}

export async function getConfig(): Promise<{ show_github_clone: boolean }> {
  const res = await fetch("/api/config");
  if (!res.ok) return { show_github_clone: false };
  return res.json();
}

export async function cloneRepo(
  githubUrl: string,
  destination: string
): Promise<{ path: string }> {
  const res = await fetch("/api/clone", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl, destination }),
  });

  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: unknown;
    };
    throw new Error(
      formatApiErrorDetail(err.detail, res.statusText || "Failed to clone repository")
    );
  }

  return res.json();
}

export async function startScan(
  projectPath: string
): Promise<{ scan_id: string; status: string }> {
  const body: Record<string, string> = { project_path: projectPath };

  const res = await fetch("/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: unknown;
    };
    throw new Error(
      formatApiErrorDetail(
        err.detail,
        res.statusText || "Failed to start optimization audit"
      )
    );
  }

  return res.json();
}

export async function getScanResult(scanId: string): Promise<ScanResult> {
  const res = await fetch(`/api/scan/${scanId}`);
  if (!res.ok) throw new Error("Failed to fetch optimization audit result");
  return res.json();
}

export async function getRecentProjects(): Promise<RecentProject[]> {
  const res = await fetch("/api/projects/recent");
  if (!res.ok) throw new Error("Failed to fetch recent projects");

  const data = (await res.json()) as { projects?: RecentProject[] };
  return data.projects ?? [];
}

export function subscribeScanStream(
  scanId: string,
  onEvent: (event: string, data: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (message: string) => void
): () => void {
  const es = new EventSource(`/api/scan/${scanId}/stream`);
  let finished = false;
  let disposed = false;

  const parseEventData = (raw: string): Record<string, unknown> => {
    try {
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return {};
    }
  };

  es.addEventListener("analyzer_status", (e) => {
    onEvent("analyzer_status", parseEventData(e.data));
  });

  es.addEventListener("analyzer_complete", (e) => {
    onEvent("analyzer_complete", parseEventData(e.data));
  });

  es.addEventListener("analyzer_failed", (e) => {
    onEvent("analyzer_failed", parseEventData(e.data));
  });

  es.addEventListener("project_summary_status", (e) => {
    onEvent("project_summary_status", parseEventData(e.data));
  });

  es.addEventListener("project_summary_complete", (e) => {
    onEvent("project_summary_complete", parseEventData(e.data));
  });

  es.addEventListener("project_summary_failed", (e) => {
    onEvent("project_summary_failed", parseEventData(e.data));
  });

  es.addEventListener("scan_complete", (e) => {
    onEvent("scan_complete", parseEventData(e.data));
  });

  es.addEventListener("stream_complete", (e) => {
    finished = true;
    onEvent("stream_complete", parseEventData(e.data));
    onDone();
    es.close();
  });

  es.onerror = () => {
    if (disposed || finished) {
      return;
    }
    es.close();
    void (async () => {
      try {
        const latest = await getScanResult(scanId);
        const summaryDone =
          latest.project_summary_status === "completed" ||
          latest.project_summary_status === "failed";

        if ((latest.status === "completed" || latest.status === "failed") && summaryDone) {
          onDone();
          return;
        }
        onError("Live progress disconnected. The optimization audit may still be running.");
      } catch {
        onError(
          "Lost connection while tracking the optimization audit. Check the backend and refresh."
        );
      }
    })();
  };

  return () => {
    disposed = true;
    es.close();
  };
}

interface FindingSummaryPayload {
  title: string;
  description: string;
  file: string;
  docs_url: string;
  cost_reduction: string;
  latency_reduction: string;
  reliability_improvement: string;
}

export async function startApply(
  prompt: string,
  projectPath: string,
  findingTitles: string[] = [],
  findingFiles: string[] = [],
  findingDocsUrls: string[] = [],
  findingSummaries: FindingSummaryPayload[] = [],
  scanId = "",
): Promise<{ apply_id: string; status: string }> {
  const res = await fetch("/api/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      project_path: projectPath,
      scan_id: scanId,
      finding_titles: findingTitles,
      finding_files: findingFiles,
      finding_docs_urls: findingDocsUrls,
      finding_summaries: findingSummaries,
    }),
  });

  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: unknown;
    };
    throw new Error(
      formatApiErrorDetail(err.detail, res.statusText || "Failed to start apply job")
    );
  }

  return res.json();
}

export async function getApplyResult(applyId: string): Promise<ApplyResult> {
  const res = await fetch(`/api/apply/${applyId}`);
  if (!res.ok) throw new Error("Failed to fetch apply job result");
  return res.json();
}

export async function retryPr(applyId: string): Promise<{ pr_url: string }> {
  const res = await fetch(`/api/apply/${applyId}/retry-pr`, { method: "POST" });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: unknown;
    };
    throw new Error(
      formatApiErrorDetail(err.detail, "Failed to retry PR creation")
    );
  }
  return res.json();
}

export function subscribeApplyStream(
  applyId: string,
  onOutput: (line: string) => void,
  onComplete: () => void,
  onFailed: (error: string) => void,
  onCreatingPr?: () => void,
  onPrCreated?: (prUrl: string) => void,
  onPrFailed?: (error: string) => void,
  onFindingProgress?: (index: number, status: "applying" | "done" | "skipped") => void,
  onKeepalive?: () => void,
): () => void {
  const es = new EventSource(`/api/apply/${applyId}/stream`);
  let finished = false;
  let disposed = false;

  const parseData = (raw: string): Record<string, unknown> => {
    try {
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return {};
    }
  };

  es.addEventListener("apply_output", (e) => {
    const data = parseData(e.data);
    if (typeof data.line === "string") {
      onOutput(data.line);
    }
  });

  es.addEventListener("finding_progress", (e) => {
    const data = parseData(e.data);
    if (typeof data.index === "number" && (data.status === "applying" || data.status === "done" || data.status === "skipped")) {
      onFindingProgress?.(data.index, data.status);
    }
  });

  es.addEventListener("keepalive", () => {
    onKeepalive?.();
  });

  es.addEventListener("apply_complete", () => {
    finished = true;
    onComplete();
    es.close();
  });

  es.addEventListener("creating_pr", () => {
    onCreatingPr?.();
  });

  es.addEventListener("pr_created", (e) => {
    const data = parseData(e.data);
    if (typeof data.pr_url === "string") {
      onPrCreated?.(data.pr_url);
    }
  });

  es.addEventListener("pr_failed", (e) => {
    const data = parseData(e.data);
    onPrFailed?.(typeof data.error === "string" ? data.error : "PR creation failed");
  });

  es.addEventListener("apply_failed", (e) => {
    finished = true;
    const data = parseData(e.data);
    onFailed(typeof data.error === "string" ? data.error : "Apply failed");
    es.close();
  });

  es.addEventListener("stream_complete", () => {
    finished = true;
    es.close();
  });

  es.onerror = () => {
    if (disposed || finished) return;
    es.close();
    void (async () => {
      try {
        const latest = await getApplyResult(applyId);
        if (latest.status === "completed") {
          if (latest.pr_url) onPrCreated?.(latest.pr_url);
          else if (latest.pr_error) onPrFailed?.(latest.pr_error);
          onComplete();
        } else if (latest.status === "failed") {
          onFailed(latest.error || "Apply failed");
        } else {
          onFailed("Lost connection to apply job. It may still be running.");
        }
      } catch {
        onFailed("Lost connection to apply job. Check the backend and refresh.");
      }
    })();
  };

  return () => {
    disposed = true;
    es.close();
  };
}

// --- History API ---

export interface ScanHistoryApply {
  apply_id: string;
  status: string;
  selection_count: number;
  pr_url: string | null;
  pr_error: string | null;
}

export interface ScanHistoryItem {
  scan_id: string;
  project_path: string;
  scan_mode: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error: string | null;
  no_claude_usage: boolean;
  findings_count: number;
  git_branch: string | null;
  git_head_sha: string | null;
  repository_id: string | null;
  repo_name: string | null;
  remote_url: string | null;
  workspace_id: string | null;
  project_summary: { one_liner: string; description: string } | null;
  scorecard: Record<string, unknown> | null;
  apply: ScanHistoryApply | null;
}

export async function getScanHistory(limit = 50, offset = 0): Promise<{ scans: ScanHistoryItem[]; total: number }> {
  const res = await fetch(`/api/history/scans?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error("Failed to fetch scan history");
  return res.json();
}
