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

6. **Output format control (model-dependent)**:
   - If the code uses a **pre-4.6 model** (any Claude 3.x, 4.0, 4.1, or 4.5 model) and could benefit
     from prefilling Claude's response (e.g., starting with '{{' for JSON), recommend prefill as a
     quick win, but note it must be removed before upgrading to 4.6.
   - If the code uses a **4.6 model** (claude-opus-4-6, claude-sonnet-4-6), do NOT recommend prefill.
     Prefilling assistant messages returns a 400 error on 4.6 models. Instead recommend:
     (a) Structured outputs via `output_config.format` with a JSON schema for guaranteed format.
     (b) Clear system prompt instructions ("Respond with valid JSON only, no preamble or fences").
     (c) Tools with enum fields for classification tasks.
   - If the code currently uses prefill on a 4.6 model, flag it as a bug. It will fail at runtime.

7. **Prompt DRY violations**: Identical or near-identical prompt fragments repeated across multiple
   files or functions instead of being centralized.

SCOPING RULES:
- For a single prompt block, prefer 1-2 high-leverage findings instead of one finding per micro-issue.
- Combine related problems when they would be fixed together (for example: XML tags + role clarity + output contract in the same system prompt rewrite).
- If the code is asking for structured JSON and manually parsing it, do NOT recommend assistant prefill as the primary fix. Prefer structured outputs. Leave API-level structure enforcement to the structured outputs analyzer.
- Focus on prompt content and structure, not tool scoping or caching mechanics.

MODEL-SPECIFIC PROMPT ENGINEERING CONSIDERATIONS:
- **Always check which model the code uses before recommending techniques.** Some features are model-dependent. Refer to the MODEL CAPABILITIES REFERENCE below for what's supported on each model family.
- More capable models (Opus) may need fewer examples and less rigid structure, while smaller models (Haiku) benefit more from explicit XML tags and strict output contracts.
- Better prompts reduce retries and wasted calls. Mention the model used in your finding.

DOCS REFERENCES:
- Prompt engineering overview: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- Use XML tags: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags
- Give examples: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/give-examples
- Be clear and direct: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct
- Assign a role: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts#give-claude-a-role
- Structured outputs: https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs
- Migration guide (prefill removal): https://platform.claude.com/docs/en/about-claude/models/migration-guide
"""


def build_prompt() -> str:
    return build_base_prompt("prompt_engineering", ANALYSIS_INSTRUCTIONS)
