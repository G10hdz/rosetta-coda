# Demo Handoff — Rosetta Coda demo site

**For:** next agent (kimi 2.7 via opencode/fireworks)
**Do NOT:** commit, push, call OpenAI, access Doppler, spend API credits. Preserve `SESSION_HANDOFF.md`.

## What exists (done, working)

- `demo/index.html`, `demo/styles.css`, `demo/app.js` — single-viewport 16:9 dark
  scientific-instrument dashboard. Plain HTML/CSS/JS, no build deps.
- Loads real evidence from `/artifacts/gates/spec-004-duration-gate.json`:
  gate status + frozen hash, cohort funnel (1375→628, 338 a / 290 i, 4 whales),
  mixed-model β=−0.132 / p=3.7e-11 / t / groups / obs, per-whale a−i z-diff bars,
  model boundary warning.
- Sol hypothesis panel: renders live `/artifacts/demo/sol-hypothesis.json` if present,
  else a **clearly-labelled Preview mock** (`mockHypothesis()` in app.js). Mock evidence
  refs are real JSON Pointers into the gate. Never implied to come from Sol.
- Disclaimers present: "Not a whale translator." / "Deterministic science first." /
  "No semantic claims." + creed strip.
- `tests/test_demo_assets.py` — smoke test (9 pass): asset presence, disclaimers,
  gate-shape invariants, mock refs resolve, mock-not-labelled-as-Sol.
- README updated with one "Demo site (local preview)" section.
- Favicon inline data-URI added (kills favicon 404).

## Verification state

- `uv run pytest -q` → **71 passed**.
- `uv run ruff check .` → clean.
- Server: `python3 -m http.server 8000 --bind 127.0.0.1` (was running pid 33124).
  Probe: demo 200, gate 200, sol 404 (expected = Preview path).
- Console: only benign 404s (favicon now fixed; sol 404 is the intended no-live-call path,
  a network log not a JS error).

## THE ONE REMAINING BUG (fix this first)

In the Sol panel the **claim title + Preview note get clipped at the top** of the
scroll region — see screenshot `rc-demo-1.jpeg`. Only the tail of the claim shows.
For a 30-sec recording the claim headline + PREVIEW label MUST be visible without scroll.

**Fix:** in `renderHypothesis()` (app.js) + markup (index.html) + `styles.css`,
split the hypothesis panel into:
1. a **pinned** region (not scrollable): compact Preview note (one line, not the big
   red box), claim `title`, claim `text`.
2. a **scrollable** `.hypo__detail` region: evidence refs, uncertainty, alternatives,
   falsifiers, limitations, meta chips.
Keep `.creed` pinned at bottom. Shrink the current `preamble` error-box to a single
compact line (the PREVIEW badge already labels origin). Tighten `.hblock` margins so
all 9 list items fit at 810px height when possible.

## Acceptance gates

- At 1440×810, claim title + Preview label visible without scrolling; nothing overflows body.
- `uv run pytest -q` still 71 passed; `uv run ruff check .` clean.
- Reload `http://localhost:8000/demo/` — no NEW console errors (favicon gone; sol 404 ok).
- Mock still clearly labelled; never presented as a Sol output.
- Design stays coherent dark ocean instrument (see rc-demo-1.jpeg for current look).

## Optional polish (if time)

- Draw inspiration from Project CETI "Listen" (listen.projectceti.org): click-train
  motif already used in the glyph — could echo in a subtle panel header or loading state.
- Per-whale bars are near-equal height (z 0.81–0.90, honest); consider a faint 0-baseline
  label or raw-seconds tooltip for scale context. Do NOT invent data.
