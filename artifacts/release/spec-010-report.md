# Rosetta Coda — run report `pipeline-53dd44fbfb00-e3fc6b402eea`

## Inputs and provenance
- `external/phonology-osf-9t6qu/codamd.csv` sha256 `e3fc6b402eeafa94a168ed215255255ed3d3acbeef2d65abe54312526b42a899`
- `external/sw-combinatoriality/data/DominicaCodas.csv` sha256 `53dd44fbfb0040da93656aa44883954f3abe18dd6539e90c625af86a96db6b45`
- 8719 rows loaded; cohort counts: `{"resolved": 2951, "unresolved_composite": 15, "unresolved_uncertain": 1, "unresolved_unknown": 5752}`

## Reproduction gate
- state: **pass** — All criteria met: hash match, sample counts match, i coefficient negative and within tolerance, all four within-whale raw and normalized a-i effects positive
- mixed model coefficient `vowel_code (i=1, a=0)` = -0.13184424421622426 (t=-6.614120539495718, p=3.73767095625381e-11, n=628)

## Feature summary
- 8714 coda feature records; 627 gate-partition codas

| feature | a − i | CI95 |
|---|---|---|
| click_rate_hz | -0.5423 | [-0.6917, -0.3588] |
| mean_ici_s | 0.03373 | [0.02309, 0.04058] |
| ici_cv | 0.03099 | [0.007418, 0.05441] |
| npvi | 2.137 | [0.2563, 4.017] |
| initial_ici_ratio | 0.05048 | [-0.009835, 0.1108] |
| terminal_ici_ratio | -0.01286 | [-0.02125, -0.004138] |
| rubato_slope | -0.01871 | [-0.03519, -0.002233] |
| drift_s | -0.03437 | [-0.04779, -0.0165] |

## Hypotheses

### #1 Within-whale monotone a>i effect across all four whales drives the pooled vowel contrast (score 0.633333)

For every whale in the frozen cohort, the within-whale raw difference a_minus_i is positive (ATWOOD 0.148, FORK 0.159, PINCHY 0.072, TBB 0.168) and the normalized z_diff is positive, matching the pooled negative vowel_code coefficient (-0.1318, p ~ 3.7e-11); this supports a consistent, same-direction vowel-associated effect across whales rather than a single-whale driver.

- uncertainty: model (heuristic)
- evidence: `/gate/per_whale_effects/0/raw_diff_a_minus_i`, `/gate/per_whale_effects/1/raw_diff_a_minus_i`, `/gate/per_whale_effects/2/raw_diff_a_minus_i`, `/gate/per_whale_effects/3/raw_diff_a_minus_i`, `/gate/mixed_model/n_groups`, `/gate/mixed_model/n_obs`, `/gate/state`, `/gate/summary`
- alternatives: The consistent sign across four whales could still arise from a shared recording or preprocessing pipeline rather than a biologically general pattern.; The mixed-model fit may be influenced by the MLE boundary warning, so the estimated coefficient could be biased or inflated.
- falsifiers: Adding more whales produces at least one whale with a negative raw_diff_a_minus_i exceeding the positive ones in magnitude.; Re-fitting without the boundary condition yields a coefficient whose sign or significance no longer matches the per-whale direction.; The per-whale effects are shown to be an artifact of unequal n_a vs n_i sampling within whales.

### #2 Vowel-conditioned click-rate contrast with lengthened a-intervals (score 0.608333)

In the frozen cohort, codas labeled with vowel 'a' are produced at a lower click_rate_hz than codas labeled 'i' (a_minus_i = -0.542 Hz, 95% CI entirely below zero), and this rate difference co-occurs with longer mean_ici_s for 'a' (a_minus_i = +0.0337 s, CI above zero), consistent with 'a'-labeled codas having more spaced click train timing rather than merely more clicks.

- uncertainty: sampling (heuristic)
- evidence: `/partition_contrasts/0`, `/partition_contrasts/1`, `/gate/mixed_model/coefficient_value`, `/gate/mixed_model/p_value`, `/whale_feature_means/0/means/click_rate_hz`, `/whale_feature_means/1/means/click_rate_hz`
- alternatives: The rate difference could reflect a per-whale production-style effect rather than a vowel-associated phonological contrast, since only four whales contribute.; The click_rate_hz contrast could be an artifact of duration normalization (duration_z) rather than an independent rate parameter.
- falsifiers: A re-partition with additional whales whose a_minus_i click_rate_hz CI includes zero.; Demonstration that the click_rate_hz contrast disappears after conditioning on mean_ici_s or click_count within this frozen cohort.; Evidence that the vowel labels are not comparable across whales (e.g., differing annotation conventions).

### #3 Rhythm-variability (NPVI and ICI-CV) increase in a-labeled codas (score 0.486905)

Within the frozen cohort, 'a'-labeled codas show higher timing variability than 'i'-labeled codas on two independent dispersion features: npvi (a_minus_i = +2.14, CI above zero) and ici_cv (a_minus_i = +0.031, CI above zero), while terminal_ici_ratio is lower for 'a' (a_minus_i = -0.0129, CI below zero), suggesting the vowel partition covaries with rhythmic dispersion and with the terminal inter-click interval specifically.

- uncertainty: sampling (heuristic)
- evidence: `/partition_contrasts/2`, `/partition_contrasts/3`, `/partition_contrasts/5`, `/feature_records_sample/0/npvi`, `/feature_records_sample/0/ici_cv`, `/feature_records_sample/0/terminal_ici_ratio`, `/feature_records_sample/48/npvi`
- alternatives: The npvi contrast, though CI-positive, could be dominated by a few high-NPVI outlier records rather than a systematic a/i distribution shift.; The terminal_ici_ratio contrast could reflect a boundary or segmentation artifact at the end of codas rather than a phonological property of the vowel partition.
- falsifiers: Recomputing the contrasts with outlier-trimmed records yields CIs spanning zero for npvi and/or ici_cv.; The terminal_ici_ratio effect reverses sign in an independent cohort with different segmentation parameters.; The npvi and ici_cv effects are found to be driven by click_count rather than vowel label.

## Calibration
- indeterminate

## Limitations

- No semantic ground truth exists; nothing in this report is a translation.
- Unresolved-identity codas are excluded from individual-controlled inference.
- Audio-dependent features are not_observable in this run (no WAV input).
- Confidence labels are heuristic unless an empirical calibration report exists.

## Cannot conclude

- coda meaning or semantic content
- individual whale intent
- clan-level grammar or syntax
- anything beyond measured click-timing structure

## Citations and reproduction

- DominicaCodas.csv — `53dd44fbfb0040da93656aa44883954f3abe18dd6539e90c625af86a96db6b45`
- codamd.csv (OSF 10.17605/OSF.IO/9T6QU) — `e3fc6b402eeafa94a168ed215255255ed3d3acbeef2d65abe54312526b42a899`
- code revision `2bc1fb3d0b8bd70396a4af7c6760552010c81e42`
- `uv sync --all-extras`
- `uv run python -m scripts.run_pipeline`
- `uv run python -m scripts.replay`
