# Claude Model Registry

> Single source of truth for model identifiers, pricing, capabilities, and migration info.
> All analyzers reference this file — update it when Anthropic releases new models or changes pricing.
>
> Last updated: 2026-03-30

---

## Current Models

| Family  | Latest Identifier              | Aliases                  | Context Window | Max Output |
|---------|--------------------------------|--------------------------|----------------|------------|
| Opus    | `claude-opus-4-6`              | —                        | 200K tokens    | 128K tokens|
| Sonnet  | `claude-sonnet-4-6`            | —                        | 200K tokens    | 128K tokens|
| Haiku   | `claude-haiku-4-5-20251001`    | `claude-haiku-4-5`       | 200K tokens    | 128K tokens|

---

## Pricing (per million tokens)

| Model           | Input    | Output   | Cache Write | Cache Read | Batch Input | Batch Output |
|-----------------|----------|----------|-------------|------------|-------------|--------------|
| Claude Opus 4   | $15.00   | $75.00   | $18.75      | $1.50      | $7.50       | $37.50       |
| Claude Sonnet 4 | $3.00    | $15.00   | $3.75       | $0.30      | $1.50       | $7.50        |
| Claude Haiku 4.5| $1.00    | $5.00    | $1.25       | $0.10      | $0.50       | $2.50        |

---

## Capabilities Matrix

Use this to verify a recommendation is valid for the model the scanned code actually uses.

| Capability                    | Claude 3.x        | Claude 4.0 / 4.1 / 4.5 | Claude 4.6 (Opus & Sonnet) | Haiku 4.5         |
|-------------------------------|--------------------|--------------------------|----------------------------|-------------------|
| Assistant message prefill     | Yes                | Yes                      | **NO — returns 400 error** | Yes               |
| Structured outputs            | No                 | Yes                      | Yes                        | Yes               |
| `output_config.format`        | No                 | No                       | Yes (preferred)            | No                |
| `output_format` (deprecated)  | No                 | Yes                      | Deprecated → output_config | Yes               |
| Adaptive thinking             | No                 | No                       | Yes (GA)                   | No                |
| Extended thinking (budget)    | No                 | Yes                      | Deprecated → adaptive      | No                |
| Effort parameter              | No                 | No                       | Yes (Sonnet defaults high) | No                |
| Prompt caching                | Yes                | Yes                      | Yes                        | Yes               |
| Tool use                      | Yes                | Yes                      | Yes                        | Yes               |
| Message Batches API           | Yes                | Yes                      | Yes                        | Yes               |
| `temp` + `top_p` together    | Yes                | **NO — pick one**        | **NO — pick one**          | **NO — pick one** |

### Key constraints

- **4.6 + prefill**: Any `messages` array ending with `role: "assistant"` returns a 400 error. Use structured outputs, system prompt instructions, or `output_config.format` instead.
- **4.6 + effort**: Sonnet 4.6 defaults to effort `"high"`, which may increase latency vs. Sonnet 4.5. Set `output_config.effort` to `"low"` or `"medium"` for latency-sensitive calls.
- **4.0+ sampling**: Cannot combine `temperature` and `top_p` — the API returns an error. Pick one.

---

## Upgrade Map

| Old Model                          | Recommended Upgrade          | Same Price? |
|------------------------------------|------------------------------|-------------|
| claude-sonnet-4-5-20250929         | claude-sonnet-4-6            | Yes         |
| claude-sonnet-4-5-20250514         | claude-sonnet-4-6            | Yes         |
| claude-sonnet-4-5 (alias)          | claude-sonnet-4-6            | Yes         |
| claude-sonnet-4-20250514           | claude-sonnet-4-6            | Yes         |
| claude-3-7-sonnet-20250219         | claude-sonnet-4-6            | Yes         |
| claude-3-5-sonnet-20241022         | claude-sonnet-4-6            | Yes         |
| claude-3-5-sonnet-20240620         | claude-sonnet-4-6            | Yes         |
| claude-opus-4-5 (alias)            | claude-opus-4-6              | Yes         |
| claude-opus-4-1-20250805           | claude-opus-4-6              | Yes         |
| claude-3-opus-20240229             | claude-opus-4-6              | Yes         |
| claude-opus-4-20250918             | claude-opus-4-6              | Yes         |
| claude-3-haiku-20240307            | claude-haiku-4-5-20251001    | Yes         |
| claude-3-5-haiku-20241022          | claude-haiku-4-5-20251001    | Yes         |

---

## Breaking Changes

### Upgrading TO Claude 4.6 (Opus or Sonnet)

- **Prefill removal**: Prefilling assistant messages returns a 400 error. If the code prefills the assistant turn, the upgrade will BREAK. Suggest: structured outputs via `output_config.format` with a JSON schema, clear system prompt instructions ("Respond with valid JSON only, no preamble"), or tools with enum fields for classification.
- **Extended thinking deprecation**: `thinking: {type: "enabled", budget_tokens: N}` is deprecated. Migrate to `thinking: {type: "adaptive"}` with the effort parameter. Also: `client.beta.messages.create` should become `client.messages.create` (adaptive thinking is GA).
- **output_format deprecation**: `output_format={...}` should become `output_config={"format": {...}}`.
- **Sonnet 4.6 effort default**: Sonnet 4.6 defaults to effort `"high"`. This may cause higher latency if not explicitly set. Recommend `output_config={"effort": "low"}` or `"medium"` for latency-sensitive or high-volume use cases.

### Upgrading FROM Claude 3.x to any 4.x+

- **Sampling parameters**: Cannot use both `temperature` AND `top_p` — pick one, or the call errors.
- **Tool versions**: Must update to latest tool versions (text_editor_20250728, code_execution_20250825). Remove any code using the `undo_edit` command.
- **New stop reasons**: Handle `refusal` and `model_context_window_exceeded` stop reasons.
- **Behavioral changes**: Claude 4+ has a more concise, direct style. Prompts may need adjustment.

---

## Deprecated Beta Headers

These are no-ops on Claude 4+ and should be removed:

| Header                                   | Status on 4.6                                    |
|------------------------------------------|--------------------------------------------------|
| `token-efficient-tools-2025-02-19`       | Built-in on Claude 4+                            |
| `output-128k-2025-02-19`                 | Built-in on Claude 4+                            |
| `interleaved-thinking-2025-05-14`        | Adaptive thinking enables this automatically     |
| `effort-2025-11-24`                      | Effort is GA on 4.6                              |
| `fine-grained-tool-streaming-2025-05-14` | GA on 4.6                                        |

---

## Documentation References

- Model overview: https://docs.anthropic.com/en/docs/about-claude/models
- Migration guide: https://platform.claude.com/docs/en/about-claude/models/migration-guide
- What's new in 4.6: https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6
- Prompt engineering: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- Structured outputs: https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs
- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Message Batches: https://docs.anthropic.com/en/docs/build-with-claude/message-batches
- Tool use: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- Adaptive thinking: https://docs.anthropic.com/en/docs/build-with-claude/adaptive-thinking
- Effort parameter: https://docs.anthropic.com/en/docs/build-with-claude/effort
