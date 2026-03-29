from analyzers.base import build_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

1. **Sequential loops making independent API calls**: For-loops, list comprehensions, or map
   operations that call the Claude API once per item when the items are independent of each other.
   Common patterns: classifying a list of items, summarizing multiple documents, scoring/ranking
   entries, enriching records.

2. **Offline/batch processing done one-by-one**: Nightly jobs, data pipelines, or background tasks
   that process items sequentially but don't need real-time responses.

3. **Async gather patterns that could use batching**: Code using asyncio.gather or similar to
   parallelize API calls. While this helps with latency, it still pays full per-request pricing.
   The Message Batches API offers 50% cost reduction.

4. **ETL or data enrichment pipelines**: Any pipeline that sends items through Claude for
   classification, extraction, transformation, or enrichment.

HOW MESSAGE BATCHES WORK:
- Send up to 100,000 requests in a single batch via the Message Batches API
- 50% cost reduction compared to individual API calls
- Results available within 24 hours (typically much faster)
- Prompt caching can stack with batching (though cache hits are best-effort in batch mode)
- Ideal for any workload that doesn't need sub-second response times

WHEN TO RECOMMEND BATCHING:
- Processing > 5 independent items in a loop
- Any offline/background processing
- Tasks where results are consumed minutes or hours later, not immediately
- Do NOT recommend batching for real-time user-facing interactions unless the code clearly has a separate offline path
- If a loop is latency-sensitive, explicitly call out the tradeoff instead of giving a blanket batching recommendation

DOCS REFERENCES:
- Message Batches: https://docs.anthropic.com/en/docs/build-with-claude/message-batches
"""


def build_prompt() -> str:
    return build_base_prompt("batching", ANALYSIS_INSTRUCTIONS)
