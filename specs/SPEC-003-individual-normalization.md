# SPEC-003 — Individual duration normalization

Status: Verified  
Owner: Engineering  
Depends on: SPEC-002

## Outcome

Remove individual duration baselines from eligible codas while keeping unresolved observations separate.

## Input contract

Validated canonical codas from SPEC-002. Only `identity_status=resolved`, finite `duration_s`, and rows not quarantined by QC are eligible.

## Algorithm

For each whale:

- `n`: eligible rows.
- `baseline_mean_s = mean(duration_s)`.
- `baseline_sd_s = sample standard deviation(duration_s, ddof=1)`.
- `duration_z = (duration_s - baseline_mean_s) / baseline_sd_s`.

Minimum eligibility: `n >= 2` and `baseline_sd_s > 0`. Ineligible resolved whales receive explicit reason. Unresolved rows always receive `duration_z = null`.

Baseline is computed from the exact analysis partition supplied by caller. Train/test or gate partitions may never reuse a baseline fitted on held-out observations without explicit spec approval.

## Output contract

- `WhaleBaseline`: whale ID, `n`, mean, sample SD, partition ID, input hash.
- `NormalizedCoda`: coda ID, whale ID/status, raw duration, nullable z-score, baseline reference.
- `NormalizationResult`: baselines, normalized rows, excluded/quarantined rows, counts, evidence trace.

## Acceptance criteria

- [x] Synthetic whale groups produce mean z-score approximately zero and sample SD approximately one.
- [x] Constant-duration and singleton whales are explicit ineligible cases.
- [x] Unresolved and quarantined rows never influence baselines.
- [x] Row order does not change results.
- [x] Same input/config produces byte-stable canonical JSON.

## Stop conditions

Any unresolved row with non-null z-score, or any mismatch between baseline partition and analysis partition, fails normalization.
