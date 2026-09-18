# SPEC-005 — Metadata-first coda extractor

Status: Accepted  
Owner: Engineering  
Depends on: SPEC-002 (pass), SPEC-004 (pass)

## Outcome

Produce canonical per-click timing records from validated metadata so that
downstream phonological measurement operates on one immutable representation,
with duration inconsistencies surfaced rather than repaired.

## Scope

Included:

- Canonical `CodaTiming` records for every valid `CodaRecord` from the
  Dominica corpus.
- Canonical `CodaTiming` records for the codamd gate partition via the verified
  `codanum == codaNUM2018` join (all 1,375 codamd rows join).
- QC report artifact covering counts, duration-consistency flags, and
  cross-file mismatches.

Excluded:

- Audio-derived timing (SPEC-006).
- Feature computation (SPEC-007).
- Identity re-classification: extraction is identity-agnostic; downstream
  stages decide eligibility.

## Input contract

- `LoadResult.records` from `load_dominica_codas` (permissive mode).
- `external/phonology-osf-9t6qu/codamd.csv`, pinned by SHA-256, joined to
  Dominica rows on `codanum == codaNUM2018`; ambiguous or missing joins are
  surfaced, never guessed.

## Output contract

`CodaTiming`:

```json
{
  "coda_id": "dominica:1234",
  "source_ref": {"dataset": "DominicaCodas.csv", "row": 1234},
  "click_count": 5,
  "click_times_s": [0.0, 0.20, 0.42, 0.66, 0.91],
  "icis_s": [0.20, 0.22, 0.24, 0.25],
  "duration_s_reported": 0.91,
  "duration_residual_s": 0.0,
  "duration_consistent": true
}
```

`ExtractionResult` artifact: timings, QC report (counts, flagged residuals,
join mismatches), input hashes. Known corpus expectations:

- 8,714 timings from the Dominica load; 7 rows with
  `duration_consistent = false` (max residual ~0.0096 s). Ten raw duration
  mismatches exist in the file, but 3 sit inside rows quarantined by the
  loader for ICI-layout inconsistency (including the ~0.225 s outlier) and
  never reach extraction.
- 1,374 timings through the codamd join; 4 cross-file duration mismatches
  flagged. Codanum 5092 is a member of the published 628-coda gate
  partition whose Dominica row was quarantined by SPEC-002 QC, so it is
  reported as unjoined rather than reconstructed — the feature partition
  therefore covers 627/628 gate codas.

## Invariants

1. Round-trip `icis_s -> click_times_s -> icis_s` is exact within `1e-6` by
   construction (`click_times_s[0] == 0.0`; cumulative sums of `icis_s`).
2. `duration_residual_s = duration_s_reported - sum(icis_s)` is reported, never
   corrected.
3. No record is dropped at this stage; QC flags travel with the record.
4. No semantic content.

## Acceptance criteria

- [ ] Known fixture counts and flagged-residual counts match golden values.
- [ ] Round-trip property holds for every record (property test).
- [ ] Join produces exactly 1,375 timings; duplicate `codanum` would fail.
- [ ] Deterministic replay: identical input produces identical artifact hash.

## Stop conditions

Join ambiguity (duplicate `codanum`), schema drift, or residual counts
differing from golden values without explanation returns `failed` and blocks
SPEC-007.
