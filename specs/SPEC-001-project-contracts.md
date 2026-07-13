# SPEC-001 — Project bootstrap and contracts

Status: Verified  
Owner: Engineering  
Depends on: SPEC-000

## Outcome

Create a locked Python 3.11+ environment and shared typed contracts so later stages serialize and replay identically.

## Scope

Included: `pyproject.toml`, `uv.lock`, importable packages, Pydantic contracts, JSON Schema export, pytest/ruff configuration.  
Excluded: LangGraph, Claude calls, signal processing, UI.

## Repository contract

Initial task paths remain stable:

- `data/loader.py`
- `analysis/normalize.py`
- `contracts/models.py`
- `tests/`

Later modules may move under `src/rosetta_coda/` only through a separate accepted migration spec.

## Base artifact fields

Every persisted result includes:

- `schema_version`
- `run_id`
- `created_at`
- `producer`
- `code_revision` when repository revision exists
- `config_hash`
- `input_hashes`

## Acceptance criteria

- [x] `uv sync` succeeds from clean environment.
- [x] `uv run pytest` passes.
- [x] `uv run ruff check .` passes.
- [x] Contracts reject NaN, infinity, negative durations, and ICI layout inconsistent with click count.
- [x] JSON round-trip preserves all fields.
- [x] Generated JSON Schema is versioned.

## Stop conditions

Dependency resolution, schema round-trip, or validation failure blocks all data implementation.
