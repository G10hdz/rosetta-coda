# Session Handoff

**Last session**: 2026-09-18 19:39
**Project**: rosetta-coda
**Branch/repo**: `G10hdz/feat/add-sol-demo-submission` → github.com/G10hdz/rosetta-coda

## Current state
SPECs 000–013 all implemented, tested (145 pass), committed, pushed. PR #1 open
against `main`, awaiting human review. Live at https://rosetta-coda.vercel.app
(static: launcher + demo w/ real DeepSeek hypothesis + research console +
immutable artifacts). Sealed release at `artifacts/release/` verified by
`scripts/replay_release.py` (7/7 deterministic bit-identical, 6/6 sealed).

## What's next
- [ ] Human review + merge PR #1 (repo rule: not self-merged). Merge auto-deploys.
- [ ] Decide: slim `artifacts/release/` out of git (keep manifest + small
      citables, gitignore ~21MB intermediates) or keep self-contained.
- [ ] Next branch: drop `G10hdz/` prefix per repo convention.

## Blockers / notes
- Calibration `indeterminate` by design (4 whales all in holdout).
- 627/628 gate timing: codanum 5092 quarantined, surfaced in QC.
- Detector parity `unverified`: no published WAV fixtures.
- LLM env: `ROSETTA_API_KEY` (use `$DEEPSEEK_API_KEY` from ~/.env), base
  `https://api.deepseek.com`, model `deepseek-chat`.
- Vercel preset pinned `"framework": null` in vercel.json — required.
- Local untracked tooling dirs: `.impeccable/`, `.playwright-mcp/`, `.vercel/`.

## Key files touched
- `scripts/{run_pipeline,replay_release}.py` — orchestrator + verifier
- `phonology/{timing,features}.py`, `detector/envelope.py`,
  `interpretation/{hypotheses,ranking}.py`, `analysis/calibration.py`,
  `reporting/report.py`, `api/app.py` — SPECs 005–012
- `research/` — console (kimi) + time-time plot (grok)
- `artifacts/release/`, `artifacts/demo/hypothesis.json` — sealed + live model
- OSS docs: CONTRIBUTING/COC/SECURITY/CITATION/CHANGELOG, `.github/`, README,
  `docs/{architecture,roadmap}.md`
