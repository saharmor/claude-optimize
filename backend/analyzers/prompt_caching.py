from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

1. **Large static system prompts without cache_control**: System prompts above ~500 tokens that are
   sent identically on every API call but don't use the `cache_control` parameter with
   `{"type": "ephemeral"}`. These are prime candidates for prompt caching. After the first request,
   subsequent requests read from cache at 90% lower cost.

2. **Repeated tool definitions**: Tool/function definitions that are passed identically on every API
   call. Tool definitions can be cached by placing a `cache_control` breakpoint after the tools array.

3. **Repeated context documents**: RAG chunks, reference documents, or instruction sets that are
   included in every request. If the same content appears in multiple sequential calls, it should
   be cached.

4. **Static conversation prefixes**: Multi-turn conversations where the same system message + initial
   turns are sent on every new message. The static prefix should be cached.

HOW PROMPT CACHING WORKS:
- Add `"cache_control": {{"type": "ephemeral"}}` to message blocks you want cached
- First request: slightly higher cost (cache write premium of 25%)
- Subsequent requests (within 5-minute TTL): 90% cost reduction on cached tokens
- Break-even: ~3-4 requests within the TTL window
- Cache is based on exact prefix matching, so the cached content must be an exact prefix of the new request
- Cacheability thresholds are model-dependent, so only recommend caching when the repeated prefix is clearly large enough to qualify

WHEN TO RECOMMEND CACHING:
- System prompts or static prefixes that are clearly large and reused frequently
- Content that is repeated across > 3 calls within a short window
- Do NOT recommend caching for content that changes frequently or is unique per request

DOCS REFERENCES:
- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
"""


def build_prompt() -> str:
    return build_base_prompt("prompt_caching", ANALYSIS_INSTRUCTIONS)
