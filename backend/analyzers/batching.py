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

MODEL-SPECIFIC BATCHING CONSIDERATIONS:
- The 50% batch discount applies to all models, but the absolute dollar savings vary greatly. Batching 1,000 calls with 2,000 input tokens each:
  - Opus: saves ~$15/day (from $30 to $15)
  - Sonnet: saves ~$3/day (from $6 to $3)
  - Haiku: saves ~$0.80/day (from $1.60 to $0.80)
- Identify the model from each API call and use its specific pricing in your savings estimates.
- If a project uses an expensive model like Opus for batch processing, consider also recommending a model downgrade for simpler tasks — Sonnet or Haiku may suffice for classification/extraction at 5-20x lower cost.

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
