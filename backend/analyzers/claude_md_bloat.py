from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

You are analyzing a project's CLAUDE.md files for quality issues. CLAUDE.md is loaded into
Claude Code's context on EVERY turn of EVERY conversation. A bloated, empty, or poorly
structured CLAUDE.md directly impacts Claude Code's effectiveness.

Analyze the CLAUDE.md for ALL of the following issues. A single file can have multiple issues
(e.g., a stub file that's also missing key sections). Report each distinct issue as a
separate finding.

---

**ISSUE A: Missing CLAUDE.md**
If NO CLAUDE.md file exists at the project root, this is a finding. Recommend creating one.
A well-crafted CLAUDE.md helps Claude Code understand the project's conventions, tech stack,
and workflow patterns, leading to better code generation and fewer mistakes.
- Examine the project to understand its tech stack, structure, and key files.
- Suggest a concrete, ready-to-use CLAUDE.md (~500-800 tokens) as the suggested_fix,
  tailored to this specific project (not a generic template).

**ISSUE B: Stub or nearly empty CLAUDE.md**
If CLAUDE.md exists but is under ~100 tokens (~400 characters), it's essentially a stub.
Common patterns:
- Single-line redirect files (e.g., just `@AGENTS.md` or `See README.md`)
- Only a project title with no substance
- A few lines that don't convey any meaningful conventions or guidance
This is nearly as bad as missing. Claude Code loads it but gets no useful project context.
- Examine the project to understand what SHOULD be in the CLAUDE.md.
- Generate a concrete, project-specific CLAUDE.md as the suggested_fix.

**ISSUE C: Missing key sections**
Even if CLAUDE.md has content, check whether it covers the essential topics. A useful
CLAUDE.md should include most of these:
- **Project description**: What this project does (1-2 sentences)
- **Tech stack**: Languages, frameworks, key dependencies
- **Key conventions**: Coding style, naming patterns, architectural rules
- **Common commands**: How to build, test, lint, run the project
- **Key files/directories**: Entry points, important modules, config locations
Flag if 3 or more of these sections are missing. Suggest additions specific to the project
(examine the actual codebase to determine the real tech stack, test commands, etc.).

**ISSUE D: Context bloat (oversized)**
If CLAUDE.md is over ~1,500 tokens (~6,000 characters), it's too large. Every token is
repeated on every Claude Code turn.
- Identify sections >500 tokens covering specific workflows (deployment, testing, CI/CD,
  database migrations) that should be extracted to `.claude/commands/` files.
- Flag duplicate instructions (same concept stated multiple ways).
- Flag verbose prose that could be terse bullet points.
- Calculate savings: (current_tokens - optimized_tokens) x 30 turns per session.

**ISSUE E: Stale references**
Check if file paths, directory names, or tool names mentioned in CLAUDE.md actually exist
in the project. Flag references to files or directories that don't exist.

**ISSUE F: No custom commands**
Check if `.claude/commands/` directory exists. If the project has complex workflows (build
pipelines, deployment steps, testing procedures, database migrations), these should be
defined as on-demand commands rather than crammed into CLAUDE.md or left undocumented.
This is a separate finding from CLAUDE.md content issues.
- Only flag this if the project is non-trivial (has a build system, tests, or deployment).
- Suggest 2-3 specific commands based on the project's actual workflows.

---

REPORT STRUCTURE:
- For each issue found, create a separate finding.
- The "location" should point to the CLAUDE.md file (or project root if missing/stub).
- The "current_state" code_snippet should show the actual content (or note it's missing/stub).
- The "suggested_fix" code_snippet should show the improved content, tailored to the project.
  DO NOT use generic templates. Read the actual project files to understand the tech stack,
  structure, and conventions, then generate specific suggestions.
- If the existing CLAUDE.md uses `@filename` includes (e.g., `@AGENTS.md`), and the
  referenced file contains useful content, keep the include in the suggested fix BUT explain
  what it does in the recommendation description (e.g., "`@AGENTS.md` is an include directive
  that pulls in the referenced file's content"). If the include references a file that doesn't
  exist or has no useful content, remove it from the suggestion.

IMPACT ESTIMATION:
- Bloat (Issue D): cost_reduction "high", latency_reduction "medium", reliability_improvement "medium"
- Missing/Stub (Issues A, B): cost_reduction "low", latency_reduction "low", reliability_improvement "high"
- Missing sections (Issue C): cost_reduction "low", latency_reduction "low", reliability_improvement "medium"
- Stale references (Issue E): cost_reduction "low", latency_reduction "low", reliability_improvement "medium"
- No custom commands (Issue F): cost_reduction "low", latency_reduction "low", reliability_improvement "medium"

CONFIDENCE:
- "high" for Issues A, B, D (objectively measurable: file exists? token count?)
- "medium" for Issues C, E, F (requires judgment about project complexity)

WHEN NOT TO FLAG:
- If CLAUDE.md is 100-1,500 tokens, well-structured, covers key sections, has no stale
  references, AND the project is simple enough to not need custom commands: return [].

DOCS REFERENCES:
- CLAUDE.md overview: https://docs.anthropic.com/en/docs/claude-code/memory
- Custom slash commands: https://docs.anthropic.com/en/docs/claude-code/slash-commands
"""


def build_prompt() -> str:
    return build_base_prompt("claude_md_bloat", ANALYSIS_INSTRUCTIONS)
