# SPEC-004 — a/i duration reproduction gate

Status: Verified — PASS  
Owner: Engineering + scientific reviewer  
Depends on: SPEC-003

## Outcome

Determine whether a-codas are longer than i-codas after controlling individual duration baselines, using frozen labels and analysis.

## Verified source

The published paper points to OSF DOI `10.17605/OSF.IO/9T6QU`. Rosetta Coda pins:

- `codamd.csv`, SHA-256 `e3fc6b402eeafa94a168ed215255255ed3d3acbeef2d65abe54312526b42a899`;
- `PhonologyCodaVowel.R`, SHA-256 `56d2aed123b0a712b31473220ee0d4d7f7735d9ee95aedb7b128e224375cd1fa`;
- `README.9t6qu.md`, SHA-256 `253b5f51bb9585f8484b997970203c7f464e9790324adf722d85cd1283c3733f`.

`codamd.csv` contains 1,375 codas and a human annotation column `handv` with `a`, `i`, or blank. These labels are independent of timing-based `codatype`; no mapping is inferred.

## Frozen primary replication

- Input: pinned `codamd.csv`.
- Label: human `handv`; retain only exact `a` or `i`.
- Coda type: exact `1+1+3` only, preventing duration differences caused by click-count/timing type.
- Whales: `ATWOOD`, `FORK`, `PINCHY`, `TBB`.
- Expected eligible sample: 628 codas: 338 `a`, 290 `i`.
- Published model: `Duration ~ Vowel + (Vowel | whale)`, treatment-coded with `a` baseline.
- Published target: coefficient for `i` approximately `-0.13 s`, `t=-6.84`, `p=0.017` under R `lmerTest`.
- Python replication: REML mixed-effects model with random intercept and vowel slope by whale; compare coefficient direction and magnitude. Inferential values may differ because Python does not reproduce `lmerTest` Satterthwaite degrees of freedom exactly.
- No outlier removal or imputation.
- Short versus long `ī` is not separated for this gate; both remain under hand label `i`, matching published duration analysis.

## Supporting normalized analysis

Using SPEC-003 z-scores fitted within the frozen 628-row partition, compute per-whale `mean(duration_z[a]) - mean(duration_z[i])`. All four effects must be positive. Report equal-whale aggregate descriptively; it does not replace the published mixed model.

- `pass`: hashes match; sample counts match; mixed-model `i` coefficient is negative and within `0.02 s` of `-0.13`; all four raw and normalized within-whale `a-i` effects are positive.
- `fail`: valid frozen data/model runs but any scientific criterion is not met.
- `indeterminate`: hash, schema, convergence, or eligible-sample requirements are not met.

Observed pre-implementation fixture means are recorded only as loader verification, not as gate execution: raw `a-i` differences are positive for all four whales (approximately 0.148, 0.159, 0.072, and 0.168 s).

## Output contract

Machine-readable gate artifact containing preregistration hash, cohort flow, per-whale effects, aggregate estimate, uncertainty interval, sensitivity results, and final state. No downstream stage accepts any state except `pass`.

Verified result: 628 codas, 338 `a`, 290 `i`, four whales; REML coefficient for `i` = `-0.131844 s`; all four raw and normalized within-whale `a-i` effects positive. Artifact: `artifacts/runs/foundation-53dd44fbfb00-e3fc6b402eea/spec-004-duration-gate.json`.

## Stop conditions

Hash drift, post-hoc mapping, join ambiguity, failed quality checks, convergence failure, or sample mismatch returns `indeterminate` and stops roadmap.
