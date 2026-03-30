import type { Finding } from "../types/scan";

export function getFindingKey(finding: Finding): string {
  return `${finding.location.file}:${finding.location.lines}:${finding.recommendation.title}`;
}
