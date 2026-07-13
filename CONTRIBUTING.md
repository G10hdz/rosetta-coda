# Contributing to Rosetta Coda

Thanks for your interest. This is a scientific research project, and contributions must preserve reproducibility, auditability, and scientific integrity.

## Scope

Rosetta Coda is spec-driven. Before writing code, read the [roadmap](docs/roadmap.md) and check existing [specs](specs/). Every change should tie to an accepted spec.

- **Bugs and data issues** — open an issue with a minimal reproduction.
- **Feature work** — must start as a spec proposal (see `specs/SPEC_TEMPLATE.md`).
- **Scientific contributions** — label mappings, validated datasets, or phonological feature definitions require cited evidence and researcher review.

## Development setup

```bash
uv sync --all-extras
uv run pytest
```

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Format and lint: `uv run ruff check . && uv run ruff format --check .`

## Code conventions

- Type-annotated Python (Pydantic v2 for contracts)
- Line length: 100
- Quote style: double
- No raw `chain-of-thought` in artifacts; use structured evidence traces
- Immutable artifacts: write via temp file + atomic rename

## Testing

- Test files in `tests/` mirror the package structure
- Golden tests for dataset-level expected counts and hashes
- `pytest -m slow` for statistical integration tests
- Reproduce gate results before changing related code

## Pull request process

1. Open an issue or reference an existing spec
2. Implement against the spec's acceptance criteria
3. Include or update tests
4. Verify all tests pass and lints are clean
5. Supply an evidence bundle per the spec completion checklist

## Conduct

Be respectful, precise, and cite your sources. This project follows a standard [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.
