import type { RecentProject, ScanResult } from "../types/scan";

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
