from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

1. **Regex-based response parsing**: Code using re.search, re.findall, or similar to extract
   structured data from Claude's free-text response. This is fragile and fails when Claude's
   phrasing varies slightly.

2. **JSON parsing with retries**: Code that does json.loads() on Claude's response wrapped in
   try/except with retry loops. This pattern suggests the code is asking for JSON via the prompt
   but Claude sometimes returns invalid JSON or extra text around it.

3. **"Return JSON" in prompts**: Prompts that include instructions like "respond with JSON",
   "return a JSON object", "output only valid JSON", etc. This is a strong signal that native
   structured outputs should be used instead.

4. **Manual response validation**: Code that checks whether Claude's response contains expected
   fields, has the right format, or matches a pattern, doing manually what structured outputs
   guarantee automatically.

5. **String manipulation of responses**: Code that strips, splits, or otherwise manipulates Claude's
   text response to extract structured information.

HOW STRUCTURED OUTPUTS WORK:
- Prefer native JSON / schema-based structured outputs when the SDK supports it
- Otherwise, define a tool whose input_schema matches your desired output and read the tool input
- No more parsing failures, no retries needed, and much less prompt text spent on format instructions
- The response shape should be guaranteed by the API or enforced by the tool schema itself

WHEN TO RECOMMEND STRUCTURED OUTPUTS:
- Any time the code parses Claude's response to extract fields
- Any time the prompt asks Claude to respond in a specific format
- Any time there are retries around response parsing
- Do NOT recommend for free-form text generation (creative writing, chat, etc.)

FIX GUIDANCE:
- If the code only needs structured JSON data, prefer the simplest native structured-output feature supported by that SDK
- If the code is already using tools or needs schema enforcement via tool calls, recommend tool_use with an explicit schema
- Tailor the suggestion to the SDK and language actually used in the repo

DOCS REFERENCES:
- Structured outputs: https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/increase-consistency
- Tool use overview: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview
"""


def build_prompt() -> str:
    return build_base_prompt("structured_outputs", ANALYSIS_INSTRUCTIONS)
