import type { Finding } from "../types/scan";
import { ANALYZER_LABELS } from "../types/scan";

export function generatePrompt(
  projectPath: string,
  projectSummary: string | null,
  findings: Finding[]
): string {
  const lines: string[] = [];

  lines.push("# Claude API Optimization Tasks");
  lines.push("");
  lines.push(
    "This project was analyzed for opportunities to optimize its usage of the Claude API. " +
    "The following changes were identified to reduce cost, improve latency, and increase reliability of the language model calls in this codebase. " +
    "Each task targets a specific file and function where the Claude API is invoked, and includes the current code along with a suggested fix."
  );
  lines.push("");
  lines.push(`**Project:** ${projectPath}`);
  if (projectSummary) {
    lines.push(`**Description:** ${projectSummary}`);
  }
  lines.push("");
  lines.push(
    `Apply the following ${findings.length} optimization${findings.length !== 1 ? "s" : ""} to the codebase. For each one, modify the specified file according to the suggested fix.`
  );

  findings.forEach((finding, index) => {
    lines.push("");
    lines.push("---");
    lines.push("");
    lines.push(
      `## ${index + 1}. ${finding.recommendation.title} (${ANALYZER_LABELS[finding.category]})`
    );
    lines.push("");
    lines.push(
      `**File:** \`${finding.location.file}\`${finding.location.lines ? ` (lines ${finding.location.lines})` : ""}`
    );
    if (finding.location.function) {
      lines.push(`**Function:** \`${finding.location.function}\``);
    }
    lines.push("");
    lines.push(`**Issue:** ${finding.current_state.description}`);
    lines.push("");
    lines.push("**Current code:**");
    lines.push(`\`\`\`${finding.current_state.language}`);
    lines.push(finding.current_state.code_snippet);
    lines.push("```");
    lines.push("");
    lines.push(`**Apply this fix:** ${finding.suggested_fix.description}`);
    lines.push(`\`\`\`${finding.suggested_fix.language}`);
    lines.push(finding.suggested_fix.code_snippet);
    lines.push("```");
    if (finding.recommendation.docs_url) {
      lines.push("");
      lines.push(`**Reference:** ${finding.recommendation.docs_url}`);
    }
  });

  lines.push("");

  return lines.join("\n");
}
