from __future__ import annotations

from models import ProjectSummary

def build_project_summary_prompt() -> str:
    return """
You are analyzing a local codebase to explain what the project does.

Inspect the repository and return exactly one JSON object with this shape:
{
  "one_liner": "Short plain-English summary",
  "description": "A slightly longer 1-2 sentence explanation"
}

Requirements:
- Focus on what the project does for a developer or end user.
- Be specific, factual, and grounded in the codebase.
- Avoid hype, marketing language, and unverifiable claims.
- Do not mention that you are an AI, Claude Code, or that this was generated.
- Keep the one_liner under 14 words.
- Keep the description under 220 characters.
- If the project purpose is ambiguous, say what it appears to do.
- Return JSON only, with double-quoted keys and string values.
""".strip()


DEMO_PROJECT_SUMMARY = ProjectSummary(
    one_liner="Claude-powered support ticket classifier for customer requests.",
    description=(
        "A sample app that classifies support tickets with Claude, including prompts, "
        "tool calls, and structured outputs that can be optimized."
    ),
)
