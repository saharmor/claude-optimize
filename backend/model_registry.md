# Claude Model Registry

> Single source of truth for model identifiers, pricing, capabilities, and migration info.
> All analyzers reference this file — update it when Anthropic releases new models or changes pricing.
>
> Last updated: 2026-03-30

---

## Current Models

| Family  | Latest Identifier           | Aliases              | Context Window | Max Output (sync) | Max Output (batch) |
|---------|-----------------------------|----------------------|----------------|--------------------|--------------------|
| Opus    | `claude-opus-4-6`           | —                    | 1M tokens      | 128K tokens        | 300K tokens*       |
| Sonnet  | `claude-sonnet-4-6`         | —                    | 1M tokens      | 64K tokens         | 300K tokens*       |
| Haiku   | `claude-haiku-4-5-20251001` | `claude-haiku-4-5`   | 200K tokens    | 64K tokens         | 64K tokens         |

*300K batch output requires beta header `output-300k-2026-03-24`.

### Older Model Identifiers (still available)

| Model                           | Alias               | Context | Max Output | Notes                                  |
|---------------------------------|----------------------|---------|------------|----------------------------------------|
| `claude-sonnet-4-5-20250929`    | `claude-sonnet-4-5`  | 200K    | 64K        |                                        |
| `claude-sonnet-4-5-20250514`    |                      | 200K    | 64K        |                                        |
| `claude-opus-4-5-20251101`      | `claude-opus-4-5`    | 200K    | 64K        |                                        |
| `claude-opus-4-1-20250805`      | `claude-opus-4-1`    | 200K    | 32K        | Higher price tier ($15/$75)            |
| `claude-sonnet-4-20250514`      | `claude-sonnet-4-0`  | 200K    | 64K        |                                        |
| `claude-opus-4-20250918`        | `claude-opus-4-0`    | 200K    | 32K        | Higher price tier ($15/$75)            |
| `claude-3-7-sonnet-20250219`    |                      | 200K    | 64K        |                                        |
| `claude-3-5-sonnet-20241022`    |                      | 200K    | 8K         |                                        |
| `claude-3-5-sonnet-20240620`    |                      | 200K    | 8K         |                                        |
| `claude-3-opus-20240229`        |                      | 200K    | 4K         | Higher price tier ($15/$75)            |
| `claude-3-5-haiku-20241022`     | `claude-3-5-haiku`   | 200K    | 8K         |                                        |
| `claude-3-haiku-20240307`       |                      | 200K    | 4K         | Retiring April 19, 2026               |

---

## Pricing (per million tokens)

| Model                   | Input   | Output  | Cache Write (5-min) | Cache Write (1-hour) | Cache Read | Batch Input | Batch Output |
|-------------------------|---------|---------|---------------------|----------------------|------------|-------------|--------------|
| Opus 4.6 / 4.5          | $5.00   | $25.00  | $6.25               | $10.00               | $0.50      | $2.50       | $12.50       |
| Opus 4.1 / 4.0          | $15.00  | $75.00  | $18.75              | $30.00               | $1.50      | $7.50       | $37.50       |
| Sonnet (all 4.x)        | $3.00   | $15.00  | $3.75               | $6.00                | $0.30      | $1.50       | $7.50        |
| Haiku 4.5               | $1.00   | $5.00   | $1.25               | $2.00                | $0.10      | $0.50       | $2.50        |
| Haiku 3.5               | $2.00   | $8.00   | $2.50               | $4.00                | $0.20      | $0.40       | $2.00        |
| Haiku 3                 | $0.25   | $1.25   | $0.30               | $0.50                | $0.03      | $0.125      | $0.625       |

**Note:** Opus 4.6 and 4.5 are significantly cheaper ($5/$25) than Opus 4.1 and earlier ($15/$75). This is a 3x price drop — flag it as a cost savings when recommending upgrades from Opus 4.1 or earlier.

### Special Pricing

- **Batch API**: 50% discount on standard input/output prices across all models.
- **Fast mode** (Opus 4.6 only, beta): $30/MTok input, $150/MTok output (6x standard). Use `speed: "fast"` with header `fast-mode-2026-02-01`.
- **US data residency**: 1.1x standard price on Opus 4.6+ when using `inference_geo: "us"`.

---

## Capabilities Matrix

Use this to verify a recommendation is valid for the model the scanned code actually uses.

| Capability                      | Claude 3.x          | Claude 4.0 / 4.1    | Claude 4.5 (Opus & Sonnet) | Claude 4.6 (Opus & Sonnet) | Haiku 4.5           |
|---------------------------------|----------------------|----------------------|-----------------------------|----------------------------|---------------------|
| Context window                  | 200K                 | 200K                 | 200K                        | **1M**                     | 200K                |
| Assistant message prefill       | Yes                  | Yes                  | Yes                         | **NO — returns 400**       | Yes                 |
| Structured outputs              | No                   | Yes                  | Yes                         | Yes                        | Yes                 |
| `output_config.format`          | No                   | No                   | No                          | Yes (preferred)            | No                  |
| `output_format` (deprecated)    | No                   | Yes                  | Yes                         | Deprecated → output_config | Yes                 |
| Adaptive thinking               | No                   | No                   | No                          | Yes (GA)                   | No                  |
| Extended thinking (budget)      | Sonnet 3.7 only      | Yes                  | Yes                         | Deprecated → adaptive      | Yes                 |
| Effort parameter                | No                   | No                   | Opus 4.5 only               | Yes (Sonnet defaults high) | No                  |
| Effort level `max`              | No                   | No                   | No                          | **Opus 4.6 only**          | No                  |
| Prompt caching                  | Yes                  | Yes                  | Yes                         | Yes                        | Yes                 |
| Tool use                        | Yes                  | Yes                  | Yes                         | Yes                        | Yes                 |
| `tool_choice: any/tool`         | Yes                  | Yes                  | Yes                         | Yes                        | Yes                 |
| `tool_choice` with thinking     | auto/none only       | auto/none only       | auto/none only              | auto/none only             | auto/none only      |
| Message Batches API             | Yes                  | Yes                  | Yes                         | Yes                        | Yes                 |
| Vision (image input)            | Yes                  | Yes                  | Yes                         | Yes                        | Yes                 |
| PDF support                     | Yes                  | Yes                  | Yes                         | Yes                        | Yes                 |
| Citations                       | No (Haiku 3 no)      | Yes                  | Yes                         | Yes                        | Yes                 |
| Code execution                  | No                   | Yes                  | Yes                         | Yes (GA, free w/ web)      | Yes                 |
| Computer use (beta)             | Sonnet 3.7 only      | Yes                  | Yes                         | Yes                        | Yes                 |
| Files API (beta)                | No                   | No                   | Yes                         | Yes                        | No                  |
| Fast mode (beta)                | No                   | No                   | No                          | **Opus 4.6 only**          | No                  |
| Compaction API (beta)           | No                   | No                   | No                          | Yes                        | No                  |
| Fine-grained tool streaming     | No                   | Beta header required | Beta header required        | GA (no header)             | Beta header required|
| `temp` + `top_p` together      | Yes                  | **NO — pick one**    | **NO — pick one**           | **NO — pick one**          | **NO — pick one**   |
| `inference_geo` (data residency)| No                   | No                   | No                          | Yes                        | No                  |

---

## Prompt Caching Details

### Minimum Cacheable Prompt Length

The prompt must be at least this many tokens for caching to activate. Below this threshold, the request succeeds but caching is silently skipped.

| Min Tokens | Models                                           |
|------------|--------------------------------------------------|
| 1,024      | Sonnet 4.5, Opus 4.1, Opus 4.0, Sonnet 4.0, Sonnet 3.7 |
| 2,048      | Sonnet 4.6, Haiku 3.5, Haiku 3                  |
| 4,096      | Opus 4.6, Opus 4.5, Haiku 4.5                   |

### Cache Behavior

- **TTL**: 5 minutes by default. Extended to 1 hour with `"ttl": "1h"` (2x base input price for the write).
- **Max breakpoints**: 4 `cache_control` markers per request.
- **Lookback window**: Up to 20 blocks backward from each breakpoint.
- **Prefix order**: `tools` → `system` → `messages` (cache prefix must be an exact match).
- **Cache reads**: Do NOT count against rate limits.
- **Workspace isolation**: Caches are not shared between workspaces (since Feb 5, 2026).

---

## Extended Thinking vs. Adaptive Thinking

### Extended Thinking (manual budget — deprecated on 4.6)

- **Supported**: All Claude 4.x models, Sonnet 3.7, Haiku 4.5.
- **NOT supported**: Claude 3.x (except Sonnet 3.7), Haiku 3.
- **Syntax**: `thinking: {type: "enabled", budget_tokens: N}`
- `budget_tokens` must be less than `max_tokens`.
- Max useful `budget_tokens`: ~32K (Claude rarely uses more).
- `display`: `"summarized"` (default) or `"omitted"` (still billed for full thinking tokens).
- **Deprecated on 4.6 models** — still functional but will be removed. Migrate to adaptive.

### Adaptive Thinking (recommended for 4.6)

- **Supported**: Claude Opus 4.6 and Sonnet 4.6 ONLY.
- **Syntax**: `thinking: {type: "adaptive"}`
- Claude dynamically decides when and how much to think.
- Automatically enables interleaved thinking (no beta header needed).
- Controlled via `effort` parameter, not `budget_tokens`.
- At `high`/`max` effort: Claude almost always thinks. At lower effort: may skip for simple problems.
- **GA** — use `client.messages.create`, not `client.beta.messages.create`.

### Thinking Token Billing

- Charged for **full thinking tokens generated**, not summary tokens.
- With `display: "omitted"`: still charged for full thinking, but faster time-to-first-text-token.
- Thinking blocks from previous assistant turns are **ignored** and do NOT count as input tokens.

### Thinking + Tool Use Constraints

- Only `tool_choice: {type: "auto"}` or `{type: "none"}` supported when thinking is enabled.
- **Cannot** use `tool_choice: {type: "any"}` or `{type: "tool", name: "..."}` with thinking.
- Must preserve thinking blocks unmodified during tool use continuations.

---

## Effort Parameter

- **Supported**: Opus 4.6, Sonnet 4.6, Opus 4.5.
- **GA on 4.6** — remove `effort-2025-11-24` beta header if present.
- **Syntax**: `output_config: {effort: "medium"}`

| Level    | Description                              | Availability                          |
|----------|------------------------------------------|---------------------------------------|
| `max`    | Maximum capability, no token constraints | **Opus 4.6 only** (errors on others)  |
| `high`   | Complex reasoning, agentic tasks         | Opus 4.6, Sonnet 4.6, Opus 4.5       |
| `medium` | Balanced speed/quality                   | Opus 4.6, Sonnet 4.6, Opus 4.5       |
| `low`    | Most efficient, significant token savings| Opus 4.6, Sonnet 4.6, Opus 4.5       |

- **Default is `high`** (omitting effort = high). Sonnet 4.6 at `high` effort may have higher latency than Sonnet 4.5.
- Affects ALL tokens: text responses, tool calls, AND thinking.

---

## Vision and Multimodal

- **Supported**: All current Claude models.
- **Image formats**: JPEG, PNG, GIF, WebP.
- **Max images per request**: 600 (100 for 200K-context models). Max 20 per turn on claude.ai.
- **Max dimensions**: 8000x8000 px (2000x2000 if >20 images).
- **Max file size**: 5 MB per image (API), 10 MB (claude.ai).
- **Token cost**: `(width_px * height_px) / 750`. Images rescaled if long edge > 1568px.
- **Input methods**: base64-encoded, URL reference, or Files API (`file_id`).
- **Limitations**: Cannot identify people by name, limited spatial reasoning, approximate counting.

---

## PDF Support

- **Supported**: All active models.
- **Max pages per request**: 600 (100 for 200K-context models).
- **Max request size**: 32 MB.
- **Token cost**: 1,500–3,000 tokens per text page; image pages cost same as vision.
- **Input methods**: URL, base64, or Files API.

---

## Citations

- **Supported**: All active models EXCEPT Haiku 3.
- **Syntax**: Add `citations: {enabled: true}` to the document content block.
- **Incompatible with structured outputs** — returns 400 error if both enabled.
- `cited_text` does NOT count toward output or input tokens.

---

## Code Execution

- **Status**: GA (graduated from beta).
- **Tool version**: `code_execution_20250825`.
- **Free** when used with web search or web fetch (no charges beyond standard I/O tokens).
- Server-side tool — Anthropic executes the code in a sandboxed environment.

---

## Computer Use

- **Status**: Beta.
- **Beta headers**:
  - `computer-use-2025-11-24` for Opus 4.6, Sonnet 4.6, Opus 4.5.
  - `computer-use-2025-01-24` for older Claude 4.x models and Sonnet 3.7.
- **Tool versions**:
  - `computer_20251124` for 4.6/4.5 (adds `zoom` action).
  - `computer_20250124` for older models.
  - `text_editor_20250728`, `bash_20250124`.

---

## Files API

- **Status**: Beta — requires header `anthropic-beta: files-api-2025-04-14`.
- **Supported**: Opus 4.6, Sonnet 4.6, Opus 4.5, Sonnet 4.5.
- **Max file size**: 500 MB per file, 500 GB total per organization.
- **Not available** on Bedrock or Vertex AI.

---

## Upgrade Map

| Old Model                          | Recommended Upgrade          | Same Price? | Notes                    |
|------------------------------------|------------------------------|-------------|--------------------------|
| `claude-opus-4-5-20251101`         | `claude-opus-4-6`            | Yes         |                          |
| `claude-opus-4-5` (alias)          | `claude-opus-4-6`            | Yes         |                          |
| `claude-opus-4-1-20250805`         | `claude-opus-4-6`            | **Cheaper** | $15/$75 → $5/$25        |
| `claude-opus-4-20250918`           | `claude-opus-4-6`            | **Cheaper** | $15/$75 → $5/$25        |
| `claude-3-opus-20240229`           | `claude-opus-4-6`            | **Cheaper** | $15/$75 → $5/$25        |
| `claude-sonnet-4-5-20250929`       | `claude-sonnet-4-6`          | Yes         |                          |
| `claude-sonnet-4-5-20250514`       | `claude-sonnet-4-6`          | Yes         |                          |
| `claude-sonnet-4-5` (alias)        | `claude-sonnet-4-6`          | Yes         |                          |
| `claude-sonnet-4-20250514`         | `claude-sonnet-4-6`          | Yes         |                          |
| `claude-3-7-sonnet-20250219`       | `claude-sonnet-4-6`          | Yes         |                          |
| `claude-3-5-sonnet-20241022`       | `claude-sonnet-4-6`          | Yes         |                          |
| `claude-3-5-sonnet-20240620`       | `claude-sonnet-4-6`          | Yes         |                          |
| `claude-3-5-haiku-20241022`        | `claude-haiku-4-5-20251001`  | Yes*        | $2/$8 → $1/$5 (cheaper) |
| `claude-3-haiku-20240307`          | `claude-haiku-4-5-20251001`  | No          | $0.25/$1.25 → $1/$5     |

---

## Breaking Changes

### Upgrading TO Claude 4.6 (Opus or Sonnet)

- **Prefill removal**: Prefilling assistant messages returns a 400 error. If the code prefills the assistant turn, the upgrade will BREAK. Suggest: structured outputs via `output_config.format` with a JSON schema, clear system prompt instructions ("Respond with valid JSON only, no preamble"), or tools with enum fields for classification.
- **Extended thinking deprecation**: `thinking: {type: "enabled", budget_tokens: N}` is deprecated. Migrate to `thinking: {type: "adaptive"}` with the effort parameter. Also: `client.beta.messages.create` should become `client.messages.create` (adaptive thinking is GA).
- **output_format deprecation**: `output_format={...}` should become `output_config={"format": {...}}`.
- **Sonnet 4.6 effort default**: Sonnet 4.6 defaults to effort `"high"`. This may cause higher latency if not explicitly set. Recommend `output_config={"effort": "low"}` or `"medium"` for latency-sensitive or high-volume use cases.
- **Tool call JSON**: JSON escaping in tool call parameters may differ. Use standard JSON parsers, not regex.

### Upgrading FROM Claude 3.x to any 4.x+

- **Sampling parameters**: Cannot use both `temperature` AND `top_p` — pick one, or the call errors.
- **Tool versions**: Must update to latest tool versions (`text_editor_20250728`, `code_execution_20250825`). Remove any code using the `undo_edit` command.
- **New stop reasons**: Handle `refusal` and `model_context_window_exceeded` stop reasons.
- **Behavioral changes**: Claude 4+ has a more concise, direct style. Prompts may need adjustment.

---

## Deprecated Beta Headers

These are no-ops on newer models and should be removed:

| Header                                   | Status on 4.6                                    |
|------------------------------------------|--------------------------------------------------|
| `token-efficient-tools-2025-02-19`       | Built-in on Claude 4+                            |
| `output-128k-2025-02-19`                 | Built-in on Claude 4+                            |
| `interleaved-thinking-2025-05-14`        | Adaptive thinking enables this automatically     |
| `effort-2025-11-24`                      | Effort is GA on 4.6                              |
| `fine-grained-tool-streaming-2025-05-14` | GA on 4.6                                        |
| `structured-outputs-2025-11-13`          | Structured outputs GA on 4.6                     |

---

## Documentation References

- Model overview: https://docs.anthropic.com/en/docs/about-claude/models
- All models & specs: https://docs.anthropic.com/en/docs/about-claude/models/all-models
- Migration guide: https://platform.claude.com/docs/en/about-claude/models/migration-guide
- What's new in 4.6: https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6
- Prompt engineering: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- Structured outputs: https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs
- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Message Batches: https://docs.anthropic.com/en/docs/build-with-claude/message-batches
- Tool use: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- Extended thinking: https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
- Adaptive thinking: https://docs.anthropic.com/en/docs/build-with-claude/adaptive-thinking
- Effort parameter: https://docs.anthropic.com/en/docs/build-with-claude/effort
- Vision: https://docs.anthropic.com/en/docs/build-with-claude/vision
- PDF support: https://docs.anthropic.com/en/docs/build-with-claude/pdf-support
- Citations: https://docs.anthropic.com/en/docs/build-with-claude/citations
- Code execution: https://docs.anthropic.com/en/docs/build-with-claude/code-execution
- Computer use: https://docs.anthropic.com/en/docs/build-with-claude/computer-use
- Files API: https://docs.anthropic.com/en/docs/build-with-claude/files-api
- Token counting: https://docs.anthropic.com/en/docs/build-with-claude/token-counting
