from analyzers.base import build_agentic_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

You are analyzing a project's total baseline context budget: the tokens loaded into Claude
Code's context on EVERY turn of EVERY conversation. This is the "always-on" cost that
compounds across all turns in a session. Community best practice recommends keeping total
baseline context under 20,000 tokens. Quality degrades noticeably past this threshold.

This is a cross-cutting analyzer. It measures the combined token footprint of all
always-loaded context sources and identifies the biggest optimization opportunities.

---

HOW TO MEASURE:

1. **CLAUDE.md tokens**
   Read the CLAUDE.md file at the project root. Estimate its token count using the
   approximation: 1 token ~ 4 characters.

   If CLAUDE.md uses @-file includes (e.g., `@AGENTS.md`, `@docs/conventions.md`), read
   each referenced file and add its tokens to the CLAUDE.md total. These inclusions are
   expanded on every turn, so they contribute to baseline context even if the user rarely
   needs that content.

   Also check for nested CLAUDE.md files in subdirectories (e.g., src/CLAUDE.md,
   frontend/CLAUDE.md). Each one adds to baseline context when working in that directory.

2. **MCP tool definition tokens**
   Read .claude/settings.json and .claude/settings.local.json. For each configured MCP
   server, estimate tool definition tokens:

   Known server tool counts (use these if the server name matches):
   - github / @anthropic-ai/github-mcp: ~30 tools x 200 tokens = ~6,000 tokens
   - slack: ~20 tools x 200 = ~4,000 tokens
   - linear: ~15 tools x 200 = ~3,000 tokens
   - filesystem / @anthropic-ai/filesystem-mcp: ~10 tools x 200 = ~2,000 tokens
   - postgres / database / sqlite: ~10 tools x 200 = ~2,000 tokens
   - browser / puppeteer: ~15 tools x 200 = ~3,000 tokens

   If the server has an "allowedTools" array, use that count instead of the full tool set:
   allowed_tool_count x 200 tokens.

   For unknown servers, estimate ~15 tools x 200 = ~3,000 tokens and note the uncertainty.

3. **Auto-memory and other context files**
   Check .claude/ directory for additional context files (memory files, project notes).
   Estimate their combined token count.

---

ANALYSIS:

Calculate the total: CLAUDE.md_tokens + MCP_tool_tokens + other_context_tokens.

**Create ONE finding if total exceeds 20,000 tokens.** This finding should:
- Break down the total by source: "CLAUDE.md: ~X tokens, MCP tools: ~Y tokens, other: ~Z tokens"
- Identify the #1 contributor and recommend the single highest-impact reduction
- Calculate per-session impact: total_baseline_tokens x 30 turns = tokens_per_session
- Provide a concrete suggested_fix showing how to reduce the biggest contributor

Specific recommendations to include based on what's consuming the most:
- If CLAUDE.md is the biggest: recommend extracting workflow sections to .claude/commands/
  (loaded on-demand, not every turn) and domain knowledge to .claude/skills/ (loaded when
  triggered). Calculate how many tokens would be saved.
- If MCP tools are the biggest: recommend adding allowedTools filters to the largest servers
  (reference the mcp_tool_bloat analyzer for details).
- If @-file includes are inflating CLAUDE.md: flag this as an anti-pattern. Large documents
  pulled in via @-references load on every turn even when rarely needed. Recommend moving
  to commands or skills.

**Also create a separate finding if CLAUDE.md alone exceeds 2,000 tokens**, even if total is
under 20,000. A 2,000-token CLAUDE.md is the recommended ceiling for the project memory file.
This helps keep per-turn costs low and ensures Claude reads and follows all instructions
(compliance drops as CLAUDE.md grows larger).

---

REPORT STRUCTURE:
- Location: "." (project root) for the total budget finding
- Location: "CLAUDE.md" for the CLAUDE.md-specific finding
- current_state: show the breakdown with approximate token counts per source
- suggested_fix: show the specific changes to reduce the biggest contributor

IMPACT ESTIMATION:
- Total budget over 20k: cost_reduction "high", latency_reduction "medium",
  reliability_improvement "medium"
- CLAUDE.md over 2,000 tokens: cost_reduction "medium", latency_reduction "low",
  reliability_improvement "medium"

CONFIDENCE:
- "medium" for all findings (these are estimates based on character counts and known
  server tool counts, not exact token measurements)

WHEN NOT TO FLAG:
- If total baseline context is under 20,000 tokens AND CLAUDE.md is under 2,000 tokens,
  return [].
- If no CLAUDE.md exists and no MCP servers are configured, return [].
  (The claude_md_bloat analyzer handles the "missing CLAUDE.md" case.)

DOCS REFERENCES:
- CLAUDE.md: https://docs.anthropic.com/en/docs/claude-code/memory
- MCP: https://docs.anthropic.com/en/docs/claude-code/mcp
- Best practices: https://docs.anthropic.com/en/docs/claude-code/best-practices
"""


def build_prompt() -> str:
    return build_agentic_base_prompt("context_budget", ANALYSIS_INSTRUCTIONS)
