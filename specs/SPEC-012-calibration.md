# SPEC-012 — Confidence calibration and held-out evaluation

Status: Accepted — confidence language requires scientific reviewer sign-off  
Owner: Engineering + scientific reviewer  
Depends on: SPEC-008, SPEC-009, SPEC-010, SPEC-011

## Outcome

Measure empirically whether claimed effects replicate on held-out whales and
bouts so that confidence labels move from `heuristic` to `empirically_checked`
with a citation — or stay honest when they do not replicate.

## Scope

Included:

- Grouped evaluation split `split-v1`: partition resolved whales (and bouts
  within whales where dates exist) into fit/hold-out groups; no whale appears
  on both sides.
- Per-claim replication check: each ranked hypothesis' directional claim is
  re-evaluated on the hold-out group using the same deterministic feature
  definitions.
- `CalibrationReport` artifact with per-claim results and a corpus-level
  replication rate.
- Uncertainty label upgrade path: `heuristic` → `empirically_checked` only
  with a `calibration_report_sha256` reference.

Excluded:

- Frequentist calibrated probabilities (sample is far too small; label stays
  qualitative).
- Post-hoc feature redefinition: hold-out evaluation reuses frozen features.

## Split and evaluation contract

`split-v1`:

- Deterministic assignment: `group = sha256(whale_id + split_seed) mod 2`,
  seed `calibration-v1`; approximately half of resolved whales per side.
- Bout nesting: where a `date` exists, all codas of a whale stay together —
  the whale is the split unit, bouts nest inside.
- Replication rule per claim: the claim's stated direction (e.g.,
  `feature_X[a] − feature_X[i] > 0`) is computed on hold-out whales with the
  same aggregate; `replicated = sign matches AND |effect| > 0`. Margins and
  effect sizes are reported, not thresholded into significance language.
- Partition size is recorded; with four resolved whales the split is
  acknowledged as illustrative, and the report says so.

## Output contract

```json
{
  "schema_version": "0.1.0",
  "calibration_version": "calibration-v1",
  "split_rule": "sha256(whale_id + seed) mod 2",
  "groups": {"fit": ["ATWOOD"], "holdout": ["FORK", "PINCHY", "TBB"]},
  "claims": [
    {"claim_ref": "hypotheses.jsonl#rank-1", "direction": "a_minus_i_positive",
     "holdout_effect": 0.0, "replicated": true, "n_whales": 3}
  ],
  "corpus_replication_rate": 0.0,
  "caveats": ["4 resolved whales; split is illustrative"]
}
```

## Invariants

1. No whale leakage between fit and hold-out.
2. Split assignment is hash-deterministic; re-running yields identical groups.
3. Report language stays qualitative — no "p <", "significant", or
   probability-of-truth phrasing (lint-enforced).

## Acceptance criteria

- [ ] Golden test: fixed whale set ⇒ fixed split.
- [ ] Leakage test: no `whale_id` in both groups.
- [ ] Each claim produces a recorded result, including `replicated = false`.
- [ ] Language lint passes on the artifact.

## Stop conditions

Zero overlapping claims or an empty hold-out group ⇒
`state = indeterminate`; uncertainty labels remain `heuristic`.
