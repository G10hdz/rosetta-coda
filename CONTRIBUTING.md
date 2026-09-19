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

## Verifying the pipeline

Any change that touches `data/`, `analysis/`, `phonology/`, `detector/`,
`interpretation/`, `reporting/`, or `scripts/run_pipeline.py` must also pass
the release replay:

```bash
uv run python -m scripts.run_pipeline --no-model   # deterministic stages
uv run python -m scripts.replay_release          # must report "verified"
```

If a change intentionally alters a deterministic artifact, regenerate the
release (`scripts/run_pipeline.py`), update `artifacts/release/` in the same
PR, and state the reason in the description.

## Branches, commits, pull requests

GitHub Flow: `main` stays stable; every change arrives on a short branch.

- Branch names: `feature/<description>`, `fix/<description>`, `chore/<description>`
- One logical change per PR, preferably under 400 lines
- Conventional, human-voiced commit messages; no tool or AI attribution trailers
- Ask for review from someone else before merge; "looks good" is enough
- Merge with rebase; delete the branch after merge

## Secrets and model providers

- Never commit API keys, credentials, private URLs, or raw provider logs
  containing them. The LLM stage reads `ROSETTA_API_KEY` /
  `ROSETTA_BASE_URL` / `ROSETTA_MODEL`; keep values in your local env only.
- Public artifacts ship precomputed model outputs — never a live key-bearing
  endpoint. If a contribution needs a public model call, stop and discuss in
  an issue first.

## Static UI rules (`demo/`, `research/`)

- No frameworks, CDNs, or external requests beyond the artifact fetches
- Keyboard-operable controls, visible focus, `prefers-reduced-motion`
  respected, semantic HTML
- Every section degrades independently: a missing artifact renders an
  explicit state, never a crash or an invented value (`not_observable`,
  `not_generated`, `api_unavailable`)

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
