# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project
versions its release artifacts by content hash, not calendar.

## [0.1.0] — first sealed release

### Added

- Deterministic pipeline SPECs 000–007: metadata ingestion with identity
  cohorting, per-whale z-score normalization, preregistered SPEC-004
  duration gate (`pass`: 628 observations, four whales), metadata coda
  extraction with codamd join QC, optional WAV detector, phonological
  feature engine (rhythm, tempo, ornament, rubato) with bootstrap CIs.
- Model stage SPECs 008–010: analyst adapter over frozen evidence bundles,
  `rank-v1` contextual interpreter (3 ranked hypotheses with resolvable
  JSON-Pointer evidence refs, alternatives, falsifiers, limitations),
  citable report generator.
- SPECs 011–013: local read-only FastAPI, static research console,
  held-out calibration (`indeterminate` — degenerate 4-whale split),
  replay verification (`scripts/replay_release.py`).
- Sealed release `artifacts/release/` pinned by `manifest.json` sha256:
  7/7 deterministic artifacts replay bit-identically.
- Public static deployment: https://rosetta-coda.vercel.app
  (`/demo/` gate panel with live model hypothesis, `/research/` console
  with time-time plot, `/artifacts/` immutable JSON).

### Known limitations

- One gate coda (627/628 timing coverage) quarantined for ICI-layout
  inconsistency; surfaced in extraction QC, not repaired.
- Detector parity `unverified` — no published WAV/MATLAB fixtures.
- Confidence labels are `heuristic`; four whales are underpowered for
  held-out calibration.
