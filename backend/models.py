from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AnalyzerGroup(str, Enum):
    API = "api"
    AGENTIC = "agentic"


class AnalyzerType(str, Enum):
    # API analyzers
    PROMPT_ENGINEERING = "prompt_engineering"
    PROMPT_CACHING = "prompt_caching"
    BATCHING = "batching"
    TOOL_USE = "tool_use"
    STRUCTURED_OUTPUTS = "structured_outputs"
    MODEL_UPGRADE = "model_upgrade"
    # Agentic analyzers
    CLAUDE_MD_BLOAT = "claude_md_bloat"
    MCP_TOOL_BLOAT = "mcp_tool_bloat"


ANALYZER_GROUPS: dict[AnalyzerGroup, list[AnalyzerType]] = {
    AnalyzerGroup.API: [
        AnalyzerType.PROMPT_ENGINEERING,
        AnalyzerType.PROMPT_CACHING,
        AnalyzerType.BATCHING,
        AnalyzerType.TOOL_USE,
        AnalyzerType.STRUCTURED_OUTPUTS,
        AnalyzerType.MODEL_UPGRADE,
    ],
    AnalyzerGroup.AGENTIC: [
        AnalyzerType.CLAUDE_MD_BLOAT,
        AnalyzerType.MCP_TOOL_BLOAT,
    ],
}


class AnalyzerStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectSource(str, Enum):
    SAMPLE_PROJECT = "sample_project"
    CURSOR = "cursor"
    VSCODE = "vscode"
    CLAUDE_CODE = "claude_code"


# --- Finding schema (shared across all analyzers) ---

class CodeLocation(BaseModel):
    file: str
    lines: str = ""
    function: str = ""


class CodeSnippet(BaseModel):
    description: str
    code_snippet: str
    language: str = "python"


class Recommendation(BaseModel):
    title: str
    description: str
    docs_url: str = ""


class Impact(BaseModel):
    cost_reduction: Literal["high", "medium", "low"] = "low"
    latency_reduction: Literal["high", "medium", "low"] = "low"
    reliability_improvement: Literal["high", "medium", "low"] = "low"
    estimated_savings_detail: str = ""


class Finding(BaseModel):
    category: AnalyzerType
    model: str = ""  # Claude model used at this API call site (e.g. "claude-sonnet-4-6")
    location: CodeLocation
    current_state: CodeSnippet
    recommendation: Recommendation
    suggested_fix: CodeSnippet
    impact: Impact
    confidence: Literal["high", "medium", "low"] = "medium"
    effort: Literal["low", "medium", "high"] = "medium"


# --- Scorecard ---

class TopWin(BaseModel):
    title: str
    category: AnalyzerType
    estimated_savings: str


class Scorecard(BaseModel):
    total_findings: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    by_impact: dict[str, int] = Field(default_factory=dict)
    estimated_total_savings: str = ""
    top_wins: list[TopWin] = Field(default_factory=list)


# --- Scan request / result ---

class CloneRequest(BaseModel):
    github_url: str
    destination: str


class ScanRequest(BaseModel):
    project_path: str


class ProjectSummary(BaseModel):
    one_liner: str
    description: str


class ScanResult(BaseModel):
    scan_id: str
    project_path: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    analyzer_statuses: dict[AnalyzerType, AnalyzerStatus] = Field(default_factory=dict)
    analyzer_errors: dict[AnalyzerType, str] = Field(default_factory=dict)
    analyzer_notes: dict[AnalyzerType, str] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    scorecard: Scorecard | None = None
    project_summary: ProjectSummary | None = None
    project_summary_status: AnalyzerStatus = AnalyzerStatus.PENDING
    project_summary_error: str | None = None
    no_claude_usage: bool = False
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


# --- Apply request / result ---

class ApplyRequest(BaseModel):
    prompt: str = Field(..., max_length=100_000)
    project_path: str


class ApplyResult(BaseModel):
    apply_id: str
    project_path: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class RecentProject(BaseModel):
    path: str
    name: str
    last_used_at: datetime | None = None
    sources: list[ProjectSource] = Field(default_factory=list)


class RecentProjectsResponse(BaseModel):
    projects: list[RecentProject] = Field(default_factory=list)
