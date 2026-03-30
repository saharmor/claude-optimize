"""Shared prompt components for all analyzers."""

MODEL_PRICING_TABLE = """\
CLAUDE MODEL PRICING REFERENCE (per million tokens):
| Model                  | Input    | Output   | Prompt caching write | Prompt caching read | Batch input | Batch output |
|------------------------|----------|----------|----------------------|---------------------|-------------|--------------|
| Claude Opus 4          | $15.00   | $75.00   | $18.75               | $1.50               | $7.50       | $37.50       |
| Claude Sonnet 4        | $3.00    | $15.00   | $3.75                | $0.30               | $1.50       | $7.50        |
| Claude Haiku 3.5       | $0.80    | $4.00    | $1.00                | $0.08               | $0.40       | $2.00        |

Common model identifiers:
- Opus: "claude-opus-4-6", "claude-opus-4-20250918"
- Sonnet: "claude-sonnet-4-6", "claude-sonnet-4-20250514"
- Haiku: "claude-haiku-4-5-20251001", "claude-haiku-3-5-20241022"
"""

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
    "estimated_savings_detail": "Specific savings estimate using the ACTUAL model's pricing, e.g. '~$X/month at Y calls/day at Opus pricing ($15/MTok input)'"
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
Different Claude models have very different pricing and capabilities. Your cost estimates and recommendations MUST be specific to the model actually used in each API call:
{MODEL_PRICING_TABLE}
- When calculating estimated savings, use the pricing for the specific model detected in that API call.
- Reference the model by name in your estimates (e.g., "at Opus pricing" or "at Haiku pricing"), never use a generic "at Sonnet pricing" unless the code actually uses Sonnet.
- If the model is set via an environment variable or config and you cannot determine the exact model, note this and provide estimates for the most likely model, stating your assumption.
- Set the "model" field in each finding to the exact model identifier string from the code (e.g., "claude-sonnet-4-6"). If the model comes from a variable, use the variable name prefixed with "$" (e.g., "$MODEL_NAME").

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
- Use conservative estimates for tokens, latency, and savings. If you cannot justify an exact number from the code, use a rough range and clearly state assumptions.
- All cost estimates must use the pricing of the actual model detected in the code, not a default or assumed model.
"""
