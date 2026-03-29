"""Pre-generated findings for the bundled sample project demo.

When a scan is run against the bundled demo project, these findings are returned
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

DEMO_FINDINGS: list[Finding] = [
    # -------------------------------------------------------------------------
    # Prompt Engineering
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.PROMPT_ENGINEERING,
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
Return ONLY valid JSON — no prose, no markdown fences:
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
                "Reduces retry rate from ~30% to near zero, cutting wasted tokens "
                "and latency on malformed responses."
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
                "~90% cost reduction on the 2,000-token prompt after the first call. "
                "On a batch of 10 tickets, saves ~18,000 input tokens (~$0.054 at Sonnet pricing)."
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

    # Submit the entire backlog — 50% cost savings vs. sequential calls
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
                "50% token cost reduction on the entire batch. At 1,000 tickets/day "
                "with 2,000 input tokens each, saves ~$3/day at Sonnet pricing."
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
                "Classification calls need zero tools — remove them entirely. "
                "For full-resolution calls, pass only the relevant subset "
                "(e.g., lookup_customer + escalate_ticket). "
                "Fewer tools means a smaller prompt, lower cost, and fewer hallucinated calls."
            ),
            docs_url="https://docs.anthropic.com/en/docs/build-with-claude/tool-use/best-practices-for-tool-definitions",
        ),
        suggested_fix=CodeSnippet(
            description="Remove tools from the classification call; use a scoped subset for resolution calls",
            code_snippet="""\
# Classification needs no tools — remove them entirely
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
    # tools parameter omitted — saves ~1,500 tokens per call
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
                "Removes ~1,500 tokens of tool definitions per classification call. "
                "On 10 tickets that's ~15,000 tokens saved (~$0.045 at Sonnet input pricing)."
            ),
        ),
        confidence="high",
        effort="low",
    ),
    # -------------------------------------------------------------------------
    # Structured Outputs
    # -------------------------------------------------------------------------
    Finding(
        category=AnalyzerType.STRUCTURED_OUTPUTS,
        location=CodeLocation(
            file=_FILE, lines="193-235", function="classify_ticket"
        ),
        current_state=CodeSnippet(
            description=(
                "The code asks Claude to 'return JSON' in the prompt, then tries json.loads, "
                "falls back to regex extraction, and retries up to 3 times with exponential "
                "backoff. This is fragile — Claude may wrap JSON in markdown fences, add "
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
                "Pydantic schema on every call — no retries, no regex, no exponential backoff. "
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
    \"\"\"Classify a ticket using native structured outputs — no retries needed.\"\"\"
    response = client.messages.parse(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": _build_user_message(ticket)}],
        output_schema=TicketClassification,
    )

    # response.parsed is a validated TicketClassification — always correct shape
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
                "Eliminates retries (each wastes ~2,000 input + 200 output tokens). "
                "With a ~30% retry rate, saves ~660 tokens per ticket on average."
            ),
        ),
        confidence="high",
        effort="low",
    ),
]
