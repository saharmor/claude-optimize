from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

1. **Kitchen sink tool pattern**: All tools defined and passed to every API call regardless of the
   task. For example, passing 8 tools when only 2 are relevant to the current operation. Each tool
   definition consumes input tokens and dilutes the model's ability to select the right tool.

2. **Oversized tool descriptions**: Tool descriptions that are paragraphs long when a sentence would
   suffice. Verbose descriptions waste tokens and can confuse tool selection.

3. **Irrelevant tools for specific workflows**: Code paths where tools are included that could never
   be useful. For example, a "send_email" tool included in a read-only classification task.

4. **Manual parsing instead of tool use**: Code that asks Claude to output structured actions in
   prose and then regex-parses the response, instead of defining proper tools that Claude can call
   natively. Claude's native tool use is more reliable than text-based action parsing.

5. **Missing tool result handling**: Code that defines tools but doesn't properly handle the
   tool_use stop reason or tool result messages in multi-turn conversations.

6. **Missing tool_choice controls**: Cases where the application expects a specific tool call or
   wants to disallow tool use, but never sets `tool_choice`. Recommend `tool_choice` when it makes
   the interaction more deterministic or cheaper.

SCOPING RULES:
- Always flag the kitchen-sink tool pattern when a task clearly does not need most of the provided tools.
- Even if another analyzer also recommends structured outputs, still report tool-use issues that affect token cost or tool selection quality.
- Prefer the highest-leverage tool findings: usually one finding for scoped tool sets and one finding for oversized descriptions or missing `tool_choice`.

WHY TOOL OPTIMIZATION MATTERS:
- Each tool definition adds ~100-500 tokens to every request
- Fewer, more relevant tools improve selection accuracy
- Native tool use is more reliable than regex-based action parsing
- Scoping tools per task type can cut input token costs by 30-60%

MODEL-SPECIFIC TOOL CONSIDERATIONS:
- Unused tool definitions waste input tokens on every call. The more expensive the model, the bigger the waste.
- Scoping tools to only what's needed can cut input costs by 30-60% on tool-heavy calls.
- Identify the model from each API call and mention it in your finding.

DOCS REFERENCES:
- Tool use overview: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview
- Tool use best practices: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/best-practices
- Tool choice: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/implement-tool-use
"""


def build_prompt() -> str:
    return build_base_prompt("tool_use", ANALYSIS_INSTRUCTIONS)
