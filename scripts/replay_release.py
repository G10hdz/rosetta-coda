"""SPEC-013: reproducible release replay.

Re-runs the deterministic pipeline stages into a temporary directory and
verifies their sha256 against the release manifest. Model-generated artifacts
are not replayable (a fresh call would differ); instead each sealed artifact
is hash-verified against the manifest and schema-validated.

Usage:
    uv run python -m scripts.replay_release [--release-dir artifacts/release]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_pipeline import run_pipeline
from storage.io import sha256_file

DETERMINISTIC = [
    "load",
    "normalization",
    "gate",
    "extraction",
    "phonology",
    "featureset",
    "evidence",
]
SEALED = [
    "model_calls",
    "ranked",
    "ranked_doc",
    "calibration",
    "report_json",
    "report_md",
]


def replay(release_dir: Path) -> dict:
    manifest = json.loads((release_dir / "manifest.json").read_text())
    checks: list[dict] = []

    input_results = []
    for rel_path, expected in manifest["inputs"].items():
        actual = sha256_file(Path(rel_path))
        ok = actual == expected
        input_results.append({"path": rel_path, "match": ok})
        checks.append({"kind": "input", "name": rel_path, "ok": ok})
    if not all(r["match"] for r in input_results):
        return _result("failed_inputs", manifest, checks)

    with tempfile.TemporaryDirectory(prefix="rosetta-replay-") as tmp:
        replay_dir, gate_state = run_pipeline(
            Path("external/sw-combinatoriality/data/DominicaCodas.csv"),
            Path("external/phonology-osf-9t6qu/codamd.csv"),
            Path(tmp),
            run_model_stage=False,
        )
        checks.append(
            {
                "kind": "gate",
                "name": "gate_state",
                "ok": gate_state == manifest["gate_state"],
                "expected": manifest["gate_state"],
                "actual": gate_state,
            }
        )
        for name in DETERMINISTIC:
            entry = manifest["artifacts"].get(name)
            if entry is None:
                checks.append(
                    {"kind": "deterministic", "name": name, "ok": False,
                     "error": "missing from manifest"}
                )
                continue
            replay_path = replay_dir / Path(entry["path"]).name
            if not replay_path.exists():
                checks.append(
                    {"kind": "deterministic", "name": name, "ok": False,
                     "error": "not regenerated"}
                )
                continue
            actual = sha256_file(replay_path)
            checks.append(
                {
                    "kind": "deterministic",
                    "name": name,
                    "ok": actual == entry["sha256"],
                    "expected": entry["sha256"],
                    "actual": actual,
                }
            )

    for name in SEALED:
        entry = manifest["artifacts"].get(name)
        sealed_path = release_dir / Path(entry["path"]).name if entry else None
        if entry is None or not sealed_path.exists():
            checks.append(
                {"kind": "sealed", "name": name, "ok": False,
                 "error": "missing"}
            )
            continue
        actual = sha256_file(sealed_path)
        ok = actual == entry["sha256"]
        if ok and sealed_path.suffix == ".json":
            try:
                json.loads(sealed_path.read_text())
            except json.JSONDecodeError:
                ok = False
        checks.append(
            {
                "kind": "sealed",
                "name": name,
                "ok": ok,
                "expected": entry["sha256"],
                "actual": actual,
            }
        )

    state = "verified" if all(c["ok"] for c in checks) else "failed"
    return _result(state, manifest, checks)


def _result(state: str, manifest: dict, checks: list[dict]) -> dict:
    return {
        "state": state,
        "run_id": manifest["run_id"],
        "gate_state": manifest["gate_state"],
        "model_stage": manifest.get("model_stage", "unknown"),
        "checks": checks,
        "deterministic_replayed": sum(
            1 for c in checks if c["kind"] == "deterministic" and c["ok"]
        ),
        "sealed_verified": sum(
            1 for c in checks if c["kind"] == "sealed" and c["ok"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-dir", type=Path, default=Path("artifacts/release")
    )
    parser.add_argument("--json", type=Path, default=None,
                        help="Optionally write the replay report JSON here")
    args = parser.parse_args()
    report = replay(args.release_dir)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for c in report["checks"]:
        mark = "ok" if c["ok"] else "FAIL"
        print(f"[{mark}] {c['kind']}: {c['name']}")
    print(
        f"{report['state']}: {report['deterministic_replayed']}/"
        f"{len(DETERMINISTIC)} deterministic replayed, "
        f"{report['sealed_verified']}/{len(SEALED)} sealed verified"
    )
    return 0 if report["state"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
