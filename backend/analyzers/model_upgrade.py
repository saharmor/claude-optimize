from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

1. **Outdated Claude model identifiers**: Any reference to older Claude model versions that have
   newer, better replacements available at the same (or lower) price point.

2. **Model identifiers in config files, environment defaults, or constants**: Check not just direct
   API calls but also .env files, config objects, constants, and default parameter values where
   model names may be defined.

3. **Aliased or variable model names**: If a model is set via a variable or config, trace it back
   to where the actual model string is defined.

4. **Deprecated API patterns that must change with the upgrade**: When recommending a model upgrade,
   also check for API patterns that will break or are deprecated on the new model version.
   Include these in the same finding so the user gets a complete migration picture.

Use the "Upgrade Map", "Breaking Changes", and "Deprecated Beta Headers" sections from the
MODEL REGISTRY (provided in the base prompt) as your authoritative reference for all upgrade
paths and breaking changes. Do not hardcode model mappings. Always defer to the registry.

EFFORT CALIBRATION:
If the finding involves upgrading to Sonnet 4.6 and the code uses assistant prefills, extended
thinking with budget_tokens, or deprecated beta headers, set effort to "medium" (not "low")
since the migration requires more than a string swap. Otherwise keep effort "low".

IMPACT ESTIMATION:
- cost_reduction: "low" (same price tier, no direct cost savings)
- latency_reduction: "medium" (newer models are generally faster, but warn about Sonnet 4.6's
  default high effort potentially increasing latency if not configured)
- reliability_improvement: "medium" (better instruction following, fewer retries needed)

WHEN TO RECOMMEND:
- Any time you find an older model identifier that has a newer replacement.
- Even if the code works fine, upgrading is a free win: better results at no extra cost.
- Set confidence to "high" since model upgrades are straightforward.
- Always include relevant breaking changes in the recommendation description so the user
  knows exactly what else needs to change beyond the model string.

DOCS REFERENCES:
- Migration guide: https://platform.claude.com/docs/en/about-claude/models/migration-guide
- Model overview: https://docs.anthropic.com/en/docs/about-claude/models
- Adaptive thinking: https://docs.anthropic.com/en/docs/build-with-claude/adaptive-thinking
- Effort parameter: https://docs.anthropic.com/en/docs/build-with-claude/effort
"""


def build_prompt() -> str:
    return build_base_prompt("model_upgrade", ANALYSIS_INSTRUCTIONS)
