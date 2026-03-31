<div align="center">

<h1>
  <img src="frontend/public/sparkles-icon.svg" alt="Sparkles icon" width="24" />
  Claude Optimize
</h1>

Scan your Claude-powered app and get a prioritized optimization report
to improve performance and reduce latency + cost

[**Get started in less than a minute →**](#quick-start)

<img width="1287" height="519" alt="Screenshot 2026-03-30 at 2 46 42 PM" src="https://github.com/user-attachments/assets/c35efb10-5946-4650-a171-e13788fb4b99" />

</div>

## What We Analyze

- **Prompt engineering**: vague prompts, missing XML structure, weak output contracts, and missing examples
- **Prompt caching**: repeated static prompt prefixes, uncached system prompts, and tool definitions that should be cached
- **Batching**: sequential Claude calls that should move to the Message Batches API
- **Tool use**: kitchen-sink tool lists, oversized tool definitions, and poor tool scoping
- **Structured outputs**: regex parsing, brittle `json.loads()` flows, and text-only schema enforcement

## Quick Start

Copy-paste this prompt into Claude Code, Cursor, or any AI coding agent:

> Clone https://github.com/saharmor/claude-optimize, create a `.env` file from `.env.example`, run `./start-dev.sh`, and open the frontend URL in my browser.

That's it — the agent will handle cloning, installing dependencies ([uv](https://docs.astral.sh/uv/getting-started/installation/), Python 3.11+, Node.js 20+), and starting both servers. If you're logged into Claude Code (`claude login`), scans use your existing subscription at no extra cost. See [Authentication & Billing](#authentication--billing) for details.

### Authentication & Billing

Claude Optimize runs scans using the Claude Code CLI. You can authenticate in two ways:

| Method | How to set up | Billing |
|---|---|---|
| **Claude Code subscription** (recommended) | Run `claude login` — no API key needed | Covered by your existing Max subscription |
| **API key** | Add `ANTHROPIC_API_KEY=sk-ant-...` to `.env` | Billed to your Anthropic API account |

The startup script auto-detects which method to use. If `ANTHROPIC_API_KEY` is set, it takes priority and **API usage will be charged to that key**. If no key is set, the CLI falls back to your Claude Code subscription.

The start script creates a virtual environment, installs all dependencies, and starts:
- Backend on `http://localhost:8000`
- Frontend on `http://localhost:5173`

Then open `http://localhost:5173`, enter a local project path, and run a scan.

## Run via Claude Code

Skip the web UI entirely — run the optimizer as a slash command in Claude Code from any project:

```bash
# One-time setup: copy the command to your global Claude commands
mkdir -p ~/.claude/commands
cp commands/optimize.md ~/.claude/commands/
```

Then open Claude Code in any project and run:

```
/user:optimize
```

This will analyze your Claude API usage across 6 categories, apply high-confidence fixes directly to your code, and generate an `OPTIMIZE_REPORT.md` summarizing what changed and why.

To get a report without applying any changes:

```
/user:optimize --report-only
```

## Sample Project

Want to see the full flow immediately? Enter the path to the `sample_project` directory (inside this repo) in the web UI:

```
/full/path/to/claude-optimize/sample_project
```

That path is wired as a fast preview so you can see the report without waiting on a full live scan.

## Configuration

```bash
ANTHROPIC_API_KEY=                          # optional — see Authentication & Billing above
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


## Roadmap

- GitHub repo URL input
- Langfuse-backed usage-aware recommendations
- thinking level recommendations
- model routing suggestions
- auto-generated PRs with fixes applied
