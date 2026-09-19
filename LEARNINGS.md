# Learnings

### 2026-07-12 — Official vowel labels are separate from combinatorial metadata

- **Problem**: `DominicaCodas.csv` contains timing-based coda types but no verified a/i vowel-quality labels.
- **Root cause**: Spectral vowel quality was hand-annotated in a separate dataset released with the 2026 phonology paper.
- **Fix**: Use OSF `9T6QU` `codamd.csv`, pin its SHA-256, and reproduce only the published 1+1+3/four-whale subset.
- **Lesson**: Never infer acoustic quality from coda-type spelling; locate coda-level spectral labels and provenance.

### 2026-07-12 — ICI layout validation must be positional

- **Problem**: Simple non-zero ICI counting found three malformed rows but missed two more.
- **Root cause**: Two rows had the expected count of non-zero values, but zeros occurred inside the valid ICI span followed by later non-zero values.
- **Fix**: Require the first `nClicks-1` ICIs to be positive and every trailing ICI to be zero; quarantine all five rows with raw provenance.
- **Lesson**: Padding validation must check position and count, not count alone.

### 2026-09-18 — Held-out split must match SPEC-012 byte-for-byte

- **Problem**: Calibration was `indeterminate` because all four gate whales hashed into holdout.
- **Root cause**: `split_whales` used `sha256(f"{whale}:{seed}")` and `digest[0] % 2`. SPEC-012 is `sha256(whale_id + seed)` as an integer mod 2 (no colon, last bit of the digest).
- **Fix**: Concatenate `whale + seed`, `int.from_bytes(digest, "big") % 2`. Groups: fit ATWOOD/FORK/TBB, holdout PINCHY. Regeneration of sealed calibration/ranked/report.
- **Lesson**: The `split_rule` string on `CalibrationReport` is a published claim. If the function differs, the sealed JSON lies. Pin the formula with a unit test against the spec text.

### 2026-09-18 — Write the run manifest before the citable report

- **Problem**: `build_report` read `manifest.json` that did not exist yet. A clean first run omitted input hashes; the sealed copy only had them because a second run to the same `run_id` saw leftover files.
- **Root cause**: Orchestrator wrote the report, then the manifest.
- **Fix**: `write_run_manifest(...)` stub (inputs + artifacts so far) before `build_report`, then rewrite after report/events.
- **Lesson**: Provenance artifacts cannot cite a file the same function has not written. Test from an empty run dir, not a reused one.
