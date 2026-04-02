"""Pre-generated findings for the sample project.

When a scan is run against the sample project, these findings are returned
instead of invoking the real Claude Code analyzers. This lets users preview a full
report instantly (< 20 seconds) without consuming API quota.
"""
from __future__ import annotations

from models import (
    AnalyzerType,
    CodeLocation,
    CodeSnippet,
    Finding,
    Impact,
    Recommendation,
)

_FILE = "classifier.py"
_CLAUDE_MD = "CLAUDE.md"
_CLAUDE_SETTINGS = ".claude/settings.json"

DEMO_FINDINGS: list[Finding] = [
    # -------------------------------------------------------------------------
    # Prompt Engineering
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.PROMPT_ENGINEERING,
        model="claude-sonnet-4-6",
        location=CodeLocation(file=_FILE, lines="30-50"),
        current_state=CodeSnippet(
            description=(
                "Vague, unstructured system prompt with no XML tags, no few-shot examples, "
                "and no output schema. The instruction to 'Return JSON' is buried at the end "
                "as a prose sentence, making format adherence unreliable."
            ),
            code_snippet=(
                'SYSTEM_PROMPT = """You are a helpful customer support assistant for ShopFlow...\n'
                "...\n"
                "You should categorize tickets and respond to them. Try to be helpful and follow "
                "the policies above. Return your response as JSON with the fields category, "
                'priority, and suggested_response."""'
            ),
            language="python",
        ),
        recommendation=Recommendation(
            title="Add XML structure, output contract, and few-shot examples",
            description=(
                "Use XML tags to separate concerns (role, policies, task, output format). "
                "Define the exact output schema upfront so Claude knows the expected shape on "
                "the first attempt. Add one short few-shot example to anchor the format."
            ),
            docs_url="https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags",
        ),
        suggested_fix=CodeSnippet(
            description="Restructured prompt with XML tags, explicit output schema, and a short example",
            code_snippet="""\
SYSTEM_PROMPT = \"\"\"<role>
You are a customer support classifier for ShopFlow, an e-commerce platform.
</role>

<policies>
Return Policy: 30 days for most items, 15 days for electronics...
Shipping Policy: Standard 5-7 days, Express 2-3 days...
Escalation Policy: Escalate for legal threats, manager requests,
                   >48h wait, or charges >$500.
</policies>

<task>
Classify the incoming support ticket and draft a response.
</task>

<output_schema>
Return ONLY valid JSON, no prose, no markdown fences:
{
  "category": "shipping|returns|billing|technical|general",
  "priority": "low|medium|high|urgent",
  "suggested_response": "<full reply to send the customer>"
}
</output_schema>

<example>
Ticket: "My order #12345 hasn't arrived after 10 days."
Response: {"category":"shipping","priority":"medium","suggested_response":"Hi! I'm sorry your order is delayed..."}
</example>
\"\"\"
""",
            language="python",
        ),
        impact=Impact(
            cost_reduction="low",
            latency_reduction="medium",
            reliability_improvement="high",
            estimated_savings_detail=(
                "Reduces retry rate from ~30% to near zero, cutting wasted calls and latency on malformed responses."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # Prompt Caching
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.PROMPT_CACHING,
        model="claude-sonnet-4-6",
        location=CodeLocation(file=_FILE, lines="196-204", function="classify_ticket"),
        current_state=CodeSnippet(
            description=(
                "The 2,000-token system prompt is sent as plain text on every API call. "
                "With 10+ tickets per batch, the same static content is billed as full "
                "input tokens every single time."
            ),
            code_snippet="""\
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=SYSTEM_PROMPT,   # ← full 2,000-token prompt, no cache_control
    tools=ALL_TOOLS,
    messages=[{"role": "user", "content": user_message}]
)
""",
            language="python",
        ),
        recommendation=Recommendation(
            title="Cache the static system prompt with cache_control",
            description=(
                "Pass the system prompt as a content block with cache_control: "
                "{type: 'ephemeral'}. After the first call the prefix is cached and "
                "subsequent calls read it at ~10% of the normal input token price."
            ),
            docs_url="https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching",
        ),
        suggested_fix=CodeSnippet(
            description="Pass the system prompt as a content block with cache_control",
            code_snippet="""\
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # ← cache the static prefix
        }
    ],
    tools=ALL_TOOLS,
    messages=[{"role": "user", "content": user_message}]
)
""",
            language="python",
        ),
        impact=Impact(
            cost_reduction="high",
            latency_reduction="medium",
            reliability_improvement="low",
            estimated_savings_detail=(
                "Cuts input cost on the system prompt by ~90% after the first request. Adds up fast on repeated calls."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # Batching
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.BATCHING,
        model="claude-sonnet-4-6",
        location=CodeLocation(
            file=_FILE, lines="248-254", function="process_ticket_backlog"
        ),
        current_state=CodeSnippet(
            description=(
                "Tickets are processed sequentially in a for-loop. Each call blocks the "
                "next, multiplying total wall-clock time by the number of tickets. "
                "The Message Batches API processes all tickets in parallel at 50% lower cost."
            ),
            code_snippet="""\
results = []
for i, ticket in enumerate(tickets):
    print(f"Processing ticket {i + 1}/{len(tickets)}: {ticket['id']}")
    result = classify_ticket(ticket)   # ← sequential, one API call at a time
    result["ticket_id"] = ticket["id"]
    results.append(result)
""",
            language="python",
        ),
        recommendation=Recommendation(
            title="Replace the for-loop with the Message Batches API",
            description=(
                "The Message Batches API accepts up to 100,000 requests in a single call, "
                "processes them in parallel, and charges 50% less per token. Ideal for "
                "offline ticket backlogs that don't need a real-time response."
            ),
            docs_url="https://docs.anthropic.com/en/docs/build-with-claude/message-batches",
        ),
        suggested_fix=CodeSnippet(
            description="Submit all tickets as a single batch and poll for completion",
            code_snippet="""\
def process_ticket_backlog(tickets: list[dict]) -> list[dict]:
    # Build one request per ticket
    requests = [
        {
            "custom_id": ticket["id"],
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "system": [
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [{"role": "user", "content": _build_user_message(ticket)}],
            },
        }
        for ticket in tickets
    ]

    # Submit the entire backlog (50% cost savings vs. sequential calls)
    batch = client.messages.batches.create(requests=requests)

    # Poll until complete
    import time
    while batch.processing_status == "in_progress":
        time.sleep(5)
        batch = client.messages.batches.retrieve(batch.id)

    # Collect results
    results = []
    for result in client.messages.batches.results(batch.id):
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            parsed = json.loads(text)
            parsed["ticket_id"] = result.custom_id
            results.append(parsed)
    return results
""",
            language="python",
        ),
        impact=Impact(
            cost_reduction="high",
            latency_reduction="high",
            reliability_improvement="medium",
            estimated_savings_detail=(
                "50% cost reduction on the entire batch. The more calls you process, the bigger the savings."
            ),
        ),
        confidence="high",
        effort="medium",
    ),
    # -------------------------------------------------------------------------
    # Tool Use
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.TOOL_USE,
        model="claude-sonnet-4-6",
        location=CodeLocation(file=_FILE, lines="200", function="classify_ticket"),
        current_state=CodeSnippet(
            description=(
                "All 8 tools are passed on every API call, even though ticket classification "
                "never needs to apply discounts, send emails, or update the CRM. "
                "Unused tools inflate the prompt (~1,500 tokens) and may confuse the model "
                "into making unintended tool calls."
            ),
            code_snippet="""\
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=SYSTEM_PROMPT,
    tools=ALL_TOOLS,   # ← all 8 tools sent on every call, most irrelevant for classification
    messages=[{"role": "user", "content": user_message}]
)
""",
            language="python",
        ),
        recommendation=Recommendation(
            title="Pass only the tools needed for the current task",
            description=(
                "Classification calls need zero tools, so remove them entirely. "
                "For full-resolution calls, pass only the relevant subset "
                "(e.g., lookup_customer + escalate_ticket). "
                "Fewer tools means a smaller prompt, lower cost, and fewer hallucinated calls."
            ),
            docs_url="https://docs.anthropic.com/en/docs/build-with-claude/tool-use/best-practices-for-tool-definitions",
        ),
        suggested_fix=CodeSnippet(
            description="Remove tools from the classification call; use a scoped subset for resolution calls",
            code_snippet="""\
# Classification needs no tools, remove them entirely
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
    # tools parameter omitted (saves ~1,500 tokens per call)
    messages=[{"role": "user", "content": user_message}]
)

# For a resolution call that may look up a customer or escalate:
RESOLUTION_TOOLS = [lookup_customer_tool, escalate_ticket_tool, search_knowledge_base_tool]
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
    tools=RESOLUTION_TOOLS,   # ← only the 3 tools actually needed
    messages=[{"role": "user", "content": user_message}]
)
""",
            language="python",
        ),
        impact=Impact(
            cost_reduction="medium",
            latency_reduction="medium",
            reliability_improvement="medium",
            estimated_savings_detail=(
                "Removes unnecessary tool definitions from every call, cutting input costs by 30-60% on this endpoint."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # Model Upgrade
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.MODEL_UPGRADE,
        model="claude-sonnet-4-5-20250514",
        location=CodeLocation(file=_FILE, lines="196-204", function="classify_ticket"),
        current_state=CodeSnippet(
            description=(
                "The API call uses claude-sonnet-4-5-20250514, an older Sonnet version. "
                "Claude Sonnet 4.6 is available at the same price with better performance, "
                "lower latency, and improved instruction following. Note: the code also "
                "prefills the assistant message to force JSON output. This will return a "
                "400 error on Sonnet 4.6, so it must be removed as part of the upgrade."
            ),
            code_snippet="""\
response = client.messages.create(
    model="claude-sonnet-4-5-20250514",   # ← outdated model version (sample uses claude-sonnet-4-6 but this demo illustrates the upgrade path)
    max_tokens=1024,
    system=SYSTEM_PROMPT,
    tools=ALL_TOOLS,
    messages=[
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": "{"},   # ← prefill breaks on 4.6
    ]
)
""",
            language="python",
        ),
        recommendation=Recommendation(
            title="Upgrade from Sonnet 4.5 to Sonnet 4.6",
            description=(
                "Claude Sonnet 4.6 is the latest Sonnet model at the same price "
                "($3/MTok input, $15/MTok output) with better reasoning, lower latency, "
                "and latest API features.\n\n"
                "**Breaking change:** Prefilling assistant messages (used here to force JSON "
                "output) returns a 400 error on Sonnet 4.6. Replace with structured outputs "
                "or system prompt instructions.\n\n"
                "**Latency note:** Sonnet 4.6 defaults to effort level 'high', which may "
                "increase latency compared to Sonnet 4.5. Set `output_config={\"effort\": \"low\"}` "
                "for latency-sensitive use cases."
            ),
            docs_url="https://platform.claude.com/docs/en/about-claude/models/migration-guide",
        ),
        suggested_fix=CodeSnippet(
            description=(
                "Upgrade model to Sonnet 4.6, remove assistant prefill, "
                "and set effort level to control latency"
            ),
            code_snippet="""\
response = client.messages.create(
    model="claude-sonnet-4-6",            # ← upgraded to latest Sonnet
    max_tokens=1024,
    system=SYSTEM_PROMPT,
    tools=ALL_TOOLS,
    output_config={"effort": "low"},      # ← match Sonnet 4.5 latency profile
    messages=[{"role": "user", "content": user_message}]
    # Prefill removed. Use structured outputs for guaranteed JSON
)
""",
            language="python",
        ),
        impact=Impact(
            cost_reduction="low",
            latency_reduction="medium",
            reliability_improvement="medium",
            estimated_savings_detail=(
                "Free upgrade: same price, better performance, and lower latency. Fewer retries from improved instruction following."
            ),
        ),
        confidence="high",
        effort="medium",
    ),
    # -------------------------------------------------------------------------
    # Structured Outputs
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.STRUCTURED_OUTPUTS,
        model="claude-sonnet-4-6",
        location=CodeLocation(
            file=_FILE, lines="193-235", function="classify_ticket"
        ),
        current_state=CodeSnippet(
            description=(
                "The code asks Claude to 'return JSON' in the prompt, then tries json.loads, "
                "falls back to regex extraction, and retries up to 3 times with exponential "
                "backoff. This is fragile: Claude may wrap JSON in markdown fences, add "
                "commentary, or produce subtle schema mismatches."
            ),
            code_snippet="""\
max_retries = 3
for attempt in range(max_retries):
    try:
        response = client.messages.create(...)
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        result = None
        try:
            result = json.loads(response_text)       # ← may fail on markdown fences
        except json.JSONDecodeError:
            json_match = re.search(r'\\{[^{}]*"category"[^{}]*\\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())  # ← brittle regex fallback

        if result and "category" in result:
            return result
        print(f"Attempt {attempt + 1}: Could not parse response, retrying...")
    except Exception as e:
        time.sleep(2 ** attempt)   # ← wastes seconds on fixable parse errors
""",
            language="python",
        ),
        recommendation=Recommendation(
            title="Use native structured outputs instead of 'return JSON' prompts",
            description=(
                "Claude's structured outputs feature guarantees the response matches your "
                "Pydantic schema on every call. No retries, no regex, no exponential backoff. "
                "Use client.messages.parse() with an output_schema argument."
            ),
            docs_url="https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs",
        ),
        suggested_fix=CodeSnippet(
            description="Define a Pydantic schema and use client.messages.parse() for guaranteed structured output",
            code_snippet="""\
from pydantic import BaseModel

class TicketClassification(BaseModel):
    category: str   # "shipping" | "returns" | "billing" | "technical" | "general"
    priority: str   # "low" | "medium" | "high" | "urgent"
    suggested_response: str

def classify_ticket(ticket: dict) -> dict:
    \"\"\"Classify a ticket using native structured outputs. No retries needed.\"\"\"
    response = client.messages.parse(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": _build_user_message(ticket)}],
        output_schema=TicketClassification,
    )

    # response.parsed is a validated TicketClassification, always correct shape
    result = response.parsed
    return {
        "category": result.category,
        "priority": result.priority,
        "suggested_response": result.suggested_response,
        "ticket_id": ticket["id"],
    }
""",
            language="python",
        ),
        impact=Impact(
            cost_reduction="low",
            latency_reduction="medium",
            reliability_improvement="high",
            estimated_savings_detail=(
                "Eliminates all parsing retries. With the current ~30% failure rate, that's roughly a third of calls you stop paying for twice."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # CLAUDE.md Context Bloat
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.CLAUDE_MD_BLOAT,
        model="",
        location=CodeLocation(file=_CLAUDE_MD, lines="1-95"),
        current_state=CodeSnippet(
            description=(
                "CLAUDE.md is ~3,200 tokens and loaded on every Claude Code turn. "
                "It contains an 800-token deployment guide and a 400-token testing "
                "section that are only needed for specific workflows, plus 200 tokens "
                "of duplicate style guidelines and 3 references to files that no longer exist."
            ),
            code_snippet="""\
# ShopFlow Support Classifier

## Project Overview
This is the ShopFlow customer support ticket classifier...
(~200 tokens of project description)

## Code Style Guidelines
- Use type hints for all function parameters and return values
- Use type hints on every function signature
- Always annotate function arguments with types
(duplicate instructions, same concept stated 3 ways)

## Deployment Guide
### Prerequisites
- AWS CLI configured with production credentials
- Docker 24+ installed
- Access to the shopflow-prod ECR repository
### Steps
1. Build the Docker image: `docker build -t shopflow-classifier .`
2. Tag for ECR: `docker tag shopflow-classifier:latest ...`
3. Push to ECR: `docker push ...`
4. Update ECS task definition...
5. Run database migrations...
(~800 tokens of deployment instructions)

## Testing Instructions
### Unit Tests
Run `pytest tests/unit -v` for unit tests...
### Integration Tests
Set up test database with `docker compose up -d postgres`...
(~400 tokens of testing instructions)

## File References
- See `src/legacy_router.py` for the old routing logic
- Config in `config/staging.yaml` for staging environment
- Check `scripts/deploy_v1.sh` for the old deploy script
(none of these files exist in the project)
""",
            language="markdown",
        ),
        recommendation=Recommendation(
            title="Reduce CLAUDE.md from 3,200 to ~1,100 tokens by extracting workflow sections",
            description=(
                "CLAUDE.md loads into context on every single Claude Code turn. At 3,200 tokens "
                "across a 30-turn session, that's ~96,000 tokens of repeated context.\n\n"
                "Extract the Deployment Guide (800 tokens) and Testing Instructions (400 tokens) "
                "into on-demand command files under `.claude/commands/`. These only load when "
                "explicitly invoked (e.g., `/project:deploy`), not on every turn.\n\n"
                "Also remove duplicate style guidelines and stale file references to files "
                "that no longer exist in the project."
            ),
            docs_url="https://docs.anthropic.com/en/docs/claude-code/memory",
        ),
        suggested_fix=CodeSnippet(
            description=(
                "Optimized CLAUDE.md (~1,100 tokens) with deployment and testing "
                "extracted to .claude/commands/"
            ),
            code_snippet="""\
# ShopFlow Support Classifier

## Overview
Customer support ticket classifier using Claude API. Categorizes tickets
by type and priority, generates draft responses.

## Stack
- Python 3.11, FastAPI, Pydantic
- Claude Sonnet 4.6 via Anthropic SDK
- PostgreSQL for ticket storage

## Conventions
- Type hints on all function signatures and return values
- Pydantic models for all API request/response schemas
- XML tags in prompts to separate concerns

## Key Files
- `classifier.py`: main classification logic and API calls
- `sample_tickets.json`: test fixture data

---
Extracted to on-demand commands:
- `.claude/commands/deploy.md`: deployment guide (invoke with /project:deploy)
- `.claude/commands/test.md`: testing instructions (invoke with /project:test)
""",
            language="markdown",
        ),
        impact=Impact(
            cost_reduction="high",
            latency_reduction="medium",
            reliability_improvement="medium",
            estimated_savings_detail=(
                "Cuts ~2,100 tokens per turn. Over a 30-turn session, that's ~63,000 fewer "
                "repeated context tokens, a 66% reduction in CLAUDE.md overhead."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # Claudeignore Quality
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.CLAUDEIGNORE_QUALITY,
        model="",
        location=CodeLocation(file=".", lines=""),
        current_state=CodeSnippet(
            description=(
                "No .claudeignore file exists. The project has __pycache__/ directories, "
                "a .pytest_cache/ directory, and requirements.txt lockfile content that Claude "
                "Code may read unnecessarily, adding noise to its context."
            ),
            code_snippet=(
                "# No .claudeignore file found\n"
                "#\n"
                "# Directories that should be excluded:\n"
                "# - __pycache__/ (Python bytecode cache)\n"
                "# - .pytest_cache/ (test runner cache)\n"
                "# - *.pyc (compiled Python files)\n"
                "# - .venv/ or venv/ (if virtual environment exists)"
            ),
            language="bash",
        ),
        recommendation=Recommendation(
            title="Create .claudeignore to exclude build artifacts and caches",
            description=(
                "The .claudeignore file works like .gitignore: it tells Claude Code which files "
                "to skip when reading the project. Without it, Claude may waste context on "
                "bytecode caches, test artifacts, and other generated content that adds no value "
                "to code analysis.\n\n"
                "This is especially important as projects grow. A .claudeignore keeps Claude "
                "focused on actual source code."
            ),
            docs_url="https://docs.anthropic.com/en/docs/claude-code/memory#claudeignore",
        ),
        suggested_fix=CodeSnippet(
            description="A .claudeignore file tailored to this Python project",
            code_snippet=(
                "# Python\n"
                "__pycache__/\n"
                "*.pyc\n"
                "*.pyo\n"
                ".venv/\n"
                "venv/\n"
                "\n"
                "# Test caches\n"
                ".pytest_cache/\n"
                "htmlcov/\n"
                "coverage/\n"
                "\n"
                "# IDE\n"
                ".idea/\n"
                ".vscode/\n"
                "\n"
                "# OS\n"
                ".DS_Store\n"
                "Thumbs.db"
            ),
            language="gitignore",
        ),
        impact=Impact(
            cost_reduction="medium",
            latency_reduction="low",
            reliability_improvement="medium",
            estimated_savings_detail=(
                "Prevents Claude from reading cache files and build artifacts, "
                "reducing context noise and improving response relevance."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # Custom Commands Quality
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.COMMANDS_QUALITY,
        model="",
        location=CodeLocation(file=".", lines=""),
        current_state=CodeSnippet(
            description=(
                "No .claude/commands/ directory exists. The project has deployment workflows "
                "(Docker + AWS), database migrations, and a multi-stage test pipeline that "
                "are documented in CLAUDE.md but would be better as on-demand commands."
            ),
            code_snippet=(
                "# No .claude/commands/ directory found\n"
                "#\n"
                "# Detected workflows that should be commands:\n"
                "# 1. Deployment: Docker build + ECR push + EKS deploy (from CLAUDE.md)\n"
                "# 2. Testing: unit + integration + E2E pipeline (from CLAUDE.md)\n"
                "# 3. Database: Alembic migration workflow (from requirements.txt)"
            ),
            language="bash",
        ),
        recommendation=Recommendation(
            title="Create custom commands for deployment and testing workflows",
            description=(
                "Custom commands under .claude/commands/ are loaded on-demand via "
                "/project:<name>, not on every turn like CLAUDE.md. Moving the 800-token "
                "deployment guide and 400-token testing instructions from CLAUDE.md to "
                "commands would reduce per-turn context by ~1,200 tokens while keeping "
                "these workflows easily accessible.\n\n"
                "Commands also support $ARGUMENTS for parameterization, making them more "
                "flexible than static CLAUDE.md content."
            ),
            docs_url="https://docs.anthropic.com/en/docs/claude-code/slash-commands",
        ),
        suggested_fix=CodeSnippet(
            description="Two custom commands extracted from CLAUDE.md workflow sections",
            code_snippet=(
                "# .claude/commands/deploy.md\n"
                "---\n"
                "description: Build, push, and deploy the classifier to production\n"
                "---\n"
                "Deploy the ShopFlow classifier. If $ARGUMENTS specifies an environment\n"
                "(staging/production), deploy there. Otherwise default to staging.\n"
                "\n"
                "Steps:\n"
                "1. Build: `docker build -t shopflow-classifier .`\n"
                "2. Tag for ECR: `docker tag shopflow-classifier:latest ...`\n"
                "3. Push: `docker push ...`\n"
                "4. Deploy: `kubectl apply -f k8s/deployment.yaml`\n"
                "5. Verify: `kubectl rollout status deployment/shopflow-classifier`\n"
                "\n"
                "# .claude/commands/test.md\n"
                "---\n"
                "description: Run tests. Pass a specific test path or run the full suite.\n"
                "---\n"
                "Run tests. If $ARGUMENTS is provided, run that specific test path.\n"
                "Otherwise run the full pipeline:\n"
                "\n"
                "1. Unit: `pytest tests/unit -v --cov=src`\n"
                "2. Integration: `docker compose up -d postgres-test &&\n"
                "   pytest tests/integration -v --timeout=60`\n"
                "3. E2E: `docker compose up -d && pytest tests/e2e -v --timeout=120`"
            ),
            language="markdown",
        ),
        impact=Impact(
            cost_reduction="medium",
            latency_reduction="low",
            reliability_improvement="medium",
            estimated_savings_detail=(
                "Moves ~1,200 tokens of workflow instructions from always-loaded CLAUDE.md "
                "to on-demand commands. Over 30 turns, saves ~36,000 context tokens."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # Settings & Permissions
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.SETTINGS_PERMISSIONS,
        model="",
        location=CodeLocation(file=_CLAUDE_SETTINGS, lines="1-25"),
        current_state=CodeSnippet(
            description=(
                "The .claude/settings.json file has MCP servers configured with API tokens "
                "directly in the committed file (GITHUB_TOKEN, SLACK_BOT_TOKEN, LINEAR_API_KEY). "
                "No permission rules are defined, meaning Claude Code will prompt for approval "
                "on every tool use. No deny rules protect against destructive operations."
            ),
            code_snippet=(
                '{\n'
                '  "mcpServers": {\n'
                '    "github": {\n'
                '      "command": "npx",\n'
                '      "args": ["-y", "@anthropic-ai/github-mcp"],\n'
                '      "env": { "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx" }\n'
                '    },\n'
                '    "slack": {\n'
                '      "env": { "SLACK_BOT_TOKEN": "xoxb-xxxxxxxxxxxx" }\n'
                '    }\n'
                '  }\n'
                '}'
            ),
            language="json",
        ),
        recommendation=Recommendation(
            title="Move secrets to settings.local.json and add permission rules",
            description=(
                "API tokens (GITHUB_TOKEN, SLACK_BOT_TOKEN) are in .claude/settings.json, which "
                "is committed to version control. These should be in .claude/settings.local.json "
                "(gitignored) instead.\n\n"
                "Additionally, adding permission rules reduces friction for safe operations and "
                "adds guardrails for dangerous ones. Allow read-only tools and common safe commands; "
                "deny destructive operations like rm -rf and git push --force."
            ),
            docs_url="https://docs.anthropic.com/en/docs/claude-code/settings",
        ),
        suggested_fix=CodeSnippet(
            description="Split settings: shared config in settings.json, secrets in settings.local.json",
            code_snippet=(
                "# .claude/settings.json (committed, shared with team)\n"
                "{\n"
                '  "mcpServers": {\n'
                '    "github": {\n'
                '      "command": "npx",\n'
                '      "args": ["-y", "@anthropic-ai/github-mcp"]\n'
                "    }\n"
                "  },\n"
                '  "permissions": {\n'
                '    "allow": [\n'
                '      "Read", "Glob", "Grep",\n'
                '      "Bash(pytest *)", "Bash(python *)", "Bash(git status)", "Bash(git diff)"\n'
                "    ],\n"
                '    "deny": [\n'
                '      "Bash(rm -rf *)", "Bash(git push --force *)", "Bash(git reset --hard *)"\n'
                "    ]\n"
                "  }\n"
                "}\n\n"
                "# .claude/settings.local.json (gitignored, per-developer secrets)\n"
                "{\n"
                '  "mcpServers": {\n'
                '    "github": {\n'
                '      "env": { "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx" }\n'
                "    }\n"
                "  }\n"
                "}"
            ),
            language="json",
        ),
        impact=Impact(
            cost_reduction="low",
            latency_reduction="low",
            reliability_improvement="high",
            estimated_savings_detail=(
                "Prevents API tokens from being exposed in version control and adds "
                "guardrails against accidental destructive commands."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # Skills Quality
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.SKILLS_QUALITY,
        model="",
        location=CodeLocation(file=".claude/", lines=""),
        current_state=CodeSnippet(
            description=(
                "No .claude/skills/ directory exists. The CLAUDE.md file contains ~800 tokens "
                "of deployment-specific domain knowledge and ~400 tokens of testing procedures "
                "that would be better served as skills. Skills load on-demand when triggered "
                "by matching context, keeping CLAUDE.md lean."
            ),
            code_snippet=(
                "# No .claude/skills/ directory found\n"
                "#\n"
                "# CLAUDE.md contains domain-specific content suitable for skills:\n"
                "# - Deployment Guide (~800 tokens): Docker + ECR + EKS procedures\n"
                "# - Testing Pipeline (~400 tokens): unit, integration, E2E instructions\n"
                "# - API Integration Notes (~200 tokens): Claude API patterns"
            ),
            language="bash",
        ),
        recommendation=Recommendation(
            title="Create skills for deployment and API integration workflows",
            description=(
                "Skills (.claude/skills/<name>/SKILL.md) are loaded when Claude Code detects "
                "matching context, not on every turn. They're ideal for domain-specific knowledge "
                "that only applies to certain tasks.\n\n"
                "Per Anthropic's best practices:\n"
                "- Use gerund-form names (e.g., 'deploying-to-production')\n"
                "- Write descriptions in third person with trigger conditions\n"
                "- Scope allowed-tools to what the skill actually needs\n"
                "- Keep body under 500 lines"
            ),
            docs_url="https://docs.anthropic.com/en/docs/claude-code/skills",
        ),
        suggested_fix=CodeSnippet(
            description="A deployment skill with proper frontmatter following Anthropic best practices",
            code_snippet=(
                "# .claude/skills/deploying-to-production/SKILL.md\n"
                "---\n"
                "name: deploying-to-production\n"
                "description: Handles building, pushing, and deploying the ShopFlow classifier\n"
                "  to production EKS. Triggers when the user asks to deploy, release, or push\n"
                "  to production.\n"
                "allowed-tools:\n"
                "  - Read\n"
                "  - Bash(docker *)\n"
                "  - Bash(kubectl *)\n"
                "  - Bash(aws ecr *)\n"
                "---\n"
                "\n"
                "## Deployment Checklist\n"
                "\n"
                "- [ ] All tests pass (`pytest tests/ -v`)\n"
                "- [ ] Build Docker image: `docker build -t shopflow-classifier .`\n"
                "- [ ] Tag for ECR: `docker tag shopflow-classifier:latest 123456789.dkr.ecr...`\n"
                "- [ ] Push: `docker push 123456789.dkr.ecr...`\n"
                "- [ ] Apply: `kubectl apply -f k8s/deployment.yaml`\n"
                "- [ ] Verify: `kubectl rollout status deployment/shopflow-classifier`\n"
                "\n"
                "## Rollback\n"
                "If deployment fails: `kubectl rollout undo deployment/shopflow-classifier`"
            ),
            language="markdown",
        ),
        impact=Impact(
            cost_reduction="medium",
            latency_reduction="low",
            reliability_improvement="high",
            estimated_savings_detail=(
                "Moves domain knowledge from always-loaded CLAUDE.md to triggered skills. "
                "Reduces per-turn context and gives Claude structured, task-specific guidance "
                "when deployment tasks are detected."
            ),
        ),
        confidence="medium",
        effort="medium",
    ),
    # -------------------------------------------------------------------------
    # Context Budget
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.CONTEXT_BUDGET,
        model="",
        location=CodeLocation(file=".", lines=""),
        current_state=CodeSnippet(
            description=(
                "Total baseline context loaded on every turn: ~26,200 tokens. This exceeds "
                "the recommended 20,000-token ceiling.\n\n"
                "Breakdown:\n"
                "- CLAUDE.md: ~3,200 tokens\n"
                "- MCP tool definitions: ~13,000 tokens (65 tools across 3 servers)\n"
                "- Other context: ~10,000 tokens (system prompt, tool descriptions)\n\n"
                "The largest contributor is MCP tools (50%), followed by CLAUDE.md (12%)."
            ),
            code_snippet=(
                "# Baseline context budget (loaded every turn)\n"
                "#\n"
                "# CLAUDE.md:     ~3,200 tokens (12%)\n"
                "#   - Project overview:    ~200 tokens\n"
                "#   - Style guidelines:    ~300 tokens (includes duplicates)\n"
                "#   - Deployment guide:    ~800 tokens\n"
                "#   - Testing instructions: ~400 tokens\n"
                "#   - Stale references:    ~100 tokens\n"
                "#   - Other:               ~1,400 tokens\n"
                "#\n"
                "# MCP tools:    ~13,000 tokens (50%)\n"
                "#   - github:   ~30 tools x 200 = ~6,000 tokens (6 used)\n"
                "#   - slack:    ~20 tools x 200 = ~4,000 tokens (3 used)\n"
                "#   - linear:   ~15 tools x 200 = ~3,000 tokens (0 used)\n"
                "#\n"
                "# TOTAL:        ~26,200 tokens per turn\n"
                "# RECOMMENDED:  <20,000 tokens per turn\n"
                "# OVER BUDGET:  ~6,200 tokens (31% over)"
            ),
            language="bash",
        ),
        recommendation=Recommendation(
            title="Reduce baseline context from ~26,200 to under 20,000 tokens",
            description=(
                "Every token in baseline context is repeated on every Claude Code turn. At "
                "26,200 tokens across 30 turns, that's ~786,000 tokens per session. Quality "
                "degrades noticeably past 20,000 tokens of baseline context.\n\n"
                "Biggest wins:\n"
                "1. Add allowedTools to MCP servers: reduces MCP from ~13,000 to ~1,800 tokens "
                "(9 tools actually used). Saves ~11,200 tokens.\n"
                "2. Extract CLAUDE.md workflow sections to commands/skills: reduces CLAUDE.md "
                "from ~3,200 to ~1,100 tokens. Saves ~2,100 tokens.\n\n"
                "Combined, this brings total to ~12,900 tokens, well under the 20,000 ceiling."
            ),
            docs_url="https://docs.anthropic.com/en/docs/claude-code/best-practices",
        ),
        suggested_fix=CodeSnippet(
            description="Optimized context budget breakdown after applying recommendations",
            code_snippet=(
                "# Optimized baseline context budget\n"
                "#\n"
                "# CLAUDE.md:     ~1,100 tokens (was 3,200)\n"
                "#   - Extracted deployment guide to .claude/commands/deploy.md\n"
                "#   - Extracted testing instructions to .claude/commands/test.md\n"
                "#   - Removed duplicate style guidelines\n"
                "#   - Removed stale file references\n"
                "#\n"
                "# MCP tools:    ~1,800 tokens (was 13,000)\n"
                "#   - github: 6 allowed tools x 200 = ~1,200 tokens\n"
                "#   - slack:  3 allowed tools x 200 = ~600 tokens\n"
                "#   - linear: removed (unused)\n"
                "#\n"
                "# TOTAL:        ~12,900 tokens per turn\n"
                "# SAVINGS:      ~13,300 tokens per turn (51% reduction)\n"
                "# PER SESSION:  ~399,000 fewer tokens across 30 turns"
            ),
            language="bash",
        ),
        impact=Impact(
            cost_reduction="high",
            latency_reduction="medium",
            reliability_improvement="medium",
            estimated_savings_detail=(
                "Reduces per-turn baseline context by 51%, from ~26,200 to ~12,900 tokens. "
                "Improves response quality and cuts session costs significantly."
            ),
        ),
        confidence="medium",
        effort="medium",
    ),
    # -------------------------------------------------------------------------
    # MCP Tool Definition Bloat
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.MCP_TOOL_BLOAT,
        model="",
        location=CodeLocation(file=_CLAUDE_SETTINGS, lines="1-25"),
        current_state=CodeSnippet(
            description=(
                "3 MCP servers configured with no allowedTools filters. All tools from "
                "each server load into context on every turn, even tools never referenced "
                "in the project. The Linear MCP server has zero tool references in the "
                "codebase, suggesting it may be unused."
            ),
            code_snippet="""\
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/github-mcp"],
      "env": { "GITHUB_TOKEN": "..." }
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/slack-mcp"],
      "env": { "SLACK_BOT_TOKEN": "...", "SLACK_TEAM_ID": "..." }
    },
    "linear": {
      "command": "npx",
      "args": ["-y", "linear-mcp-server"],
      "env": { "LINEAR_API_KEY": "..." }
    }
  }
}
""",
            language="json",
        ),
        recommendation=Recommendation(
            title="Add allowedTools filters to scope MCP servers and remove unused Linear server",
            description=(
                "Each MCP server exposes its full tool set into Claude's context on every turn. "
                "GitHub MCP has ~30 tools, Slack ~20, Linear ~15, totaling ~65 tool definitions "
                "(~13,000 tokens) loaded every turn, most of which are never used.\n\n"
                "Only 6 GitHub tools and 3 Slack tools are referenced in the codebase. The Linear "
                "server has zero references. Consider removing it entirely.\n\n"
                "Add `allowedTools` arrays to `.claude/settings.json` to scope each server to only "
                "the tools you actually use. This reduces context size and improves tool selection accuracy."
            ),
            docs_url="https://docs.anthropic.com/en/docs/claude-code/mcp",
        ),
        suggested_fix=CodeSnippet(
            description="Scoped MCP config with allowedTools filters and unused server removed",
            code_snippet="""\
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/github-mcp"],
      "env": { "GITHUB_TOKEN": "..." }
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/slack-mcp"],
      "env": { "SLACK_BOT_TOKEN": "...", "SLACK_TEAM_ID": "..." }
    }
  },
  "allowedTools": [
    "mcp__github__create_issue",
    "mcp__github__list_pulls",
    "mcp__github__get_file",
    "mcp__github__create_pull",
    "mcp__github__search_code",
    "mcp__github__get_repo",
    "mcp__slack__post_message",
    "mcp__slack__search_messages",
    "mcp__slack__list_channels"
  ]
}
""",
            language="json",
        ),
        impact=Impact(
            cost_reduction="medium",
            latency_reduction="medium",
            reliability_improvement="medium",
            estimated_savings_detail=(
                "Removes ~56 unused tool definitions from context (~11,200 tokens per turn). "
                "Over a 30-turn session, that's ~336,000 fewer tokens. Fewer tools also means "
                "more accurate tool selection."
            ),
        ),
        confidence="high",
        effort="low",
    ),

    # -------------------------------------------------------------------------
    # Skills from Chat History
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.SKILLS_FROM_HISTORY,
        model="",
        location=CodeLocation(file=".claude/skills/"),
        current_state=CodeSnippet(
            description=(
                "The user repeatedly asks Claude to review all changes before pushing. "
                "This exact workflow appeared 7 times across 4 sessions with near-identical wording."
            ),
            code_snippet=(
                "Examples from chat history:\n\n"
                '1. "Review all my changes for bugs, security issues, and inefficiencies before I push"\n'
                '2. "Go through the diff and check for any issues - bugs, bad patterns, security problems"\n'
                '3. "Before I push, review everything I changed and flag anything wrong"\n'
                '4. "Check all my changes for bugs and improvements before I commit"'
            ),
            language="markdown",
        ),
        recommendation=Recommendation(
            title="Create a pre-push review skill to replace repeated prompts",
            description=(
                "This is the most common repeated workflow in your chat history. Instead of "
                "typing this prompt every time, create a Skill that Claude auto-triggers when "
                "you mention reviewing or pushing changes. The skill encapsulates your review "
                "checklist so it's consistent every time and you never forget a step."
            ),
            docs_url="https://docs.anthropic.com/en/docs/claude-code/skills",
        ),
        suggested_fix=CodeSnippet(
            description="Create .claude/skills/reviewing-changes/SKILL.md with this content:",
            code_snippet="""\
---
name: reviewing-changes
description: Reviews all staged and unstaged code changes for bugs, security
  issues, performance problems, and code quality. Triggers when the user asks
  to review changes before pushing, committing, or creating a PR.
allowed-tools:
  - Read
  - Bash(git diff)
  - Bash(git diff --cached)
  - Bash(git status)
  - Bash(git log -10 --oneline)
  - Grep
  - Glob
---

## Pre-Push Code Review Checklist

Review every changed file (`git diff` and `git diff --cached`) against this checklist:

### Security
- No secrets, API keys, or credentials in code or config
- No SQL injection, XSS, or command injection vectors
- Input validation on all external boundaries

### Correctness
- No off-by-one errors, null pointer risks, or unhandled edge cases
- Error handling covers failure modes
- Types are correct and consistent

### Performance
- No N+1 queries or unnecessary loops
- No blocking calls in async paths
- Resource cleanup (close files, connections, cursors)

### Code Quality
- No dead code, unused imports, or commented-out blocks
- Naming is clear and consistent
- No duplicated logic that should be extracted

Report findings grouped by severity (critical > warning > suggestion).\
""",
            language="markdown",
        ),
        impact=Impact(
            cost_reduction="low",
            latency_reduction="medium",
            reliability_improvement="high",
            estimated_savings_detail=(
                "Replaces a manually typed prompt with a consistent, auto-triggered skill — "
                "ensuring the same thorough review every time with zero effort."
            ),
        ),
        confidence="high",
        effort="low",
    ),
]
