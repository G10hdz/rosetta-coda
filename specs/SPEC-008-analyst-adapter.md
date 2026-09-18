# SPEC-008 — Phonological analyst adapter

Status: Accepted  
Owner: Engineering  
Depends on: SPEC-007

## Outcome

Obtain schema-valid, falsifiable hypotheses from an LLM over frozen
deterministic evidence so that every model claim is auditable against exact
artifact paths — extending the existing gate-evidence hypothesis stage to the
full feature evidence bundle.

## Scope

Included:

- `AnalystEvidence` artifact: frozen bundle joining the SPEC-004 gate result,
  SPEC-007 partition contrasts, per-whale aggregates, and a fixed sample of
  feature records, each with resolvable JSON paths.
- Generalize `interpretation.generate_hypothesis` to accept any frozen
  evidence artifact, not only `GateResult`.
- Model-call record per call: model ID, provider params, request schema hash,
  response, usage, cache key. Secrets are never persisted.
- Evidence-reference validation against the actual evidence document.

Excluded:

- Semantic or translation claims (forbidden at schema level, existing
  validator retained).
- Model-derived measurements: the model never computes numbers; it cites
  them.
- Private chain-of-thought storage.

## Input contract

`AnalystEvidence` (versioned artifact):

```json
{
  "schema_version": "0.1.0",
  "gate": "<SPEC-004 GateResult>",
  "partition_contrasts": "<SPEC-007 contrasts>",
  "whale_feature_means": "<per whale × vowel aggregates>",
  "feature_records": "<deterministic sample: first N records by coda_id sort>",
  "evidence_manifest": {"gate_sha256": "...", "features_sha256": "..."}
}
```

The bundle is written once per run; the model receives exactly this document
and nothing else.

## Output contract

`HypothesisRun` (existing contract, unchanged) plus `model-calls.jsonl`:

```json
{
  "call_id": "call-0001",
  "model": "deepseek-chat",
  "params_hash": "...",
  "request_sha256": "...",
  "response": "<raw structured output>",
  "usage": {"prompt_tokens": 0, "completion_tokens": 0},
  "cache_key": "..."
}
```

Validation gates, all enforced before the run is accepted:

1. Output validates against `HypothesisCandidate` schema.
2. Every `evidence_refs` JSON Pointer resolves inside the evidence document.
3. Semantic-claim lint passes on all free-text fields.
4. `gate_state == pass`; a non-passing gate raises before any model call.

## Acceptance criteria

- [ ] Schema-valid output on a recorded fixture response (no network in tests).
- [ ] Evidence refs resolve; an unresolvable ref fails the call.
- [ ] Semantic-claim fixtures rejected.
- [ ] Model-call record persisted with request hash; no API key material in
      artifacts.
- [ ] Real-call integration test marked `slow`, skipped without
      `ROSETTA_API_KEY`.

## Stop conditions

Schema failure after one schema-repair retry, or missing API key, leaves the
run with `hypothesis_available = false`; deterministic stages are unaffected.
