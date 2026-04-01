export type AnalyzerType =
  | "prompt_engineering"
  | "prompt_caching"
  | "batching"
  | "tool_use"
  | "structured_outputs"
  | "model_upgrade"
  | "claude_md_bloat"
  | "mcp_tool_bloat";

export type AnalyzerGroup = "api" | "agentic";
export type AnalyzerStatus = "pending" | "running" | "completed" | "failed";
export type Severity = "high" | "medium" | "low";
export type ProjectSource = "sample_project" | "cursor" | "vscode" | "claude_code";

export const API_ANALYZERS: AnalyzerType[] = [
  "prompt_engineering",
  "prompt_caching",
  "batching",
  "tool_use",
  "structured_outputs",
  "model_upgrade",
];

export const AGENTIC_ANALYZERS: AnalyzerType[] = [
  "claude_md_bloat",
  "mcp_tool_bloat",
];

export const ALL_ANALYZERS: AnalyzerType[] = [
  ...API_ANALYZERS,
  ...AGENTIC_ANALYZERS,
];

export interface CodeLocation {
  file: string;
  lines: string;
  function: string;
}

export interface CodeSnippet {
  description: string;
  code_snippet: string;
  language: string;
}

export interface Recommendation {
  title: string;
  description: string;
  docs_url: string;
}

export interface Impact {
  cost_reduction: Severity;
  latency_reduction: Severity;
  reliability_improvement: Severity;
  estimated_savings_detail: string;
}

export interface Finding {
  category: AnalyzerType;
  model: string;
  location: CodeLocation;
  current_state: CodeSnippet;
  recommendation: Recommendation;
  suggested_fix: CodeSnippet;
  impact: Impact;
  confidence: Severity;
  effort: Severity;
}

export interface TopWin {
  title: string;
  category: AnalyzerType;
  estimated_savings: string;
}

export interface Scorecard {
  total_findings: number;
  by_category: Record<string, number>;
  by_impact: Record<string, number>;
  estimated_total_savings: string;
  top_wins: TopWin[];
}

export interface ProjectSummary {
  one_liner: string;
  description: string;
}

export interface ScanResult {
  scan_id: string;
  project_path: string;
  status: "pending" | "running" | "completed" | "failed";
  analyzer_statuses: Partial<Record<AnalyzerType, AnalyzerStatus>>;
  analyzer_errors: Partial<Record<AnalyzerType, string>>;
  analyzer_notes: Partial<Record<AnalyzerType, string>>;
  findings: Finding[];
  scorecard: Scorecard | null;
  project_summary: ProjectSummary | null;
  project_summary_status: AnalyzerStatus;
  project_summary_error: string | null;
  no_claude_usage: boolean;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface RecentProject {
  path: string;
  name: string;
  last_used_at: string | null;
  sources: ProjectSource[];
}

export interface ApplyResult {
  apply_id: string;
  project_path: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export const ANALYZER_LABELS: Record<AnalyzerType, string> = {
  prompt_engineering: "Prompt Engineering",
  prompt_caching: "Prompt Caching",
  batching: "Batching",
  tool_use: "Tool Use",
  structured_outputs: "Structured Outputs",
  model_upgrade: "Model Upgrade",
  claude_md_bloat: "CLAUDE.md Context Bloat",
  mcp_tool_bloat: "MCP Tool Bloat",
};

export const ANALYZER_GROUP_LABELS: Record<AnalyzerGroup, string> = {
  api: "API Optimization",
  agentic: "Agentic",
};

