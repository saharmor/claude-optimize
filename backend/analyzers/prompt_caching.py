from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

1. **Large static system prompts without cache_control**: System prompts above ~500 tokens that are
   sent identically on every API call but don't use the `cache_control` parameter with
   `{"type": "ephemeral"}`. These are prime candidates for prompt caching. After the first request,
   subsequent requests read from cache at 90% lower cost.

2. **Repeated tool definitions without caching**: Tool/function definitions that are passed
   identically on every API call but never set `cache_control`. The correct pattern is to place
   `"cache_control": {{"type": "ephemeral"}}` on the **last tool** in the `tools` array (not after
   the array -- on the last tool object itself). This caches the entire tool-definitions prefix.
   Especially impactful for large tool arrays (5+ tools) reused across turns.

3. **Tool ordering that breaks caching**: The tools array uses prefix-matching for cache hits. If
   the code reorders tools between calls, or inserts/removes tools in the middle, the cache is
   invalidated entirely. Recommend keeping tool order stable, placing always-used tools first and
   conditionally-included tools last.

4. **Missing defer_loading for large tool sets**: Applications that pass many tools (10+) but only
   use a few per turn. `defer_loading: true` on rarely-used tools excludes them from the cached
   prefix entirely -- the model discovers them via tool search. This keeps the cached prefix intact
   and cuts input token cost for unused tool definitions.

5. **Frequent tool_choice or disable_parallel_tool_use changes**: Code that toggles these between
   turns in the same conversation. Both affect the messages-level cache, so toggling them
   invalidates the messages cache on every turn.

CACHE INVALIDATION HIERARCHY (tools -> system -> messages):
Changes at one level invalidate that level and everything after it:
- Modifying tool definitions (including reordering) -> invalidates entire cache
- Toggling web search or citations -> invalidates system and messages caches
- Changing tool_choice or disable_parallel_tool_use -> invalidates messages cache
A single tool definition change wipes out ALL cached content. Tool stability is critical.

6. **Repeated context documents**: RAG chunks, reference documents, or instruction sets that are
   included in every request. If the same content appears in multiple sequential calls, it should
   be cached.

7. **Static conversation prefixes**: Multi-turn conversations where the same system message + initial
   turns are sent on every new message. The static prefix should be cached.

HOW PROMPT CACHING WORKS:
- Add `"cache_control": {{"type": "ephemeral"}}` to message blocks you want cached
- First request: slightly higher cost (cache write premium of 25%)
- Subsequent requests (within 5-minute TTL): 90% cost reduction on cached tokens
- Break-even: ~3-4 requests within the TTL window
- Cache is based on exact prefix matching, so the cached content must be an exact prefix of the new request
- Cacheability thresholds are model-dependent, so only recommend caching when the repeated prefix is clearly large enough to qualify

MODEL-SPECIFIC CACHING CONSIDERATIONS:
- Caching saves ~90% on repeated input tokens. The benefit is proportionally larger for expensive models (Opus) than cheap ones (Haiku).
- Identify the model from the `model` parameter in each API call and mention it in your finding.

WHEN TO RECOMMEND CACHING:
- System prompts or static prefixes that are clearly large and reused frequently
- Tool arrays that are reused across multiple calls in a conversation
- Content that is repeated across > 3 calls within a short window
- Do NOT recommend caching for content that changes frequently or is unique per request
- For tool-related findings (items 2-5), only flag when tools are clearly reused across multiple calls, not single-shot tool use

DOCS REFERENCES:
- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Tool use with prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/tool-use-with-prompt-caching
"""


def build_prompt() -> str:
    return build_base_prompt("prompt_caching", ANALYSIS_INSTRUCTIONS)
