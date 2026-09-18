# SPEC-013 — Reproducible research release

Status: Accepted  
Owner: Engineering  
Depends on: SPEC-012

## Outcome

Replay the complete analysis from a clean environment against locked inputs
and produce a verification report so that a third party can confirm every
artifact bit-for-bit without trusting the original run.

## Scope

Included:

- `scripts/replay.py`: regenerates every deterministic artifact from pinned
  inputs in a fresh `artifacts/runs/` directory and compares SHA-256 against
  the reference manifest.
- `REPRODUCE.md`: exact environment + commands (Python 3.11, `uv sync`,
  pinned input hashes).
- Reference manifest: `artifacts/release/manifest.json` listing every
  artifact name → sha256 for the released golden run.
- Replay report artifact: per-artifact match/mismatch and overall verdict.

Excluded:

- LLM-call replay: model outputs are non-deterministic; the released
  hypothesis artifact is included in the manifest as a *shipped* artifact
  (hash-verified, not regenerated). The report states this explicitly.
- Container packaging (uv.lock is the reproducibility contract).

## Replay contract

1. Verify pinned inputs exist with expected SHA-256
   (`DominicaCodas.csv`, `codamd.csv`, `PhonologyCodaVowel.R`, README).
2. Run the deterministic pipeline end-to-end into a scratch run directory.
3. Compare each regenerated artifact hash to the reference manifest.
4. Emit `replay-report.json`: `{verdict: match|mismatch, per_artifact: {...},
   skipped: ["hypothesis.json (model output, shipped not regenerated)"]}`.
5. Exit non-zero on any mismatch.

## Invariants

1. No network access during replay (deterministic stages need none).
2. The reference manifest covers every released artifact; an unmanifested
   file in the release tree is a failure, not a warning.
3. Replay never writes into the released run directory.

## Acceptance criteria

- [ ] `uv run python -m scripts.replay` on a clean checkout returns `match`.
- [ ] Corrupted-input fixture produces `mismatch` with the artifact named.
- [ ] Manifest completeness check fails on an extra unmanifested file.
- [ ] `REPRODUCE.md` commands are exactly what replay executes.

## Stop conditions

Input hash failure stops before any computation (`inputs_mismatch`); the
release is considered broken until resolved.
