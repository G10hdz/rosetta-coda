# Model provider research — Rosetta Coda hypothesis stage

Status: research snapshot (2026-08)  
Scope: one structured, falsifiable phonological hypothesis over a frozen ~2KB gate artifact.  
Not in scope: measurements, audio models, multi-agent stacks, OpenAI/Anthropic brand requirements.

## Decision (course / product default)

| Choice | Value |
|---|---|
| **Default provider** | **DeepSeek** (OpenAI-compatible API) |
| **Default model** | DeepSeek V4-Flash / `deepseek-chat` (use current catalog id) |
| **Why** | Lowest paid cost that still follows instructions + JSON; same client shape as OpenAI SDK via `base_url` |
| **Offline fallback** | Ollama on local GPU (`qwen3:30b` or similar) |
| **Quality gate** | Repo validators — Pydantic schema, JSON Pointer resolution, semantic-claim ban — not the vendor logo |

**Sol / GPT-5.6 / Anthropic are not required** for science or for a course final. They only matter if a marketing pitch names them.

---

## What the hypothesis job actually needs

Must:

1. Obey “no meaning / intent / translation” instructions.
2. Emit strict schema: `title`, `claim`, `evidence_refs` (JSON Pointers), `uncertainty_kind`, `alternatives`, `falsifiers`, `limitations`.
3. Cite only pointers that exist in the gate JSON.
4. Stay scientifically cautious under ambiguity.

Nice:

- Reasoning control
- Native structured outputs (JSON Schema / Pydantic)
- Stable logged `model` id for provenance

Input size: gate artifact ≈ **1.8–2.2 KB**. Cost is almost all **output (+ reasoning) tokens**, not input.

---

## Is a flagship model forced?

| Goal | Flagship needed? |
|---|---|
| Demo UI + gate + preview mock hypothesis | No |
| Product: frozen evidence → schema-valid hypothesis | No |
| Course final: pipeline + ethics + structured LLM | No |
| Marketing that says a specific flagship name | Only that named model, once, freeze artifact |

Science creed: deterministic stats first; LLM last; evidence-bound. Model is a replaceable adapter.

---

## Price ladder (USD / 1M tokens, short context, ~Aug 2026)

### OpenAI GPT-5.6 family (reference only — not required)

Post–30 Jul 2026 Terra/Luna cut:

| Model | Input | Output | Notes |
|---|---:|---:|---|
| gpt-5.6-sol | $5.00 | $30.00 | Flagship; overkill for 2KB gate |
| gpt-5.6-terra | $2.00 | $12.00 | Mid tier |
| gpt-5.6-luna | $0.20 | $1.20 | Same API family, ~25× cheaper out than Sol |

Sources: OpenAI pricing / GPT-5.6 posts (verify live before spend).

Rough **one-run** cost (≈1–2k in, 0.5–3k out + optional reasoning):

| Path | Ballpark / run |
|---|---|
| Sol medium reasoning | cents → tens of cents |
| Terra | ~⅓–½ of Sol |
| Luna | pennies |
| DeepSeek Flash | fractions of a cent |
| Gemini 2.5 Flash | pennies |
| OpenRouter `:free` | $0 (rate limits, flaky) |
| Local Ollama | $0 power |

OpenRouter sometimes applies temporary discounts (e.g. Terra 50% off); treat as ephemeral.

---

## Chinese / Asia providers (preferred cost path)

| Family | Model (typical) | In / Out (approx) | Structured JSON | Fit for this job |
|---|---|---:|---|---|
| **DeepSeek** | **V4-Flash** | **$0.14 / $0.28** | JSON mode; validate with Pydantic | **Best $/quality default** |
| DeepSeek | V4-Pro | $0.435 / $0.87 | same | If Flash fails schema once |
| **Zhipu / Z.ai** | **GLM-5.2** | OR promo ~$0.28/$0.88; list higher | OpenAI-compat hosts | Strong reasoning |
| Z.ai | GLM-5 | ~$0.60–1.00 / $1.92–3.20 | same | Flagship, still ≪ Sol |
| **Alibaba Qwen** | Flash / Plus | ~$0.10–0.40 / $0.30–1.80 | DashScope / OR | Good JSON with schema in prompt |
| Qwen | Qwen3.8-Max | $2 / $6 | yes | Overkill vs DeepSeek Flash |
| **Moonshot Kimi** | K2.5 | ~$0.60 / $3.00 | OpenAI-compat | OK, pricier than DS Flash |
| Kimi | K2.6 | ~$0.95 / $4.00 | same | Mid |
| Kimi | K3 | ~$2.90–3 / $14–15 | same | Near-flagship price → skip |
| **Local** | qwen3:30b (Ollama) | **$0** | prompt + validate | Best $0 offline path |

### Ranked for *this* repo

1. **DeepSeek V4-Flash** — default paid cloud  
2. **GLM-5.2 via OpenRouter** (when discounted)  
3. **Qwen Flash/Plus**  
4. **Ollama qwen3:30b** — $0  
5. Skip Kimi K3 / Qwen Max for a 2KB artifact  

**Caveats (DeepSeek):**

- Strict JSON-Schema enforcement may be weaker than OpenAI/Gemini → **repo validators are the real gate**.
- Data leaves to provider jurisdiction (OK for public scientific gate JSON; not for private PII).
- Confirm current model ids and whether `responses.parse` vs `chat.completions` + `response_format` is supported on the endpoint you use.

---

## Other cheap non-Chinese options

| Path | In / Out | Notes |
|---|---:|---|
| Gemini 2.5 Flash | ~$0.30 / $2.50 | Strong structured / Pydantic; free tier on AI Studio often exists |
| OpenRouter free routes | $0 | e.g. various `:free` models; dry-run schema before demo day |
| gpt-5.6-luna | $0.20 / $1.20 | Only if you already have OpenAI billing and want zero adapter work |

Anthropic: not needed; typically more expensive for this workload.

---

## Wiring pattern (minimum)

No multi-provider framework.

```text
ROSETTA_BASE_URL=https://api.deepseek.com   # or Ollama / OpenRouter
ROSETTA_API_KEY=...
ROSETTA_MODEL=deepseek-chat                 # or qwen3:30b, glm-…, etc.
```

Client shape:

- Prefer **OpenAI Python SDK** pointed at any OpenAI-compatible base URL (DeepSeek, OpenRouter, Ollama).
- Parse model JSON into existing `HypothesisCandidate` / `HypothesisRun`.
- Reject bad pointers and semantic claims in-process (already implemented).
- Persist `model` id on the artifact for provenance.

Artifact path (post–Sol cleanup):

- `artifacts/demo/hypothesis.json`
- Manifest flag: `hypothesis_available`
- CLI: `uv run python -m scripts.run_hypothesis_demo`

---

## Decision matrix

| Scenario | Pick |
|---|---|
| Course final, low cost | **DeepSeek Flash** |
| Offline / no cloud | **Ollama qwen3:30b** |
| Compare models for rubric | Same schema, 2–3 models, table of cost + validator pass |
| Need Gemini-class structured free tier | Gemini 2.5 Flash |
| Someone insists on US flagship branding | One paid call, freeze JSON, never call again |

---

## Explicit non-goals

- Semantic translation or “whale language” claims  
- Paying flagship rates for a 2KB structured claim  
- Multi-provider abstraction layers before a second provider is proven necessary  
- Coupling product correctness to a single vendor brand  

---

## Verification checklist after a live run

1. Artifact validates as `HypothesisRun`  
2. Every `evidence_refs` pointer resolves in the gate JSON  
3. No semantic-claim regex hits  
4. Demo badge shows real `model` string  
5. Manifest `hypothesis_available: true` only after a real write  
6. `uv run pytest` green  

---

## Changelog

| Date | Note |
|---|---|
| 2026-08 | Research captured from provider docs / OpenRouter listings; Sol branding removed from product surfaces; default recommendation = DeepSeek Flash + validator gate. |

Prices and model ids drift — re-check official pricing before any budget commitment.
