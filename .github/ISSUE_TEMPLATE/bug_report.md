---
name: Bug report
about: Something broke or produced a wrong result
title: ""
labels: bug
---

## What happened

<!-- Expected vs actual. Paste error output. -->

## Reproduction

<!-- Minimal steps. Include the command you ran and, if relevant, the
     artifact or input file involved. -->

## Environment

- OS:
- Python: <!-- `uv run python -V` -->
- Commit: <!-- `git rev-parse HEAD` -->

## Integrity check

- [ ] Does this affect a frozen artifact or gate result? If so, which
      `artifacts/` file and which sha256 in `manifest.json`?
- [ ] Does it involve a semantic, intent, or translation claim? (Those are
      never valid output — say so explicitly.)
