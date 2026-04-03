from analyzers.base import build_agentic_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

You are analyzing a project's Claude Code skills (.claude/skills/ directory) for quality
issues and gaps. Skills are on-demand capabilities defined by SKILL.md files with YAML
frontmatter. Claude Code loads them when triggered by matching context, making them ideal
for domain-specific workflows that don't need to be in every conversation's context.

This analysis is based on Anthropic's official best practices for skills:
https://docs.anthropic.com/en/docs/claude-code/skills

---

**ISSUE A: No skills defined**

If .claude/skills/ does not exist or is empty, check whether the project would benefit from
skills. Look for:
- CLAUDE.md sections with domain-specific workflows (>200 tokens on a specific topic, such
  as deployment procedures, data processing pipelines, review checklists, migration steps)
- Complex project with multiple distinct task types that Claude Code handles differently
- Repeated patterns in .claude/commands/ that indicate domain knowledge Claude needs

Only recommend skills if there's clear evidence the project has domain-specific work.
Do NOT suggest skills for simple projects. When suggesting, provide 1-3 specific skills with
ready-to-use SKILL.md content, including proper YAML frontmatter.

IMPORTANT: Each skill MUST live in its own subdirectory under .claude/skills/, with the
file named SKILL.md. The directory name is the skill's slug and must be lowercase with
hyphens only. Do NOT create flat .md files directly in .claude/skills/.

Correct:   .claude/skills/processing-migrations/SKILL.md
Incorrect: .claude/skills/processing-migrations.md

Example skill structure:
```
# File: .claude/skills/processing-migrations/SKILL.md
---
name: processing-migrations
description: Handles database migration creation and validation. Triggers when the user
  asks to create, modify, or troubleshoot database migrations.
allowed-tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Bash(npm run migrate:*)
---

## Database Migration Guide

[Domain-specific instructions here...]
```

**ISSUE B: SKILL.md body too large**

For each SKILL.md file, check the body length (content after the YAML frontmatter):
- Over 500 lines: this is a hard limit from Anthropic. Performance degrades significantly.
  Recommend splitting into a main SKILL.md with references to separate resource files.
- Over 100 lines: this is the "danger zone." Add a table of contents at the top so Claude
  can see the full scope even with partial reads.

**ISSUE C: Poor naming**

Check the skill directory name (which determines the skill's slug):
- Must be lowercase with hyphens and numbers only (no underscores, no uppercase, no spaces)
- Must be max 64 characters
- Should use gerund form (action-oriented): "processing-pdfs", "reviewing-code",
  "running-migrations" -- NOT "helper", "utils", "stuff", "my-skill", "tool"
- Should NOT use reserved words: "anthropic", "claude"

**ISSUE D: Poor or missing description**

Check the `description` field in YAML frontmatter:
- Missing description: Claude cannot discover or auto-trigger the skill. This is critical.
- First-person or second-person description: "I can help you with..." or "You can use
  this to..." -- these cause skill discovery problems. Must be third-person:
  "Processes Excel files and extracts structured data."
- Missing trigger conditions: the description must include WHAT the skill does AND WHEN
  to use it. Without the WHEN, Claude doesn't know when to auto-trigger. Good example:
  "Handles database migration creation and validation. Triggers when the user asks to
  create, modify, or troubleshoot database migrations."

**ISSUE E: Missing allowed-tools restriction**

If a SKILL.md has no `allowed-tools` field in its frontmatter, the skill gets access to ALL
tools. This is wasteful and potentially unsafe:
- A code review skill doesn't need Bash or Write access
- A documentation skill doesn't need to run commands
- A testing skill should only run specific test commands

Recommend specific allowed-tools arrays based on what the skill actually does.

**ISSUE F: Chained file references**

Check if SKILL.md references external files (e.g., "See reference/guide.md for details"),
and those files in turn reference other files. Anthropic's guidance: keep references ONE
level deep from SKILL.md. Claude may only partially read deeply nested files using head -100.

File chain: SKILL.md -> reference/guide.md (OK)
File chain: SKILL.md -> reference/guide.md -> reference/details.md (BAD)

**ISSUE G: Content quality issues**

Check SKILL.md content for:
- Time-sensitive information: "as of March 2025...", "currently...", "recently added..."
  This becomes stale. Use collapsible "old patterns" sections or remove dates entirely.
- Inconsistent terminology: mixing synonyms for the same concept within the skill
  (e.g., alternating between "endpoint", "URL", and "route" for the same thing).
  Pick one term and use it consistently.
- Content that belongs in CLAUDE.md instead: general project conventions, coding style
  rules, or other context that applies to ALL tasks, not just this skill's domain.

---

REPORT STRUCTURE:
- For missing skills: location is ".claude/", current_state describes what domain workflows
  were found, suggested_fix shows complete SKILL.md files.
- For existing skill issues: location is the specific SKILL.md file path, current_state
  shows the problematic content, suggested_fix shows the corrected version.

IMPACT ESTIMATION:
- Missing skills (A): cost_reduction "medium" (can reduce CLAUDE.md by extracting domain
  content), latency_reduction "low", reliability_improvement "high"
- Body too large (B): cost_reduction "medium", latency_reduction "medium",
  reliability_improvement "medium"
- Poor naming (C): cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"
- Poor description (D): cost_reduction "low", latency_reduction "low",
  reliability_improvement "high" (affects skill discovery and auto-triggering)
- Missing allowed-tools (E): cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"
- Chained references (F): cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"
- Content quality (G): cost_reduction "low", latency_reduction "low",
  reliability_improvement "low"

CONFIDENCE:
- "high" for Issues B, C, D (objectively checkable against specific rules)
- "medium" for Issues A, E, F, G (requires judgment about project needs)

WHEN NOT TO FLAG:
- If the project is very simple with no domain-specific workflows, return [].
- If skills exist and follow all the guidelines above, return [].
- Do NOT flag every project for missing skills. Only flag when there's concrete evidence
  of domain workflows that would benefit from skill extraction.

DOCS REFERENCES:
- Skills overview: https://docs.anthropic.com/en/docs/claude-code/skills
- Skills best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
"""


def build_prompt() -> str:
    return build_agentic_base_prompt("skills_quality", ANALYSIS_INSTRUCTIONS)
