from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AnalyzerType(str, Enum):
    PROMPT_ENGINEERING = "prompt_engineering"
    PROMPT_CACHING = "prompt_caching"
    BATCHING = "batching"
    TOOL_USE = "tool_use"
    STRUCTURED_OUTPUTS = "structured_outputs"


class AnalyzerStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectSource(str, Enum):
    BUNDLED_DEMO = "bundled_demo"
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

class ScanRequest(BaseModel):
    project_path: str


class ScanResult(BaseModel):
    scan_id: str
    project_path: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    analyzer_statuses: dict[AnalyzerType, AnalyzerStatus] = Field(default_factory=dict)
    analyzer_errors: dict[AnalyzerType, str] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    scorecard: Scorecard | None = None
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
