from __future__ import annotations

import json

from scripts.run_pipeline import analyst_candidates, write_run_manifest
from storage.io import write_json_atomic


class Boom:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("model down")


def test_analyst_candidates_failure_is_generation_failed(monkeypatch):
    monkeypatch.setenv("ROSETTA_API_KEY", "sk-test")
    monkeypatch.setattr("scripts.run_pipeline.generate_candidates", Boom)
    candidates, records, state = analyst_candidates(object(), run_model_stage=True)
    assert candidates == []
    assert records == []
    assert state == "generation_failed"


def test_analyst_candidates_skips_without_key(monkeypatch):
    monkeypatch.delenv("ROSETTA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    candidates, records, state = analyst_candidates(object(), run_model_stage=True)
    assert candidates == []
    assert records == []
    assert state == "skipped_no_api_key"


def test_stub_manifest_carries_inputs(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    artifact = write_json_atomic({"state": "pass"}, run / "gate.json")
    manifest = write_run_manifest(
        run,
        run_id="run-test",
        inputs={"DominicaCodas.csv": "a" * 64, "codamd.csv": "b" * 64},
        artifact_paths={"gate": artifact},
        gate_state="pass",
        model_stage="skipped_no_api_key",
    )
    on_disk = json.loads((run / "manifest.json").read_text())
    assert on_disk["inputs"]["DominicaCodas.csv"] == "a" * 64
    assert on_disk["artifacts"]["gate"]["sha256"] == manifest["artifacts"]["gate"]["sha256"]
    assert len(on_disk["manifest_sha256"]) == 64
