<div align="center">

# Claude Optimize

Find the biggest wins in your Claude integration.

<img src="frontend/src/assets/hero.png" alt="Claude Optimize hero" width="200" />

</div>

## What We Analyze

- **Prompt engineering**: vague prompts, missing XML structure, weak output contracts, and missing examples
- **Prompt caching**: repeated static prompt prefixes, uncached system prompts, and tool definitions that should be cached
- **Batching**: sequential Claude calls that should move to the Message Batches API
- **Tool use**: kitchen-sink tool lists, oversized tool definitions, and poor tool scoping
- **Structured outputs**: regex parsing, brittle `json.loads()` flows, and text-only schema enforcement

## Run In <1 Min

- Python 3.11+
- Node.js 20.19+ or 22.12+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- Add your `ANTHROPIC_API_KEY` to `.env`

```bash
cp .env.example .env
./start-dev.sh
```

That script:

- Loads `.env` if present
- Creates the backend virtual environment
- Installs backend dependencies
- Installs frontend dependencies
- Starts the backend on `http://localhost:8000`
- Starts the frontend on `http://localhost:5173`

Then open `http://localhost:5173`, enter a local project path, and run a scan.

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
