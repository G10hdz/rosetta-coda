# Session Handoff

**Last session**: 2026-07-12 21:24 CST  
**Project**: Rosetta Coda  
**Branch/repo**: no root git repository; upstream dataset repo lives under `external/`

## Current state

Foundation specs `SPEC-000` through `SPEC-004` are verified. Metadata loader, unresolved identity cohorting, per-whale z-score normalization, typed contracts, JSON Schema, atomic artifacts, and reproducible foundation runner exist. Official a/i labels and code were pinned from OSF `9T6QU`. Published duration result reproduces: gate `pass`, REML i coefficient `-0.131844 s`, 628 codas, four whales.

## What's next

- [ ] Scientific review/acceptance of `SPEC-004` result and limitations.
- [ ] Draft `SPEC-005` metadata-first Coda Extractor.
- [ ] Decide whether to initialize root git repository before more work.
- [ ] Keep audio-dependent spectral/coarticulation outputs `not_observable` until WAV evidence exists.

## Blockers / notes

- No current blocker: gate passed.
- `DominicaCodas.csv`: 8,719 rows; permissive loader emits 8,714 records and quarantines five malformed ICI layouts.
- Unresolved cohort never receives `whale_id` or z-score.
- Foundation run: `artifacts/runs/foundation-53dd44fbfb00-e3fc6b402eea/`.
- Verification: 55 tests, Ruff clean, `uv.lock` current.
- Long-term memories: `2d915f9d-7f33-4837-846b-48d55087b242`, `0fab02d6-4bd0-4424-9ec2-5f84fe3d498d`.

## Key files touched

- `data/loader.py` — validated loader, identity cohorts, typed quarantine.
- `analysis/normalize.py` — deterministic resolved-only z-scores.
- `analysis/reproduce_duration.py` — pinned REML reproduction gate.
- `contracts/models.py` — typed scientific contracts.
- `scripts/run_foundation.py` — reproducible artifact runner.
- `docs/architecture.md`, `docs/roadmap.md` — modular architecture and spec roadmap.

## Resume prompt

Read `SESSION_HANDOFF.md`, `docs/roadmap.md`, and `specs/SPEC-004-ai-duration-gate.md`. Confirm foundation artifact hashes, then draft `SPEC-005` only; do not build later stages or make semantic claims.
