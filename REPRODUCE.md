# Reproducing the release

The golden run in `artifacts/release/` is content-addressed: every artifact's
sha256 is pinned in `artifacts/release/manifest.json`, keyed by the sha256 of
the two source CSVs.

## Verify

```bash
uv sync
uv run python -m scripts.replay_release
```

Expected output ends with:

```
verified: 7/7 deterministic replayed, 6/6 sealed verified
```

## What is replayed vs. sealed

Replayed bit-for-bit (deterministic stage):

- `spec-002-load.json`, `spec-003-normalization.json`,
  `spec-004-duration-gate.json`
- `spec-005-extraction.json`
- `spec-007-phonology.jsonl`, `spec-007-featureset.json`
- `spec-008-analyst-evidence.json`

Sealed by hash (model stage; a fresh call would differ, so integrity is
verified against the manifest, not reproduced):

- `spec-008-model-calls.jsonl`
- `spec-009-ranked-hypotheses.json` / `.jsonl`
- `spec-010-report.json` / `.md`
- `spec-012-calibration.json`

## Regenerate from scratch

```bash
uv run python -m scripts.run_pipeline            # full run, needs ROSETTA_API_KEY
uv run python -m scripts.run_pipeline --no-model # deterministic stages only
```

Outputs land in `artifacts/runs/pipeline-<dataset-hash>-<codamd-hash>/`; the
run id is derived from input hashes, so identical inputs always produce the
same run directory.

Environment: Python 3.11+, dependencies locked in `uv.lock`.
