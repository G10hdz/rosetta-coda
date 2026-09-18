from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse

ARTIFACTS_ROOT = Path("artifacts/runs")
MAX_LIMIT = 500

app = FastAPI(title="Rosetta Coda", version="0.1.0")

# Idempotency-Key -> run_id for POST /v1/runs
_IDEMPOTENT_RUNS: dict[str, str] = {}


def _error(status: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": details or {}}},
    )


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body("http_error", str(exc.detail)),
    )


def _run_dir(run_id: str) -> Path:
    if "/" in run_id or ".." in run_id or "\\" in run_id:
        raise _error(400, "invalid_run_id", "run_id contains illegal characters")
    path = ARTIFACTS_ROOT / run_id
    if not path.is_dir():
        raise _error(404, "run_not_found", f"no run {run_id!r}")
    return path


def _artifact_path(run_dir: Path, name: str) -> Path:
    if "/" in name or ".." in name or "\\" in name:
        raise _error(400, "invalid_artifact_name", "artifact name must be a plain filename")
    path = run_dir / name
    if not path.is_file():
        raise _error(404, "artifact_not_found", f"no artifact {name!r} in run")
    return path


@app.post("/v1/runs", status_code=201)
def start_run(idempotency_key: str = Header(alias="Idempotency-Key")) -> dict[str, Any]:
    if not idempotency_key:
        raise _error(400, "missing_idempotency_key", "Idempotency-Key header required")
    if idempotency_key in _IDEMPOTENT_RUNS:
        run_id = _IDEMPOTENT_RUNS[idempotency_key]
        return {"run_id": run_id, "state": "existing", "idempotent": True}

    from scripts.run_pipeline import run_pipeline

    run_dir, gate_state = run_pipeline()
    run_id = Path(run_dir).name
    _IDEMPOTENT_RUNS[idempotency_key] = run_id
    return {"run_id": run_id, "state": gate_state, "idempotent": False}


@app.get("/v1/runs")
def list_runs() -> dict[str, Any]:
    if not ARTIFACTS_ROOT.is_dir():
        return {"runs": []}
    runs = sorted(p.name for p in ARTIFACTS_ROOT.iterdir() if p.is_dir())
    return {"runs": runs}


@app.get("/v1/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run_dir = _run_dir(run_id)
    manifest = _artifact_path(run_dir, "manifest.json")
    data = json.loads(manifest.read_text())
    return {
        "run_id": run_id,
        "gate_state": data.get("gate_state"),
        "model_stage": data.get("model_stage"),
        "artifacts": sorted((data.get("artifacts") or {}).keys()),
        "manifest_sha256": data.get("manifest_sha256"),
    }


@app.get("/v1/runs/{run_id}/codas")
def get_codas(
    run_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=MAX_LIMIT),
) -> dict[str, Any]:
    run_dir = _run_dir(run_id)
    phonology = run_dir / "spec-007-phonology.jsonl"
    if not phonology.is_file():
        raise _error(404, "artifact_not_found", "no phonology features in this run")

    records: list[dict[str, Any]] = []
    with phonology.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    records.sort(key=lambda r: r["coda_id"])

    start = 0
    if cursor is not None:
        try:
            decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            start = int(decoded["offset"])
        except Exception:
            raise _error(400, "invalid_cursor", "cursor is not a valid position token")
        if start < 0 or start > len(records):
            raise _error(400, "invalid_cursor", "cursor out of range")

    page = records[start : start + limit]
    next_cursor = None
    if start + limit < len(records):
        token = json.dumps({"offset": start + limit})
        next_cursor = base64.urlsafe_b64encode(token.encode()).decode()
    return {
        "run_id": run_id,
        "count": len(page),
        "total": len(records),
        "next_cursor": next_cursor,
        "codas": page,
    }


@app.get("/v1/runs/{run_id}/artifacts/{name}")
def get_artifact(run_id: str, name: str) -> Response:
    run_dir = _run_dir(run_id)
    path = _artifact_path(run_dir, name)
    media = "application/jsonl" if name.endswith(".jsonl") else "application/json"
    if name.endswith(".md"):
        media = "text/markdown"
    return Response(content=path.read_bytes(), media_type=media)


@app.get("/v1/runs/{run_id}/events")
def get_events(run_id: str) -> StreamingResponse:
    run_dir = _run_dir(run_id)
    events = _artifact_path(run_dir, "events.jsonl")
    lines = events.read_text().splitlines()

    def stream():
        for seq, line in enumerate(lines):
            yield f"id: {seq}\nevent: stage\ndata: {line}\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


__all__ = ["app"]
