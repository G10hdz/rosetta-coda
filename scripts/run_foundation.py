from __future__ import annotations

import argparse
from pathlib import Path

from analysis.normalize import normalize_durations
from analysis.reproduce_duration import run_duration_gate
from data.loader import load_dominica_codas
from storage.io import sha256_file, write_json_atomic

DEFAULT_DOMINICA = Path("external/sw-combinatoriality/data/DominicaCodas.csv")
DEFAULT_CODAMD = Path("external/phonology-osf-9t6qu/codamd.csv")


def run_foundation(
    dominica_path: Path = DEFAULT_DOMINICA,
    codamd_path: Path = DEFAULT_CODAMD,
    artifacts_root: Path = Path("artifacts/runs"),
) -> tuple[Path, str]:
    loaded = load_dominica_codas(str(dominica_path), qc_mode="permissive")
    normalized = normalize_durations(
        loaded.records,
        partition_id="dominica-all-valid-v1",
        input_hash=loaded.dataset_hash,
    )
    gate = run_duration_gate(str(codamd_path))
    run_id = f"foundation-{loaded.dataset_hash[:12]}-{gate.codamd_hash[:12]}"
    run_dir = artifacts_root / run_id

    artifact_paths = {
        "load": write_json_atomic(loaded, run_dir / "spec-002-load.json"),
        "normalization": write_json_atomic(
            normalized, run_dir / "spec-003-normalization.json"
        ),
        "gate": write_json_atomic(gate, run_dir / "spec-004-duration-gate.json"),
    }
    manifest = {
        "run_id": run_id,
        "schema_version": "0.1.0",
        "inputs": {
            str(dominica_path): loaded.dataset_hash,
            str(codamd_path): gate.codamd_hash,
        },
        "artifacts": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in artifact_paths.items()
        },
        "gate_state": gate.state.value,
    }
    write_json_atomic(manifest, run_dir / "manifest.json")
    return run_dir, gate.state.value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dominica", type=Path, default=DEFAULT_DOMINICA)
    parser.add_argument("--codamd", type=Path, default=DEFAULT_CODAMD)
    parser.add_argument("--artifacts-root", type=Path, default=Path("artifacts/runs"))
    args = parser.parse_args()
    run_dir, gate_state = run_foundation(
        args.dominica, args.codamd, args.artifacts_root
    )
    print(f"{gate_state} {run_dir}")
    return 0 if gate_state == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
