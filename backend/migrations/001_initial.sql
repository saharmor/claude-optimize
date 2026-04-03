-- Initial schema for Claude Optimize persistent storage.
-- All UUID/ID columns use TEXT for SQLite compatibility.
-- JSON payload columns store forward-compatible structured data.

-- ============================================================
-- Core Identity Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS repositories (
    id              TEXT PRIMARY KEY,
    git_root        TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL DEFAULT '',
    remote_url      TEXT,
    provider        TEXT,          -- 'github', 'gitlab', etc.
    default_branch  TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    metadata_json   TEXT           -- forward-compatible blob
);

CREATE TABLE IF NOT EXISTS workspaces (
    id              TEXT PRIMARY KEY,
    repository_id   TEXT NOT NULL REFERENCES repositories(id),
    canonical_path  TEXT UNIQUE NOT NULL,
    source          TEXT NOT NULL DEFAULT 'manual',  -- manual, cursor, vscode, claude_code, clone, sample_project
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    last_scanned_at TEXT,
    is_demo         INTEGER NOT NULL DEFAULT 0,
    metadata_json   TEXT
);

CREATE INDEX IF NOT EXISTS idx_workspaces_repository ON workspaces(repository_id);

-- ============================================================
-- Scan Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS scan_runs (
    id                      TEXT PRIMARY KEY,
    repository_id           TEXT REFERENCES repositories(id),
    workspace_id            TEXT REFERENCES workspaces(id),
    requested_path          TEXT NOT NULL,
    scan_mode               TEXT NOT NULL DEFAULT 'live',  -- live, demo
    status                  TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    requested_at            TEXT NOT NULL,
    started_at              TEXT,
    completed_at            TEXT,
    duration_ms             INTEGER,
    error_text              TEXT,
    no_claude_usage         INTEGER NOT NULL DEFAULT 0,
    project_summary_json    TEXT,
    project_summary_status  TEXT NOT NULL DEFAULT 'pending',
    project_summary_error   TEXT,
    scorecard_json          TEXT,
    findings_count          INTEGER NOT NULL DEFAULT 0,
    scanner_version         TEXT,
    git_branch              TEXT,
    git_head_sha            TEXT,
    summary_json            TEXT      -- forward-compatible blob
);

CREATE INDEX IF NOT EXISTS idx_scan_runs_workspace ON scan_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_scan_runs_repository ON scan_runs(repository_id);
CREATE INDEX IF NOT EXISTS idx_scan_runs_status ON scan_runs(status);

CREATE TABLE IF NOT EXISTS scan_analyzer_runs (
    id              TEXT PRIMARY KEY,
    scan_run_id     TEXT NOT NULL REFERENCES scan_runs(id),
    analyzer_type   TEXT NOT NULL,   -- matches AnalyzerType enum values
    analyzer_group  TEXT NOT NULL,   -- 'api' or 'agentic'
    status          TEXT NOT NULL DEFAULT 'pending',
    started_at      TEXT,
    completed_at    TEXT,
    duration_ms     INTEGER,
    model_name      TEXT,            -- the Claude model used to run this analyzer
    prompt_version  TEXT,            -- version tag of the prompt template
    prompt_hash     TEXT,            -- sha256 of the full prompt text
    result_count    INTEGER NOT NULL DEFAULT 0,
    error_text      TEXT,
    note_text       TEXT,
    raw_output_json TEXT             -- full Claude response for debugging
);

CREATE INDEX IF NOT EXISTS idx_scan_analyzer_runs_scan ON scan_analyzer_runs(scan_run_id);

CREATE TABLE IF NOT EXISTS finding_instances (
    id                      TEXT PRIMARY KEY,
    scan_run_id             TEXT NOT NULL REFERENCES scan_runs(id),
    scan_analyzer_run_id    TEXT REFERENCES scan_analyzer_runs(id),
    repository_id           TEXT REFERENCES repositories(id),
    analyzer_type           TEXT NOT NULL,
    title                   TEXT NOT NULL,
    model                   TEXT NOT NULL DEFAULT '',
    file_path               TEXT NOT NULL DEFAULT '',
    line_range              TEXT NOT NULL DEFAULT '',
    function_name           TEXT NOT NULL DEFAULT '',
    docs_url                TEXT NOT NULL DEFAULT '',
    cost_reduction          TEXT NOT NULL DEFAULT 'low',
    latency_reduction       TEXT NOT NULL DEFAULT 'low',
    reliability_improvement TEXT NOT NULL DEFAULT 'low',
    confidence              TEXT NOT NULL DEFAULT 'medium',
    effort                  TEXT NOT NULL DEFAULT 'medium',
    estimated_savings_detail TEXT NOT NULL DEFAULT '',
    finding_json            TEXT NOT NULL,   -- full Finding as JSON for reconstruction
    sort_order              INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_finding_instances_scan ON finding_instances(scan_run_id);
CREATE INDEX IF NOT EXISTS idx_finding_instances_analyzer_run ON finding_instances(scan_analyzer_run_id);
CREATE INDEX IF NOT EXISTS idx_finding_instances_repository ON finding_instances(repository_id);

-- ============================================================
-- Apply Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS apply_jobs (
    id                      TEXT PRIMARY KEY,
    repository_id           TEXT REFERENCES repositories(id),
    workspace_id            TEXT REFERENCES workspaces(id),
    source_scan_run_id      TEXT REFERENCES scan_runs(id),
    project_path            TEXT NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'pending',
    started_at              TEXT,
    completed_at            TEXT,
    duration_ms             INTEGER,
    error_text              TEXT,
    prompt_text             TEXT,
    selection_count         INTEGER NOT NULL DEFAULT 0,
    git_head_before         TEXT,
    git_head_after          TEXT,
    pr_url                  TEXT,
    pr_branch               TEXT,
    pr_error                TEXT,
    result_summary_json     TEXT
);

CREATE INDEX IF NOT EXISTS idx_apply_jobs_workspace ON apply_jobs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_apply_jobs_scan ON apply_jobs(source_scan_run_id);
CREATE INDEX IF NOT EXISTS idx_apply_jobs_status ON apply_jobs(status);

CREATE TABLE IF NOT EXISTS apply_job_findings (
    id                  TEXT PRIMARY KEY,
    apply_job_id        TEXT NOT NULL REFERENCES apply_jobs(id),
    finding_instance_id TEXT REFERENCES finding_instances(id),
    ordinal             INTEGER NOT NULL DEFAULT 0,
    title               TEXT NOT NULL DEFAULT '',
    file_path           TEXT NOT NULL DEFAULT '',
    docs_url            TEXT NOT NULL DEFAULT '',
    summary_json        TEXT,
    status              TEXT NOT NULL DEFAULT 'pending'  -- pending, applying, done, skipped
);

CREATE INDEX IF NOT EXISTS idx_apply_job_findings_job ON apply_job_findings(apply_job_id);

CREATE TABLE IF NOT EXISTS apply_events (
    id              TEXT PRIMARY KEY,
    apply_job_id    TEXT NOT NULL REFERENCES apply_jobs(id),
    sequence_no     INTEGER NOT NULL DEFAULT 0,
    event_type      TEXT NOT NULL,   -- apply_output, finding_progress, creating_pr, pr_created, etc.
    created_at      TEXT NOT NULL,
    payload_json    TEXT
);

CREATE INDEX IF NOT EXISTS idx_apply_events_job ON apply_events(apply_job_id);

-- ============================================================
-- Discovery Tables (created but not wired up yet)
-- ============================================================

CREATE TABLE IF NOT EXISTS project_observations (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT REFERENCES workspaces(id),
    source          TEXT NOT NULL,   -- cursor, vscode, claude_code, manual
    observed_at     TEXT NOT NULL,
    rank_hint       INTEGER,
    payload_json    TEXT
);

CREATE TABLE IF NOT EXISTS clone_events (
    id                  TEXT PRIMARY KEY,
    repository_id       TEXT REFERENCES repositories(id),
    workspace_id        TEXT REFERENCES workspaces(id),
    github_url          TEXT NOT NULL,
    destination_path    TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    created_at          TEXT NOT NULL,
    error_text          TEXT
);

-- ============================================================
-- Settings
-- ============================================================

CREATE TABLE IF NOT EXISTS app_settings (
    key         TEXT PRIMARY KEY,
    value_json  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
