# Demo Handoff — Rosetta Coda demo site

**For:** next agent  
**Do NOT:** commit/push unless asked; spend API credits without need. Preserve session notes.

## What exists (done, working)

- `demo/index.html`, `demo/styles.css`, `demo/app.js` — single-viewport 16:9 dark
  scientific-instrument dashboard. Plain HTML/CSS/JS, no build deps.
- Loads real evidence from `/artifacts/gates/spec-004-duration-gate.json`:
  gate status + frozen hash, cohort funnel (1375→628, 338 a / 290 i, 4 whales),
  mixed-model β=−0.132 / p=3.7e-11 / t / groups / obs, per-whale a−i z-diff bars,
  model boundary warning.
- Hypothesis panel: renders live `/artifacts/demo/hypothesis.json` if
  `artifacts/demo/manifest.json` has `hypothesis_available: true`, else a
  **clearly-labelled Preview mock** (`mockHypothesis()` in app.js). Mock evidence
  refs are real JSON Pointers into the gate. Never implied to come from a model.
- Disclaimers present: "Not a whale translator." / "Deterministic science first." /
  "No semantic claims." + creed strip.
- `tests/test_demo_assets.py` — smoke tests for assets, disclaimers, gate shape,
  mock refs, mock-not-labelled-as-model.
- Provider research: `docs/model-provider-research.md` (DeepSeek default).

## Verification

- `uv run pytest -q`
- `uv run ruff check .`
- Server: `python3 -m http.server 8000 --bind 127.0.0.1`
  Probe: demo 200, gate 200; hypothesis 404 expected when manifest flag is false.

## Live hypothesis

```bash
export ROSETTA_API_KEY=...
uv run python -m scripts.run_hypothesis_demo
# set artifacts/demo/manifest.json hypothesis_available → true
```

## Acceptance gates

- At 1440×810, claim title + Preview/Live label visible without scrolling.
- pytest green; ruff clean.
- Mock still clearly labelled when no live artifact.
- Design stays coherent dark ocean instrument.
