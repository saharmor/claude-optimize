from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

1. **Missing XML tag structure**: System prompts or user message templates that use plain prose
   instead of XML tags (<instructions>, <context>, <examples>, etc.) to delineate sections.
   Claude performs significantly better with XML-tagged sections for clarity.

2. **No few-shot examples**: Prompts that describe a complex task but provide zero examples of
   expected input/output. Adding 2-3 examples dramatically improves output consistency.

3. **Missing output format contract**: Prompts that don't explicitly specify what format Claude
   should respond in (JSON, markdown, specific fields, etc.). This leads to inconsistent outputs.

4. **Vague or ambiguous instructions**: Instructions like "be helpful" or "analyze this" without
   specifying criteria, constraints, or evaluation dimensions.

5. **No role/persona assignment**: System prompts that don't establish Claude's role or expertise
   area for the task. Role prompting improves task-specific performance.

6. **Missing prefill usage**: Cases where the code could benefit from prefilling Claude's response
   (e.g., starting with '{' for JSON output) but doesn't use the assistant message prefill technique.

7. **Prompt DRY violations**: Identical or near-identical prompt fragments repeated across multiple
   files or functions instead of being centralized.

SCOPING RULES:
- For a single prompt block, prefer 1-2 high-leverage findings instead of one finding per micro-issue.
- Combine related problems when they would be fixed together (for example: XML tags + role clarity + output contract in the same system prompt rewrite).
- If the code is asking for structured JSON and manually parsing it, do NOT recommend assistant prefill as the primary fix unless the code clearly must stay text-only. Leave API-level structure enforcement to the structured outputs analyzer.
- Focus on prompt content and structure, not tool scoping or caching mechanics.

MODEL-SPECIFIC PROMPT ENGINEERING CONSIDERATIONS:
- Different models benefit differently from prompt engineering techniques. More capable models (Opus) may need fewer examples and less rigid structure, while smaller models (Haiku) benefit more from explicit XML tags, detailed examples, and strict output contracts.
- When estimating impact, consider that prompt engineering improvements reduce retries and wasted tokens — the dollar value of those wasted tokens depends on the model's pricing.
- Identify the model from each API call and use its specific pricing in your estimates.

DOCS REFERENCES:
- Prompt engineering overview: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- Use XML tags: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags
- Give examples: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/give-examples
- Be clear and direct: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct
- Assign a role: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts#give-claude-a-role
- Prefill responses: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response
"""


def build_prompt() -> str:
    return build_base_prompt("prompt_engineering", ANALYSIS_INSTRUCTIONS)
