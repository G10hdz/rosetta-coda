## Summary

<!-- One logical change. What and why — link the spec or issue. -->

Spec / issue:

## Verification

- [ ] `uv run ruff check .` clean
- [ ] `uv run pytest` green
- [ ] Touches pipeline code? → `uv run python -m scripts.replay_release` reports `verified`
- [ ] Intentional artifact change? → regenerated `artifacts/release/` in this PR, reason stated below

## Scientific integrity

- [ ] No semantic/intent claims introduced
- [ ] Downstream stages still stop on a non-`pass` gate
- [ ] Unresolved identities excluded from individual-controlled calculations
- [ ] No secrets, keys, or provider logs committed

## Evidence bundle (spec changes only)

<!-- accepted spec hash · test result · artifact hashes · deviations -->
