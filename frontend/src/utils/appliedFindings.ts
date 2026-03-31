const STORAGE_KEY = "claude-optimize:applied-findings";

/** Returns the set of finding keys that have been successfully applied for a given scan. */
export function getAppliedFindings(scanId: string): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const data: Record<string, string[]> = JSON.parse(raw);
    return new Set(data[scanId] ?? []);
  } catch {
    return new Set();
  }
}

/** Marks the given finding keys as successfully applied for a scan. */
export function markFindingsApplied(scanId: string, keys: string[]): void {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const data: Record<string, string[]> = raw ? JSON.parse(raw) : {};
    const existing = new Set(data[scanId] ?? []);
    for (const k of keys) existing.add(k);
    data[scanId] = [...existing];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // localStorage unavailable — silently ignore
  }
}
