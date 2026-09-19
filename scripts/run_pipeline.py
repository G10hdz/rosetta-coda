from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from analysis.calibration import (
    apply_calibration_labels,
    evaluate_claims,
    lint_calibration_language,
)
from analysis.normalize import normalize_durations
from analysis.reproduce_duration import run_duration_gate
from data.loader import load_dominica_codas
from interpretation.hypotheses import (
    build_analyst_evidence,
    generate_candidates,
)
from interpretation.ranking import rank_candidates
from phonology.features import build_feature_set
from phonology.timing import extract_all
from reporting.report import build_report, render_markdown
from storage.io import sha256_file, write_json_atomic, write_jsonl_atomic

DEFAULT_DOMINICA = Path("external/sw-combinatoriality/data/DominicaCodas.csv")
DEFAULT_CODAMD = Path("external/phonology-osf-9t6qu/codamd.csv")

CANDIDATE_COUNT = 3


def _has_api_key() -> bool:
    return bool(os.environ.get("ROSETTA_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def write_run_manifest(
    run_dir: Path,
    *,
    run_id: str,
    inputs: dict[str, str],
    artifact_paths: dict[str, Path],
    gate_state: str,
    model_stage: str,
    evidence_manifest_sha256: str | None = None,
    note: str | None = None,
) -> dict:
    manifest: dict = {
        "run_id": run_id,
        "schema_version": "0.1.0",
        "inputs": inputs,
        "artifacts": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in artifact_paths.items()
        },
        "gate_state": gate_state,
        "model_stage": model_stage,
    }
    if evidence_manifest_sha256 is not None:
        manifest["evidence_manifest_sha256"] = evidence_manifest_sha256
    if note is not None:
        manifest["note"] = note
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest["artifacts"], sort_keys=True).encode()
    ).hexdigest()
    write_json_atomic(manifest, run_dir / "manifest.json")
    return manifest


def analyst_candidates(
    evidence,
    *,
    run_model_stage: bool,
) -> tuple[list, list, str]:
    """Run the LLM candidate stage. Failures do not abort deterministic work."""
    if not run_model_stage:
        return [], [], "not_generated"
    if not _has_api_key():
        return [], [], "skipped_no_api_key"
    try:
        candidates, records = generate_candidates(evidence, k=CANDIDATE_COUNT)
    except Exception:
        return [], [], "generation_failed"
    state = "generated" if candidates else "generation_failed"
    return candidates, records, state


def run_pipeline(
    dominica_path: Path = DEFAULT_DOMINICA,
    codamd_path: Path = DEFAULT_CODAMD,
    artifacts_root: Path = Path("artifacts/runs"),
    run_model_stage: bool = True,
) -> tuple[Path, str]:
    loaded = load_dominica_codas(str(dominica_path), qc_mode="permissive")
    normalized = normalize_durations(
        loaded.records,
        partition_id="dominica-all-valid-v1",
        input_hash=loaded.dataset_hash,
    )
    gate = run_duration_gate(str(codamd_path))
    run_id = f"pipeline-{loaded.dataset_hash[:12]}-{gate.codamd_hash[:12]}"
    run_dir = artifacts_root / run_id
    events: list[dict] = []

    artifact_paths: dict[str, Path] = {}
    artifact_paths["load"] = write_json_atomic(
        loaded, run_dir / "spec-002-load.json"
    )
    artifact_paths["normalization"] = write_json_atomic(
        normalized, run_dir / "spec-003-normalization.json"
    )
    artifact_paths["gate"] = write_json_atomic(
        gate, run_dir / "spec-004-duration-gate.json"
    )
    events.append({"seq": len(events), "stage": "foundation", "state": gate.state.value})

    extraction = extract_all(loaded, codamd_path=codamd_path)
    artifact_paths["extraction"] = write_json_atomic(
        extraction, run_dir / "spec-005-extraction.json"
    )
    features, feature_set = build_feature_set(extraction, normalized)
    artifact_paths["phonology"] = write_jsonl_atomic(
        features, run_dir / "spec-007-phonology.jsonl"
    )
    artifact_paths["featureset"] = write_json_atomic(
        feature_set, run_dir / "spec-007-featureset.json"
    )
    events.append(
        {"seq": len(events), "stage": "features", "state": "ok",
         "n_partition": feature_set.n_gate_partition}
    )

    inputs = {
        str(dominica_path): loaded.dataset_hash,
        str(codamd_path): gate.codamd_hash,
    }
    if gate.state.value != "pass":
        write_run_manifest(
            run_dir,
            run_id=run_id,
            inputs=inputs,
            artifact_paths=artifact_paths,
            gate_state=gate.state.value,
            model_stage="not_generated",
            note="gate did not pass; downstream stages not run",
        )
        return run_dir, gate.state.value

    stage_hashes = {
        name: sha256_file(path) for name, path in artifact_paths.items()
    }
    evidence = build_analyst_evidence(
        gate,
        feature_set,
        evidence_manifest=stage_hashes,
    )
    artifact_paths["evidence"] = write_json_atomic(
        evidence, run_dir / "spec-008-analyst-evidence.json"
    )
    evidence_doc = evidence.model_dump(mode="json")
    evidence_sha = sha256_file(artifact_paths["evidence"])

    candidates, call_records, model_state = analyst_candidates(
        evidence, run_model_stage=run_model_stage
    )
    if call_records:
        artifact_paths["model_calls"] = write_jsonl_atomic(
            call_records, run_dir / "spec-008-model-calls.jsonl"
        )
    events.append(
        {"seq": len(events), "stage": "analyst", "state": model_state}
    )

    ranked = rank_candidates(
        candidates, evidence_doc, evidence_manifest={"analyst_evidence_sha256": evidence_sha}
    )
    calibration = evaluate_claims(
        feature_set.partition_features, ranked, evidence_doc
    )
    language_hits = lint_calibration_language(calibration)
    if language_hits:
        raise ValueError(
            f"calibration language lint failed: {language_hits}"
        )
    artifact_paths["calibration"] = write_json_atomic(
        calibration, run_dir / "spec-012-calibration.json"
    )
    ranked = apply_calibration_labels(
        ranked, calibration, sha256_file(artifact_paths["calibration"])
    )
    artifact_paths["ranked"] = write_jsonl_atomic(
        [e.model_dump(mode="json") for e in ranked.ranked],
        run_dir / "spec-009-ranked-hypotheses.jsonl"
    )
    artifact_paths["ranked_doc"] = write_json_atomic(
        ranked, run_dir / "spec-009-ranked-hypotheses.json"
    )
    events.append(
        {"seq": len(events), "stage": "interpretation", "state": ranked.state}
    )

    stage_hashes.update(
        {name: sha256_file(path) for name, path in artifact_paths.items()}
    )
    evidence_manifest_sha = hashlib.sha256(
        json.dumps(stage_hashes, sort_keys=True).encode()
    ).hexdigest()

    write_run_manifest(
        run_dir,
        run_id=run_id,
        inputs=inputs,
        artifact_paths=artifact_paths,
        gate_state=gate.state.value,
        model_stage=model_state,
        evidence_manifest_sha256=evidence_manifest_sha,
    )

    report = build_report(run_dir)
    report = report.model_copy(update={"manifest_sha256": evidence_manifest_sha})
    artifact_paths["report_json"] = write_json_atomic(
        report, run_dir / "spec-010-report.json"
    )
    report_md = render_markdown(report)
    md_path = run_dir / "spec-010-report.md"
    md_path.write_text(report_md, encoding="utf-8")
    artifact_paths["report_md"] = md_path

    events.append({"seq": len(events), "stage": "report", "state": "ok"})
    artifact_paths["events"] = run_dir / "events.jsonl"
    write_jsonl_atomic(events, artifact_paths["events"])

    write_run_manifest(
        run_dir,
        run_id=run_id,
        inputs=inputs,
        artifact_paths=artifact_paths,
        gate_state=gate.state.value,
        model_stage=model_state,
        evidence_manifest_sha256=evidence_manifest_sha,
    )
    return run_dir, gate.state.value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the full Rosetta Coda pipeline into artifacts/runs/."
    )
    parser.add_argument("--dominica", type=Path, default=DEFAULT_DOMINICA)
    parser.add_argument("--codamd", type=Path, default=DEFAULT_CODAMD)
    parser.add_argument("--artifacts-root", type=Path, default=Path("artifacts/runs"))
    parser.add_argument(
        "--no-model",
        action="store_true",
        help="Skip the LLM candidate stage even if an API key is set",
    )
    args = parser.parse_args()
    run_dir, gate_state = run_pipeline(
        args.dominica,
        args.codamd,
        args.artifacts_root,
        run_model_stage=not args.no_model,
    )
    print(f"{gate_state} {run_dir}")
    return 0 if gate_state == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
