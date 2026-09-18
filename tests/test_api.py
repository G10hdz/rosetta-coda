from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import api.app as api_app
from api.app import app


@pytest.fixture()
def run_root(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    run = root / "run-abc"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run-abc",
                "gate_state": "pass",
                "model_stage": "generated",
                "artifacts": {"gate": {"path": "x", "sha256": "0" * 64}},
                "manifest_sha256": "1" * 64,
            }
        )
    )
    (run / "spec-004-duration-gate.json").write_text('{"state": "pass"}')
    (run / "spec-010-report.md").write_text("# report\n")
    (run / "events.jsonl").write_text(
        '{"seq": 0, "stage": "foundation", "state": "pass"}\n'
        '{"seq": 1, "stage": "report", "state": "ok"}\n'
    )
    with (run / "spec-007-phonology.jsonl").open("w") as handle:
        for i in range(5):
            handle.write(json.dumps({"coda_id": f"dominica:{i}", "x": i}) + "\n")
    monkeypatch.setattr(api_app, "ARTIFACTS_ROOT", root)
    return root


@pytest.fixture()
def client(run_root):
    return TestClient(app)


class TestRuns:
    def test_list_runs(self, client):
        body = client.get("/v1/runs").json()
        assert body == {"runs": ["run-abc"]}

    def test_get_run(self, client):
        body = client.get("/v1/runs/run-abc").json()
        assert body["gate_state"] == "pass"
        assert body["manifest_sha256"] == "1" * 64
        assert "gate" in body["artifacts"]

    def test_unknown_run_404(self, client):
        resp = client.get("/v1/runs/nope")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "run_not_found"

    def test_run_id_traversal_400(self, client):
        resp = client.get("/v1/runs/..%2Fmanifest")
        assert resp.status_code in (400, 404, 422)


class TestArtifacts:
    def test_fetch_artifact(self, client):
        resp = client.get("/v1/runs/run-abc/artifacts/spec-004-duration-gate.json")
        assert resp.status_code == 200
        assert resp.json() == {"state": "pass"}

    def test_markdown_media_type(self, client):
        resp = client.get("/v1/runs/run-abc/artifacts/spec-010-report.md")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]

    def test_unknown_artifact_404(self, client):
        resp = client.get("/v1/runs/run-abc/artifacts/nope.json")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "artifact_not_found"

    def test_traversal_rejected(self, client):
        resp = client.get("/v1/runs/run-abc/artifacts/..%2Fmanifest.json")
        assert resp.status_code in (400, 404, 422)


class TestCodas:
    def test_pagination(self, client):
        first = client.get("/v1/runs/run-abc/codas?limit=2").json()
        assert first["count"] == 2
        assert first["total"] == 5
        assert first["next_cursor"] is not None
        assert first["codas"][0]["coda_id"] == "dominica:0"

        second = client.get(
            f"/v1/runs/run-abc/codas?limit=2&cursor={first['next_cursor']}"
        ).json()
        assert second["codas"][0]["coda_id"] == "dominica:2"

        last = client.get(
            f"/v1/runs/run-abc/codas?limit=2&cursor={second['next_cursor']}"
        ).json()
        assert last["count"] == 1
        assert last["next_cursor"] is None

    def test_invalid_cursor(self, client):
        resp = client.get("/v1/runs/run-abc/codas?cursor=garbage")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_cursor"

    def test_limit_cap(self, client):
        resp = client.get("/v1/runs/run-abc/codas?limit=9999")
        assert resp.status_code == 422


class TestEvents:
    def test_sse_replay(self, client):
        resp = client.get("/v1/runs/run-abc/events")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        text = resp.text
        assert "event: stage" in text
        assert '"stage": "foundation"' in text or '"stage":"foundation"' in text
        assert "event: end" in text


class TestStartRun:
    def test_missing_idempotency_key(self, client):
        resp = client.post("/v1/runs")
        assert resp.status_code in (400, 422)
