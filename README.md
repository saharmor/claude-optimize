<div align="center">

<h1>
  <img src="frontend/public/sparkles-icon.svg" alt="Sparkles icon" width="24" />
  Claude Optimize
</h1>

Scan your Claude-powered app and get a prioritized optimization report
to improve performance and reduce latency + cost

<br/>

<img width="761" src="frontend/src/assets/hero.png" alt="Claude Optimize preview" style="border-radius: 12px;" />

</div>

## What We Analyze

- **Prompt engineering**: vague prompts, missing XML structure, weak output contracts, and missing examples
- **Prompt caching**: repeated static prompt prefixes, uncached system prompts, and tool definitions that should be cached
- **Batching**: sequential Claude calls that should move to the Message Batches API
- **Tool use**: kitchen-sink tool lists, oversized tool definitions, and poor tool scoping
- **Structured outputs**: regex parsing, brittle `json.loads()` flows, and text-only schema enforcement

## Quick Start

Copy-paste this prompt into Claude Code, Cursor, or any AI coding agent:

> Clone https://github.com/saharmor/claude-optimize, create a `.env` file with my `ANTHROPIC_API_KEY`, run `./start-dev.sh`, and open the frontend URL in my browser.

That's it — the agent will handle cloning, installing dependencies (Python 3.11+, Node.js 20+), and starting both servers.

### Manual Setup

If you prefer to set things up yourself:

```bash
git clone https://github.com/saharmor/claude-optimize.git
cd claude-optimize
cp .env.example .env        # add your ANTHROPIC_API_KEY
./start-dev.sh
```

Requires Python 3.11+, Node.js 20.19+ or 22.12+, and the [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated.

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


## Roadmap

- GitHub repo URL input
- Langfuse-backed usage-aware recommendations
- thinking level recommendations
- model routing suggestions
- auto-generated PRs with fixes applied
