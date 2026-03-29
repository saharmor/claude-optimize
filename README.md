# Claude Optimize

Scan your Claude-powered codebase and get a prioritized optimization report. Surface concrete opportunities to reduce cost, cut latency, and improve reliability by leveraging Claude API capabilities that most developers haven't implemented.

## What it does

Claude Optimize runs **5 parallel analyzers** against your codebase, each powered by a Claude Code headless session:

| Analyzer | What it finds |
|---|---|
| **Prompt Engineering** | Vague prompts, missing XML tags, no few-shot examples, missing output contracts |
| **Prompt Caching** | Large static prompts sent without `cache_control`, repeated tool definitions |
| **Batching** | Sequential loops of independent API calls that could use Message Batches (50% savings) |
| **Tool Use** | All tools passed to every call, oversized descriptions, manual parsing instead of native tool use |
| **Structured Outputs** | Regex parsing, json.loads with retries, "return JSON" prompts instead of native structured outputs |

Each finding includes:
- The exact code from your repo with the issue highlighted
- A plain-English explanation of the Claude feature being leveraged
- An auto-generated fix ready to copy-paste
- Estimated cost/latency impact
- Link to the relevant Anthropic docs

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated

### 1. Install backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Install frontend

```bash
cd frontend
npm install
```

### 3. Run

Start both in separate terminals:

```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Open http://localhost:5173, enter the path to a Claude-powered project, and click **Run Scan**.

### Environment notes

- Set `ANTHROPIC_API_KEY` in your shell or local `.env` file before running scans.
- For safer local scanning, the backend only allows project paths inside the current user's home directory by default.
- For production, set `CLAUDE_OPTIMIZE_ALLOWED_PATHS` to a comma-separated allowlist of directories the service is permitted to scan.
- Set `CLAUDE_OPTIMIZE_CORS_ORIGINS` in production instead of relying on the local dev default.
- If your Claude CLI workflow requires it, you can explicitly opt into `CLAUDE_OPTIMIZE_SKIP_PERMISSIONS=true`.

### Try the demo

Point the scanner at the included sample project:

```
/path/to/claude-optimize/sample_project
```

This is a customer support ticket classifier with all 5 anti-patterns baked in. Claude Optimize will find them all.

## Architecture

```
[React UI] --> [FastAPI backend] --> [5x Claude Code headless sessions (parallel)]
                                            |
                                     [Structured findings]
                                            |
                                     [Ranking + aggregation]
                                            |
                                     [Report JSON --> UI]
```

- **Frontend**: React + TypeScript + Vite
- **Backend**: Python FastAPI with SSE for real-time progress
- **Analysis engine**: Claude Code headless (`claude --print`) with specialized prompts per analyzer
- **Operational guardrails**: scan path allowlisting, bounded concurrent scans, scan TTL cleanup, and health checks via `/api/health`

## Roadmap (v1)

- GitHub repo URL input (clone + scan)
- Langfuse integration for data-driven caching/batching recommendations
- Thinking level optimization (recommend appropriate thinking levels per call)
- Model routing (recommend Haiku vs Sonnet vs Opus per task)
- Auto-generated PRs with fixes applied
