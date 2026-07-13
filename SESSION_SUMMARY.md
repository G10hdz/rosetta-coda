# Session Summary

## Session Summary (2026-07-12, 21:24 CST)

**Goal**: Establish a reproducible, scientifically honest foundation for Rosetta Coda and stop unless the published a-coda/i-coda duration result reproduces.

**Done**:

- Cloned and inspected `sw-combinatoriality`; documented real schemas and identity ambiguity.
- Designed modular-monolith architecture, evidence trace, and `SPEC-000` through `SPEC-013` roadmap.
- Located official 2026 paper data/code at OSF `9T6QU`; pinned files and hashes under `external/phonology-osf-9t6qu/`.
- Implemented `contracts/models.py`, `data/loader.py`, `analysis/normalize.py`, and `analysis/reproduce_duration.py`.
- Added versioned JSON Schema, atomic persistence, manifest hashes, and `scripts/run_foundation.py`.
- Reviewed adversarially: fixed unresolved identity leakage, order-dependent normalization, incorrect zero-duration exclusion, incomplete quarantine provenance, ML/REML mismatch, and upstream lint scope.
- Found five malformed ICI layouts, including two missed by non-zero counting alone.
- Reproduced published result: 628 eligible codas; i coefficient `-0.131844 s`; all four whales have positive a-i differences; gate `pass`.
- Verified 55 tests, Ruff, and `uv.lock`.

**In progress / unfinished**:

- No Stage 2–4 pipeline work started.
- `SPEC-005` remains draft work for next session.
- Root directory is not a git repository, so no commit exists.

**Decisions made**:

- Unresolved IDs stay separate and always receive `whale_id=null`, `duration_z=null`.
- Numeric science remains deterministic; LLMs only generate typed, falsifiable hypotheses over frozen evidence.
- UI exposes structured evidence traces, never private chain-of-thought.
- Metadata-only runs cannot claim spectral quality or coarticulation observations.
- Only gate `pass` unlocks downstream specs.

**Next steps**:

- Obtain scientific sign-off on `SPEC-004` and its exact replication language.
- Draft `SPEC-005` metadata-first extractor with acceptance fixtures.
- Initialize git if desired before new implementation.
