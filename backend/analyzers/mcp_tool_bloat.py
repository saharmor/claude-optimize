from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

You are analyzing a project's MCP (Model Context Protocol) server configuration for tool
definition bloat. Every tool from every configured MCP server is injected into Claude's
context on each turn. Unused tools waste tokens and can confuse tool selection.

1. **Find MCP configuration files**: Check these locations:
   - `.claude/settings.json` → look for "mcpServers" section
   - `.claude/settings.local.json` → local overrides
   - Any JSON files in the project referencing MCP server definitions
   Do NOT check the user's home directory (~/.claude/). Only check project-level configs.

2. **Check for allowedTools / disabledTools filters**: For each configured MCP server,
   check if `allowedTools` or `disabledTools` arrays are specified. If absent, the server's
   FULL tool set loads into context on every single turn, even tools never used.

3. **Scan codebase for tool usage patterns**: Search for references to MCP tools in:
   - CLAUDE.md files (may reference tool names in instructions)
   - `.claude/commands/` files (skill/command definitions may use specific tools)
   - Source code files (look for `mcp__<server>__<tool>` patterns)
   - Any documentation referencing specific MCP tool names

4. **Known MCP server tool counts**: For popular MCP servers, use these reference counts
   to estimate bloat even without connecting to the server:
   - github / @anthropic-ai/github-mcp: ~30 tools
   - slack: ~20 tools
   - linear: ~15 tools
   - filesystem / @anthropic-ai/filesystem-mcp: ~10 tools
   - postgres / database servers: ~10 tools
   - browser / puppeteer: ~15 tools
   For unknown servers, note that tool count can't be determined statically and suggest
   the user review their tool exposure.

5. **Flag unused MCP servers**: If a server is configured but zero tool references are found
   anywhere in the project, flag it as potentially unused. Recommend removing it or adding
   allowedTools to minimize context waste.

6. **Missing MCP configuration**: If NO MCP servers are configured but the project could
   benefit from them (e.g., it's a GitHub-hosted project, uses a database, has Slack
   integrations), suggest relevant MCP servers. However, only make this recommendation if
   there's clear evidence in the codebase (e.g., GitHub API calls, database queries,
   Slack webhook code). This is a LOWER confidence finding.

REPORT STRUCTURE:
- For each MCP server without allowedTools: list the server name, estimated total tools,
  tools actually referenced in code, and recommend a specific allowedTools array.
- Calculate estimated wasted tokens: (total_tools - used_tools) × ~200 tokens per tool
  definition × turns per session (assume 30 turns).
- The "location" should point to the config file where the MCP server is defined.
- The "current_state" code_snippet should show the MCP server config as-is.
- The "suggested_fix" should show the config with allowedTools added.

IMPACT ESTIMATION:
- cost_reduction: "high" if >20 unused tools across servers, "medium" for 10-20, "low" for <10.
- latency_reduction: "medium" (fewer tools = faster tool selection and smaller context).
- reliability_improvement: "medium" (fewer tools = less confusion in tool selection,
  fewer hallucinated tool calls).

WHEN TO RECOMMEND:
- Flag any MCP server without allowedTools filter (high confidence).
- Flag MCP servers with zero tool references in code (medium confidence, could be used
  interactively but not referenced in files).
- Only suggest NEW MCP servers if strong evidence exists (low confidence).
- If no MCP servers are configured and no evidence of need, return an empty array.

DOCS REFERENCES:
- MCP overview: https://docs.anthropic.com/en/docs/claude-code/mcp
- Claude Code settings: https://docs.anthropic.com/en/docs/claude-code/settings
"""


def build_prompt() -> str:
    return build_base_prompt("mcp_tool_bloat", ANALYSIS_INSTRUCTIONS)
