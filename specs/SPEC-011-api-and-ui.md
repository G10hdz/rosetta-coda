# SPEC-011 — Local API and research UI

Status: Accepted  
Owner: Engineering  
Depends on: SPEC-010

## Outcome

Inspect, replay, and cite a complete run through a versioned local HTTP API
and a research UI that renders gate, feature, hypothesis, and report views —
with the UI also consumable as a static site reading frozen artifacts.

## Scope

Included:

- `api` module: FastAPI app over the immutable run store.
- `web` research UI (vanilla JS, same stack as `demo/`): gate panel, feature
  contrast table, ranked-hypothesis panel with evidence trace, report view,
  and per-coda rhythm (ICI pattern) and time-time scatter views.
- Golden-run replay contract: endpoints return byte-identical artifacts.

Excluded:

- Multi-user auth or cloud deployment (roadmap: no requirement).
- Write endpoints beyond run creation — no artifact mutation over HTTP.

## API contract

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/runs` | Start run from validated config; `Idempotency-Key` header required |
| `GET` | `/v1/runs` | List known runs |
| `GET` | `/v1/runs/{run_id}` | Run state and gate status |
| `GET` | `/v1/runs/{run_id}/codas` | Cursor-paginated coda/feature view (`cursor`, `limit` ≤ 500) |
| `GET` | `/v1/runs/{run_id}/artifacts/{name}` | Fetch immutable artifact (name allowlisted from manifest) |
| `GET` | `/v1/runs/{run_id}/events` | SSE stage/evidence event stream replayed from `events.jsonl` |

Errors: `{"error": {"code": "...", "message": "...", "details": {}}}`.
Artifact names outside the manifest allowlist return `404`; path traversal
returns `400`.

## UI contract

- Static assets under `web/`; reads `/artifacts/...` when served statically
  (Vercel) and `/v1/runs/{id}/artifacts/...` when served by the API — one
  configurable base URL, same code path.
- States: loading, populated, empty (`not_observable` / `not_generated` shown
  as first-class states, never blank panels).
- Reduced-motion respected; keyboard-operable controls; no invented data —
  every displayed number carries its artifact path in a `data-` attribute or
  tooltip.

## Acceptance criteria

- [ ] Golden-run replay: every manifest artifact is fetchable and
      byte-identical through the API.
- [ ] Pagination is stable (cursor on `coda_id` sort).
- [ ] Traversal/unknown artifact names rejected.
- [ ] Idempotent `POST /v1/runs`: same key ⇒ same `run_id`, no second run.
- [ ] UI contract test: static render of the frozen golden run (jsdom or
      screenshot fixture already used by `test_demo_assets.py` patterns).

## Stop conditions

API failure does not affect artifacts; the UI explicitly renders
`api_unavailable` when the backend is absent and falls back to static
artifact URLs.
