# SPEC-009 — Contextual interpreter

Status: Accepted  
Owner: Engineering + scientific reviewer (confidence language)  
Depends on: SPEC-008

## Outcome

Rank a set of validated hypothesis candidates under a deterministic,
documented rubric so that researchers see the best-supported claims first,
each carrying its uncertainty kind and falsifiers.

## Scope

Included:

- Candidate set: `k` hypothesis candidates for the same frozen
  `AnalystEvidence` bundle (single list-mode model call or `k` recorded calls;
  generation detail belongs to SPEC-008).
- Deterministic ranking rubric `rank-v1` — pure code over validated fields.
- `RankedHypotheses` artifact: rank, score components, reasons, and the
  selection rule version.

Excluded:

- Learned ranking models.
- Calibrated confidence (SPEC-012).
- Human-in-the-loop reordering inside the artifact (reviewers re-rank
  downstream, outside the immutable record).

## Ranking rubric `rank-v1`

Score = weighted sum over each candidate (all inputs already validated):

| Component | Weight | Measure |
|---|---:|---|
| Evidence grounding | 0.40 | fraction of `evidence_refs` that resolve to numeric values × count capped at 5 |
| Falsifier specificity | 0.25 | falsifiers containing a measurable condition (numeric threshold, named test, or held-out cohort reference) |
| Alternative coverage | 0.20 | count of distinct alternatives, capped at 4 |
| Uncertainty honesty | 0.15 | `epistemic` or `model` kinds score 1.0; `sampling` 0.5 (a sampling claim on descriptive evidence overstates precision) |

Ties break by lexical `coda_id` order of first evidence ref, then claim text.
Scores and per-component values are emitted for audit.

## Output contract

```json
{
  "selection_rule_version": "rank-v1",
  "evidence_manifest": {"analyst_evidence_sha256": "..."},
  "ranked": [
    {
      "rank": 1,
      "score": 0.78,
      "score_components": {"evidence_grounding": 0.32, "...": "..."},
      "reasons": ["3/3 evidence refs resolve to numerics"],
      "hypothesis": "<HypothesisCandidate>",
      "uncertainty": {"kind": "epistemic", "label": "heuristic"}
    }
  ]
}
```

Every ranked entry keeps `alternatives`, `falsifiers`, `limitations`, and an
uncertainty kind in `{sampling, model, measurement, epistemic}`. Confidence is
labeled `heuristic` until SPEC-012 supplies empirical calibration.

## Invariants

1. Ranking is pure code: identical candidate set ⇒ identical ranking.
2. No candidate is edited by the interpreter; ranking annotates only.
3. Forbidden-claim lint runs on the final artifact.

## Acceptance criteria

- [ ] Golden ranking test: fixed candidate set ⇒ fixed order and scores.
- [ ] Weight table sums to 1.0; component values in artifact match
      recomputation.
- [ ] All entries carry uncertainty kind + falsifiers.
- [ ] Deterministic replay hash.

## Stop conditions

Fewer than one valid candidate ⇒ empty ranked artifact with
`state = indeterminate`; report stage notes the absence.
