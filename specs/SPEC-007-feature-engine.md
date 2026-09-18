# SPEC-007 — Deterministic phonological feature engine

Status: Accepted  
Owner: Engineering + scientific reviewer  
Depends on: SPEC-005, SPEC-004 (pass)

## Outcome

Compute reproducible rhythm, tempo, ornament, and rubato features per coda so
that hypothesis generation grounds in explicit measurements — including on the
frozen 628-coda gate partition, where the verified a/i duration effect can be
decomposed into timing structure.

## Scope

Included:

- Per-coda features from `CodaTiming` records (metadata and detector sources).
- Aggregate features per cohort (vowel `a`/`i`, coda type, whale) on the gate
  partition.
- `phonology.jsonl` + `FeatureSet` artifact with code version and input hashes.

Excluded:

- Any learned or stochastic feature.
- Semantic labels.
- Audio-dependent features (spectral quality, formants, edge-click
  coarticulation): emitted as `not_observable` unless SPEC-006 supplies
  detections — currently it does not.

## Feature definitions

Per coda (all deterministic, version `phonology-features-v1`):

| Feature | Definition |
|---|---|
| `click_rate_hz` | `click_count / duration_s` |
| `mean_ici_s` | mean of `icis_s` |
| `ici_cv` | sample sd / mean of `icis_s` (ddof=1; null if fewer than 2 ICIs) |
| `npvi` | `100 × mean(|ici_i − ici_{i+1}| / ((ici_i + ici_{i+1})/2))` over successive ICI pairs (normalized pairwise variability index; null if fewer than 3 ICIs) |
| `ici_pattern` | `ici_s / mean_ici_s` per position (unitless rhythm shape) |
| `initial_ici_ratio` | `icis_s[0] / mean(icis_s[1:])` (null if fewer than 2 ICIs) |
| `terminal_ici_ratio` | `icis_s[-1] / mean(icis_s[:-1])` — coda-final lengthening analogue |
| `rubato_slope` | OLS slope of ICI vs ordinal position, normalized by `mean_ici_s` (null if fewer than 3 ICIs) |
| `drift_s` | `icis_s[-1] − icis_s[0]` |
| `duration_z` | carried from SPEC-003 normalization when the coda is in the resolved cohort |
| `spectral_quality`, `formants`, `edge_coarticulation` | `not_observable` |

Aggregates on the gate partition: per whale × vowel means of the above, plus
cohort-level contrasts `a − i` for each feature with a whale-cluster bootstrap
(seed fixed, 10,000 iterations).

## Input contract

- `ExtractionResult` timings (SPEC-005).
- `NormalizationResult` (SPEC-003) for `duration_z`.
- Gate partition membership from the SPEC-004 artifact.

## Output contract

`PhonologyFeature` records keyed by `coda_id`; `FeatureSet` artifact:

```json
{
  "code_version": "phonology-features-v1",
  "input_hashes": {"extraction": "...", "normalization": "..."},
  "n_features": 8714,
  "n_gate_partition": 627,
  "partition_contrasts": [{"feature": "ici_cv", "a_minus_i": ..., "ci95": [...]}]
}
```

## Invariants

1. Pure functions only; same inputs ⇒ identical hashes.
2. Unresolved-cohort codas get features but never `duration_z`.
3. Nulls are explicit (`null`), never zero-filled.
4. No semantic claims anywhere in the artifact.

## Acceptance criteria

- [ ] Known-answer fixtures: synthetic ICIs with hand-computed nPVI, CV,
      ratios, slope.
- [ ] Null behavior at boundary click counts (1, 2, 3 clicks).
- [ ] Gate-partition feature table reproduces the published duration effect
      sign (`a − i > 0` for `mean_ici_s`-consistent measures).
- [ ] Deterministic replay hash.

## Stop conditions

Feature values failing golden fixtures or partition membership mismatch
returns `failed`; blocks SPEC-008.
