# SPEC-010 — Report generator

Status: Accepted  
Owner: Engineering  
Depends on: SPEC-009

## Outcome

Assemble a citable report from a run's immutable artifacts so that every
number in prose traces to a hashed artifact, and limitations plus
cannot-conclude statements are mandatory, not optional.

## Scope

Included:

- `report/report.json`: structured sections, citations, limitations,
  cannot-conclude list.
- `report/report.md`: rendered human-readable form generated from the JSON —
  never hand-edited.
- Citation block: dataset names, SHA-256 input hashes, OSF DOI
  `10.17605/OSF.IO/9T6QU`, code revision, spec versions, model ID when a
  hypothesis ran.

Excluded:

- Free-form LLM prose generation: report text is deterministic templating
  over artifact values.
- Interactive or PDF output.

## Mandatory sections

1. Inputs and provenance (datasets, hashes, row counts, cohort flow).
2. Reproduction gate result (state, coefficient, per-whale effects).
3. Feature summary (partition contrasts, feature counts).
4. Hypotheses (ranked; each with evidence refs, alternatives, falsifiers,
   uncertainty kind) or the explicit `not_generated` / `indeterminate` state.
5. Limitations — always present; must include at minimum:
   - no semantic ground truth;
   - unresolved-identity cohort excluded from controlled inference;
   - audio-dependent features `not_observable` in this run;
   - confidence labels are `heuristic` unless SPEC-012 calibration exists.
6. Cannot conclude — explicit list (e.g., "coda meaning", "individual
   intent", "clan-level grammar" — nothing beyond measured timing structure).
7. Reproduction: exact commands, locked environment, artifact manifest hash.

## Invariants

1. Read-only over artifacts; the generator never recomputes scientific values.
2. Every numeric claim in `report.md` originates from a cited artifact field.
3. Semantic-claim lint runs on the rendered markdown.

## Output contract

```json
{
  "schema_version": "0.1.0",
  "run_id": "...",
  "sections": {"inputs": {...}, "gate": {...}, "features": {...},
               "hypotheses": {...}, "limitations": [...], "cannot_conclude": [...]},
  "citations": {"datasets": [...], "code_revision": "...", "model": "...|null"},
  "manifest_sha256": "..."
}
```

## Acceptance criteria

- [ ] Mandatory sections present; report fails to build if `limitations` or
      `cannot_conclude` would be empty.
- [ ] Citation check: every artifact referenced exists in the run manifest.
- [ ] Rendered markdown passes the forbidden-claim lint.
- [ ] Golden report test on the frozen foundation run.

## Stop conditions

Missing upstream artifact ⇒ section records its state (`not_observable`,
`not_generated`, `indeterminate`) rather than failing the report — except the
gate section: a non-passing gate produces a stop report only.
