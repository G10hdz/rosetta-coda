from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from contracts.models import ReportContract
from interpretation.hypotheses import _SEMANTIC_CLAIM_PATTERNS

MANDATORY_LIMITATIONS = [
    "No semantic ground truth exists; nothing in this report is a translation.",
    "Unresolved-identity codas are excluded from individual-controlled inference.",
    "Audio-dependent features are not_observable in this run (no WAV input).",
    "Confidence labels are heuristic unless an empirical calibration report exists.",
]

CANNOT_CONCLUDE = [
    "coda meaning or semantic content",
    "individual whale intent",
    "clan-level grammar or syntax",
    "anything beyond measured click-timing structure",
]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _code_revision() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def lint_report_text(text: str) -> list[str]:
    return [
        pattern
        for pattern in _SEMANTIC_CLAIM_PATTERNS
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]


def _model_id(run_dir: Path, hypothesis: dict[str, Any] | None) -> str | None:
    """Prefer the demo hypothesis artifact; fall back to model-calls.jsonl."""
    if hypothesis and hypothesis.get("model"):
        return str(hypothesis["model"])
    calls = run_dir / "spec-008-model-calls.jsonl"
    if not calls.is_file():
        return None
    for line in calls.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("model"):
            return str(record["model"])
    return None


def build_report(run_dir: str | Path) -> ReportContract:
    """Assemble the report from a run directory's immutable artifacts."""
    run_dir = Path(run_dir)
    manifest = _read_json(run_dir / "manifest.json") or {}
    load = _read_json(run_dir / "spec-002-load.json")
    gate = _read_json(run_dir / "spec-004-duration-gate.json")
    extraction = _read_json(run_dir / "spec-005-extraction.json")
    feature_set = _read_json(run_dir / "spec-007-featureset.json")
    ranked = _read_json(run_dir / "spec-009-ranked-hypotheses.json")
    calibration = _read_json(run_dir / "spec-012-calibration.json")
    hypothesis = _read_json(run_dir / "spec-008-hypothesis.json")
    model_id = _model_id(run_dir, hypothesis)

    sections: dict[str, Any] = {}

    run_id = manifest.get("run_id") or run_dir.name
    sections["inputs"] = {
        "run_id": run_id,
        "inputs": manifest.get("inputs", {}),
        "load": (
            {
                "row_count": load.get("row_count"),
                "cohort_counts": load.get("cohort_counts"),
                "dataset_hash": load.get("dataset_hash"),
            }
            if load
            else {"state": "missing"}
        ),
    }

    sections["gate"] = (
        {
            "state": gate.get("state"),
            "summary": gate.get("summary"),
            "cohort_flow": gate.get("cohort_flow"),
            "mixed_model": gate.get("mixed_model"),
            "per_whale_effects": gate.get("per_whale_effects"),
        }
        if gate
        else {"state": "missing"}
    )

    sections["features"] = (
        {
            "n_features": feature_set.get("n_features"),
            "n_gate_partition": feature_set.get("n_gate_partition"),
            "partition_contrasts": feature_set.get("partition_contrasts"),
            "code_version": feature_set.get("code_version"),
        }
        if feature_set
        else {"state": "not_observable"}
    )
    if extraction:
        sections["features"]["extraction_qc"] = extraction.get("qc")

    if ranked:
        sections["hypotheses"] = {
            "state": ranked.get("state"),
            "selection_rule_version": ranked.get("selection_rule_version"),
            "ranked": ranked.get("ranked"),
        }
    elif hypothesis:
        sections["hypotheses"] = {
            "state": "generated_unranked",
            "hypothesis": hypothesis.get("hypothesis"),
            "model": hypothesis.get("model"),
        }
    else:
        sections["hypotheses"] = {"state": "not_generated"}

    sections["calibration"] = (
        {
            "state": calibration.get("state"),
            "calibration_version": calibration.get("calibration_version"),
            "corpus_replication_rate": calibration.get("corpus_replication_rate"),
            "caveats": calibration.get("caveats"),
        }
        if calibration
        else {"state": "not_run"}
    )

    sections["reproduction"] = {
        "commands": [
            "uv sync --all-extras",
            "uv run python -m scripts.run_pipeline",
            "uv run python -m scripts.replay_release",
        ],
        "environment": "Python 3.11, uv.lock pinned",
        "manifest_sha256": manifest.get("manifest_sha256"),
    }

    limitations = list(MANDATORY_LIMITATIONS)
    if calibration and calibration.get("state") == "ok":
        limitations[3] = (
            "Confidence labels are empirically_checked where the calibration "
            "report evaluated them; the whale split is illustrative."
        )

    citations = {
        "datasets": [
            {
                "name": "DominicaCodas.csv",
                "sha256": (load or {}).get("dataset_hash"),
            },
            {
                "name": "codamd.csv (OSF 10.17605/OSF.IO/9T6QU)",
                "sha256": (gate or {}).get("codamd_hash"),
            },
        ],
        "code_revision": _code_revision(),
        "model": model_id,
        "selection_rule": (ranked or {}).get("selection_rule_version"),
        "calibration_version": (calibration or {}).get("calibration_version"),
    }

    if not limitations or not CANNOT_CONCLUDE:
        raise ValueError("report requires non-empty limitations and cannot_conclude")

    return ReportContract(
        run_id=run_id,
        sections=sections,
        citations=citations,
        limitations=limitations,
        cannot_conclude=list(CANNOT_CONCLUDE),
        manifest_sha256=manifest.get("manifest_sha256"),
    )


def render_markdown(report: ReportContract) -> str:
    s = report.sections
    lines = [
        f"# Rosetta Coda — run report `{report.run_id}`",
        "",
        "## Inputs and provenance",
    ]
    for name, sha in (s["inputs"].get("inputs") or {}).items():
        lines.append(f"- `{name}` sha256 `{sha}`")
    load = s["inputs"].get("load", {})
    if load.get("row_count"):
        lines.append(
            f"- {load['row_count']} rows loaded; cohort counts: "
            f"`{json.dumps(load['cohort_counts'], sort_keys=True)}`"
        )

    gate = s["gate"]
    lines += ["", "## Reproduction gate"]
    if gate.get("state"):
        mm = gate.get("mixed_model") or {}
        lines.append(
            f"- state: **{gate['state']}** — {gate.get('summary', '')}"
        )
        if mm:
            lines.append(
                f"- mixed model coefficient `{mm.get('coefficient_label')}` = "
                f"{mm.get('coefficient_value')} (t={mm.get('t_value')}, "
                f"p={mm.get('p_value')}, n={mm.get('n_obs')})"
            )
    else:
        lines.append("- gate artifact missing; report is a stop report")

    features = s["features"]
    lines += ["", "## Feature summary"]
    if features.get("partition_contrasts"):
        lines.append(
            f"- {features['n_features']} coda feature records; "
            f"{features['n_gate_partition']} gate-partition codas"
        )
        lines.append("")
        lines.append("| feature | a − i | CI95 |")
        lines.append("|---|---|---|")
        for c in features["partition_contrasts"]:
            lo, hi = c.get("ci95_low"), c.get("ci95_high")
            ci = f"[{lo:.4g}, {hi:.4g}]" if lo is not None and hi is not None else "—"
            lines.append(f"| {c['feature']} | {c['a_minus_i']:.4g} | {ci} |")
    else:
        lines.append("- features not_observable in this run")

    hyp = s["hypotheses"]
    lines += ["", "## Hypotheses"]
    if hyp.get("ranked"):
        for entry in hyp["ranked"]:
            h = entry["hypothesis"]
            lines += [
                "",
                f"### #{entry['rank']} {h.get('title', 'untitled')} "
                f"(score {entry['score']})",
                "",
                h.get("claim", ""),
                "",
                f"- uncertainty: {entry['uncertainty'].get('kind')} "
                f"({entry['uncertainty'].get('label')})",
                f"- evidence: {', '.join(f'`{r}`' for r in h.get('evidence_refs', []))}",
                f"- alternatives: {'; '.join(h.get('alternatives', []))}",
                f"- falsifiers: {'; '.join(h.get('falsifiers', []))}",
            ]
    else:
        lines.append(f"- {hyp.get('state')}")

    cal = s["calibration"]
    lines += ["", "## Calibration"]
    if cal.get("state") == "ok":
        lines.append(
            f"- replication rate: {cal.get('corpus_replication_rate')} "
            f"({cal.get('calibration_version')})"
        )
        for caveat in cal.get("caveats") or []:
            lines.append(f"- caveat: {caveat}")
    else:
        lines.append(f"- {cal.get('state')}")

    lines += ["", "## Limitations", ""]
    lines += [f"- {item}" for item in report.limitations]
    lines += ["", "## Cannot conclude", ""]
    lines += [f"- {item}" for item in report.cannot_conclude]

    citations = report.citations
    lines += ["", "## Citations and reproduction", ""]
    for ds in citations.get("datasets", []):
        lines.append(f"- {ds['name']} — `{ds['sha256']}`")
    if citations.get("code_revision"):
        lines.append(f"- code revision `{citations['code_revision']}`")
    if citations.get("model"):
        lines.append(f"- model `{citations['model']}`")
    for cmd in s["reproduction"]["commands"]:
        lines.append(f"- `{cmd}`")

    text = "\n".join(lines) + "\n"
    hits = lint_report_text(text)
    if hits:
        raise ValueError(f"semantic-claim lint failed on report: {hits}")
    return text


__all__ = ["build_report", "render_markdown", "lint_report_text"]
