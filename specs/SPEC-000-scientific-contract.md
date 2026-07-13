# SPEC-000 — Scientific contract

Status: Accepted  
Owner: Rosetta Coda  
Scientific reviewer: Project owner  
Depends on: none

## Outcome

Prevent semantic overclaim and analytic flexibility from entering any Rosetta Coda artifact.

## Invariants

1. Rosetta Coda is a phonological hypothesis tool, never a translator.
2. No output states or implies “this coda means X” or assigns intention without ground truth.
3. Observations, deterministic features, statistical estimates, and hypotheses remain distinct typed records.
4. Every hypothesis includes evidence references, uncertainty kind, alternatives, and falsifiers.
5. `0`, `9999`, composite IDs, uncertain IDs, and unapproved aliases are `unresolved`.
6. Unresolved rows remain available for descriptive analysis but never enter individual baselines or individual-controlled inference.
7. Every scientific gate has `pass`, `fail`, and `indeterminate`; only `pass` unblocks dependents.
8. Thresholds, exclusions, labels, seeds, and primary estimands are frozen before viewing gate results.
9. Reports always include methods, provenance, limitations, and “what this analysis cannot conclude”.
10. Audit UI exposes structured evidence traces, not provider-private chain-of-thought.

## Forbidden-claim examples

- “This coda means danger.”
- “The whale is asking for food.”
- “Confidence 84%” when confidence has no empirical calibration record.

Allowed form: “Observed timing pattern supports hypothesis H under model M; alternative A remains viable; observation F would falsify H.”

## Acceptance criteria

- [x] Invariants reflect project premise.
- [x] Unresolved cohort policy explicit.
- [x] Gate semantics explicit.
- [ ] Later: automated forbidden-claim tests cover every generated report.

## Stop conditions

Any component unable to preserve these distinctions is blocked from producing a final report.

