# Session Handoff

**Last session**: 2026-09-18 20:47
**Project**: rosetta-coda
**Branch/repo**: `main` @ `7c8947d` → github.com/G10hdz/rosetta-coda

## Current state
PR #1 (pipeline SPECs 005–013 + six review blockers) and PR #3 (homepage
→ research console) are merged to `main`. Production
https://rosetta-coda.vercel.app/ returns 307 to `/research` (console HTML,
not the July launcher). `/demo/` still serves the duration-gate panel.
CI `gate` workflow is on `main` (fetches pinned CSVs, ruff, pytest).
Sealed release replay: 7/7 deterministic, 6/6 sealed. Tests: 152 passed.

## What's next
- [ ] Optional: API allowlist + persisted idempotency (SPEC-011).
- [ ] Optional: pydantic schema-repair retry inside `_structured_call`.
- [ ] Optional: single whale-set constant (`FOUR_WHALES` / `GATE_WHALES`).
- [ ] Decide whether to slim `artifacts/release/` out of git.

## Blockers / notes
- Calibration is no longer all-holdout: fit ATWOOD/FORK/TBB, holdout PINCHY,
  state `ok`, replication rate 0.5.
- 627/628 gate timing: codanum 5092 quarantined.
- Detector parity `unverified`: no published WAV fixtures.
- LLM: `ROSETTA_API_KEY` / DeepSeek `deepseek-chat`.
- Vercel `"framework": null` is required.
- #2 closed when #1 deleted its base; continuation was #3 (merged).
- Local untracked: `.impeccable/`, `.playwright-mcp/`, `.vercel/`.

## Key files touched
- `analysis/calibration.py`, `reporting/report.py`, `scripts/run_pipeline.py`
- `.github/workflows/gate.yml`, `tests/test_pipeline.py`
- `artifacts/release/` resealed (report model ID, split, replay command)
- `index.html`, `vercel.json` — `/` redirects to `/research/`
