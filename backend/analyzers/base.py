"""Shared prompt components for all analyzers."""

from model_registry import get_full_registry

_MODEL_REGISTRY = get_full_registry()

FINDING_SCHEMA = """\
Each finding must be a JSON object with this exact structure:
{
  "category": "<CATEGORY>",
  "model": "the Claude model identifier used in this specific API call (e.g. 'claude-sonnet-4-6')",
  "location": {
    "file": "relative/path/to/file.py",
    "lines": "42-68",
    "function": "function_name_if_applicable"
  },
  "current_state": {
    "description": "Plain-English description of what the code currently does and why it's suboptimal.",
    "code_snippet": "The actual code from the repo that exhibits the issue.",
    "language": "python"
  },
  "recommendation": {
    "title": "Short actionable title (e.g. 'Enable prompt caching on system prompt')",
    "description": "Detailed explanation of what to do and why. Include estimated impact. Be educational. Explain the Claude feature being leveraged.",
    "docs_url": "https://docs.anthropic.com/en/docs/..."
  },
  "suggested_fix": {
    "description": "Brief description of what changed in the fix.",
    "code_snippet": "The rewritten code with the optimization applied.",
    "language": "python"
  },
  "impact": {
    "cost_reduction": "high | medium | low",
    "latency_reduction": "high | medium | low",
    "reliability_improvement": "high | medium | low",
    "estimated_savings_detail": "One plain-English sentence describing the practical impact. Focus on the percentage or qualitative improvement, not raw token counts or per-MTok math. Good: 'Cuts input cost on this call by ~90% after the first request.' Bad: '~18,000 tokens saved (~$0.054 at $3/MTok input).'"
  },
  "confidence": "high | medium | low",
  "effort": "low | medium | high"
}"""


def build_base_prompt(category: str, analysis_instructions: str) -> str:
    return f"""\
You are an expert code analyzer for the Claude Optimize tool. Your task is to analyze a codebase that uses the Anthropic Claude API and find optimization opportunities related to: {category}.

INSTRUCTIONS:
1. Start by locating likely integration files, prioritizing Python, TypeScript, JavaScript, TSX/JSX, Go, Java, Ruby, and Rust source files plus config files.
2. Focus your turns on files that reference Anthropic, Claude, prompts, messages.create, tool definitions, JSON parsing, retry logic, or batching patterns.
3. Read only the files needed to understand the real implementation. Avoid spending turns on unrelated UI, assets, tests, vendored code, virtual environments, or node_modules.
4. **For each API call you analyze, identify which Claude model it uses.** Look for the `model` parameter in API calls (e.g., `model="claude-sonnet-4-6"`), configuration variables, environment variables, or constants that set the model. A single project may use different models for different tasks — track each one separately.
5. Identify specific optimization opportunities related to {category}.
6. For each finding, include the EXACT code from the repo and provide a concrete, working fix adapted to that codebase.
7. Prefer a small number of high-confidence findings over a long list of speculative ones.

MODEL-AWARE ANALYSIS:
Different Claude models have very different pricing, capabilities, and breaking changes. Identify the model used in each API call.
- Set the "model" field in each finding to the exact model identifier string from the code (e.g., "claude-sonnet-4-6"). If the model comes from a variable, use the variable name prefixed with "$" (e.g., "$MODEL_NAME").
- If the model is set via an environment variable or config and you cannot determine the exact model, note this and state your assumption.
- Before recommending any technique, cross-check the capabilities matrix below against the model the code uses. Do NOT recommend unsupported features.

{_MODEL_REGISTRY}

WRITING IMPACT ESTIMATES:
- Keep estimated_savings_detail to ONE short, readable sentence.
- Lead with the practical benefit: percentage saved, retries eliminated, latency cut.
- Do NOT include raw token counts, per-MTok pricing breakdowns, or multi-step arithmetic. Readers want to know "what gets better" not "how many tokens times what price."
- Good examples: "Cuts input cost on this call by ~90% after the first request." / "Eliminates retry overhead, saving ~30% of wasted calls." / "50% cost reduction on the entire batch by switching from sequential to batch API."
- Bad examples: "saves ~18,000 input tokens (~$0.054 at claude-sonnet-4-6 pricing of $3/MTok input)" / "Removes ~1,500 tokens of tool definitions per classification call. On 10 tickets that's ~15,000 tokens saved (~$0.045)"

{analysis_instructions}

OUTPUT FORMAT:
Return ONLY a valid JSON array of findings. No markdown fences. No explanatory text before or after.
Each element must match this schema:

{FINDING_SCHEMA}

Set "category" to "{category}" for all findings.

If you find no issues related to {category}, return an empty array: []

IMPORTANT:
- Only flag real issues you can see in the code. Do not speculate.
- Include actual code snippets from the files, not placeholders.
- Every suggested_fix must be syntactically valid and ready to use.
- Be educational in recommendation descriptions. Explain the Claude feature and why it helps.
- If there are multiple possible fixes, choose the one that is simplest, safest, and most aligned with Anthropic best practices.
- Consolidate closely related issues that share the same root cause instead of emitting many small overlapping findings.
- Avoid recommending a weaker workaround when a stronger Claude-native feature is a better fit; prefer the highest-leverage primary fix.
- Keep impact estimates concise and human-readable. One sentence, no token math or per-MTok pricing breakdowns.
"""
