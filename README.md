<div align="center">

# Claude Optimize

Find the biggest wins in your Claude integration.

<img src="frontend/src/assets/hero.png" alt="Claude Optimize hero" width="280" />

</div>

## Features

- **Prompt review**: finds vague prompts, missing XML structure, weak output contracts, and missing examples
- **Prompt caching analysis**: detects large repeated prompt prefixes and tool definitions that should be cached
- **Batching recommendations**: flags sequential Claude calls that belong in the Message Batches API
- **Tool use optimization**: catches kitchen-sink tool lists, oversized definitions, and poor tool scoping
- **Structured output checks**: spots regex parsing, brittle `json.loads()` flows, and text-only schema enforcement
- **Actionable report UI**: every finding includes the current code, a recommendation, and a suggested fix

## Run In <1 Min

### Prerequisites

- Python 3.11+
- Node.js 20.19+ or 22.12+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- `ANTHROPIC_API_KEY` exported in your shell before starting the backend

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, enter a local project path, and run a scan.

## Bundled Demo

Want to see the full flow immediately? Use the bundled demo project:

```bash
sample_project
```

That path is wired as a fast demo so you can preview the report without waiting on a full live scan.

## Configuration

```bash
ANTHROPIC_API_KEY=
CLAUDE_OPTIMIZE_MODEL=sonnet
CLAUDE_OPTIMIZE_MAX_TURNS=12
CLAUDE_OPTIMIZE_MAX_CONCURRENT_SCANS=2
CLAUDE_OPTIMIZE_SCAN_TTL_SECONDS=3600
CLAUDE_OPTIMIZE_SKIP_PERMISSIONS=false
CLAUDE_OPTIMIZE_ALLOWED_PATHS=
CLAUDE_OPTIMIZE_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

- Local scans are restricted to allowed roots for safety
- By default, the backend accepts paths inside your home directory and this repository
- Set `CLAUDE_OPTIMIZE_ALLOWED_PATHS` in production to explicitly control what can be scanned

## Tech Stack

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + SSE
- **Analysis engine**: Claude Code headless sessions

## Roadmap

- GitHub repo URL input
- Langfuse-backed usage-aware recommendations
- thinking level recommendations
- model routing suggestions
- auto-generated PRs with fixes applied

## License

This project is currently unlicensed.
