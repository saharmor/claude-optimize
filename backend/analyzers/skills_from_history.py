"""Analyzer that reviews Claude Code chat history to find repeated user intents
that could be turned into reusable Skills.

Unlike other analyzers that send Claude to inspect project files, this one
pre-extracts user messages from the local chat history JSONL files and embeds
them directly in the prompt for pattern analysis.
"""
from analyzers.base import build_agentic_base_prompt
from chat_history_extractor import (
    extract_messages,
    format_messages_for_prompt,
)

ANALYSIS_INSTRUCTIONS_TEMPLATE = """\
WHAT TO LOOK FOR:

You are analyzing a user's Claude Code chat history to find repeated intents and
workflows that should be turned into reusable Skills. Skills are on-demand
capabilities defined by SKILL.md files that Claude Code auto-triggers when it
detects a matching context.

This is NOT about analyzing project files. Instead, you are given the user's
actual chat messages from past conversations. Your job is to find patterns —
prompts the user types repeatedly, workflows they kick off often, or domain
knowledge they paste in again and again.

---

**ISSUE A: Repeated workflow prompt**

The user pastes or types a similar prompt multiple times across sessions to
accomplish a recurring task. Examples:
- "Review all my changes for bugs, inefficiencies, and security issues before I push"
- "Run the tests, fix any failures, then run them again"
- "Update the changelog and bump the version"

For each cluster of similar prompts, report:
- How many times this intent appeared (count)
- 2-3 example messages showing the pattern
- A ready-to-use SKILL.md that automates this workflow

**ISSUE B: Repeated context pasting**

The user repeatedly pastes the same reference material, code patterns, or
domain knowledge into conversations. This should be a Skill with embedded
reference content, so Claude always has it available.

**ISSUE C: Multi-step ritual**

The user consistently follows the same sequence of requests within a session
(e.g., "first do X, then Y, then Z"). This sequence should be a single Skill
that handles the full workflow.

---

SKILL STRUCTURE:

When suggesting skills, provide complete SKILL.md files with proper YAML frontmatter:

```
---
name: reviewing-changes
description: Reviews all staged and unstaged code changes for bugs, security
  issues, and inefficiencies. Triggers when the user asks to review changes
  before pushing or committing.
allowed-tools:
  - Read
  - Bash(git diff)
  - Bash(git diff --cached)
  - Bash(git status)
  - Grep
  - Glob
---

## Pre-Push Code Review

[Detailed review instructions, checklist, what to look for...]
```

REPORT STRUCTURE:
- For each finding, set location.file to ".claude/skills/" (where the skill would be created)
- In current_state, show the repeated user messages as evidence (include count and examples)
- In recommendation, explain what skill to create and why
- In suggested_fix, provide the complete SKILL.md content ready to use
- Set language to "markdown" for both current_state and suggested_fix

IMPACT ESTIMATION:
- Repeated workflow (A): cost_reduction "low", latency_reduction "medium",
  reliability_improvement "high" (consistent execution every time)
- Repeated context (B): cost_reduction "medium" (avoids re-pasting large content),
  latency_reduction "low", reliability_improvement "medium"
- Multi-step ritual (C): cost_reduction "low", latency_reduction "high"
  (one command instead of many), reliability_improvement "high"

CONFIDENCE:
- "high" for prompts repeated 3+ times with near-identical wording
- "medium" for prompts repeated 2 times or with varied wording but same intent
- "low" for single prompts that look like they could become recurring

WHEN NOT TO FLAG:
- If there are fewer than 10 user messages total, return []
- Do NOT suggest skills for one-off tasks that are unlikely to recur
- Do NOT suggest skills for simple commands (/exit, /help, etc.)
- Focus on the TOP 3-5 most impactful opportunities, not every minor pattern

DOCS REFERENCES:
- Skills overview: https://docs.anthropic.com/en/docs/claude-code/skills
- Skills best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

---

USER CHAT HISTORY (from Claude Code conversations in this project):

{chat_history}
"""


def build_prompt(*, project_path: str) -> str:
    """Build the analyzer prompt with embedded chat history.

    This prompt builder requires project_path (unlike other analyzers) because
    it needs to locate and read the chat history JSONL files.
    """
    messages = extract_messages(project_path)
    formatted = format_messages_for_prompt(messages)
    instructions = ANALYSIS_INSTRUCTIONS_TEMPLATE.format(chat_history=formatted)
    return build_agentic_base_prompt("skills_from_history", instructions)
