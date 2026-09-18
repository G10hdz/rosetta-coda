from __future__ import annotations

import json

import pytest

from reporting.report import (
    CANNOT_CONCLUDE,
    MANDATORY_LIMITATIONS,
    build_report,
    lint_report_text,
    render_markdown,
)


def make_run_dir(tmp_path, **overrides) -> str:
    run = tmp_path / "run-test"
    run.mkdir()
    (run / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run-test",
                "inputs": {"DominicaCodas.csv": "a" * 64, "codamd.csv": "b" * 64},
                "manifest_sha256": "c" * 64,
            }
        )
    )
    (run / "spec-004-duration-gate.json").write_text(
        json.dumps(
            {
                "state": "pass",
                "summary": "gate passed",
                "codamd_hash": "b" * 64,
                "cohort_flow": {"n_a": 338, "n_i": 290},
                "mixed_model": {
                    "coefficient_label": "vowel_code",
                    "coefficient_value": -0.13,
                    "t_value": -6.6,
                    "p_value": 1e-11,
                    "n_obs": 628,
                },
                "per_whale_effects": [],
            }
        )
    )
    if overrides.get("features", True):
        (run / "spec-007-featureset.json").write_text(
            json.dumps(
                {
                    "n_features": 8714,
                    "n_gate_partition": 627,
                    "code_version": "phonology-features-v1",
                    "partition_contrasts": [
                        {
                            "feature": "mean_ici_s",
                            "a_minus_i": 0.034,
                            "ci95_low": 0.02,
                            "ci95_high": 0.04,
                            "n_whales": 4,
                        }
                    ],
                }
            )
        )
    if overrides.get("ranked"):
        (run / "spec-009-ranked-hypotheses.json").write_text(
            json.dumps(
                {
                    "state": "ok",
                    "selection_rule_version": "rank-v1",
                    "ranked": [
                        {
                            "rank": 1,
                            "score": 0.8,
                            "uncertainty": {"kind": "epistemic", "label": "heuristic"},
                            "hypothesis": {
                                "title": "uniform stretch",
                                "claim": "a-codas stretch all intervals",
                                "evidence_refs": ["/partition_contrasts/0"],
                                "alternatives": ["tempo confound"],
                                "falsifiers": ["held-out effect <= 0"],
                                "limitations": ["4 whales"],
                            },
                        }
                    ],
                }
            )
        )
    return str(run)


class TestBuildReport:
    def test_mandatory_sections_and_limitations(self, tmp_path):
        report = build_report(make_run_dir(tmp_path))
        assert set(report.sections) >= {
            "inputs", "gate", "features", "hypotheses", "calibration", "reproduction"
        }
        assert report.limitations == MANDATORY_LIMITATIONS
        assert report.cannot_conclude == CANNOT_CONCLUDE
        assert report.sections["gate"]["state"] == "pass"
        assert report.sections["hypotheses"]["state"] == "not_generated"
        assert report.manifest_sha256 == "c" * 64

    def test_missing_artifacts_become_states(self, tmp_path):
        report = build_report(make_run_dir(tmp_path, features=False))
        assert report.sections["features"]["state"] == "not_observable"

    def test_ranked_and_calibration_sections(self, tmp_path):
        report = build_report(make_run_dir(tmp_path, ranked=True))
        assert report.sections["hypotheses"]["ranked"][0]["hypothesis"]["title"] == (
            "uniform stretch"
        )
        assert report.citations["selection_rule"] == "rank-v1"

    def test_empty_limitations_would_fail(self):
        from contracts.models import ReportContract

        with pytest.raises(Exception):
            ReportContract(run_id="x", limitations=[], cannot_conclude=[])


class TestMarkdown:
    def test_render_contains_key_values(self, tmp_path):
        report = build_report(make_run_dir(tmp_path, ranked=True))
        md = render_markdown(report)
        assert "## Reproduction gate" in md
        assert "-0.13" in md
        assert "mean_ici_s" in md
        assert "uniform stretch" in md
        assert "## Limitations" in md
        assert "## Cannot conclude" in md
        assert "DominicaCodas.csv" in md
        assert lint_report_text(md) == []

    def test_lint_catches_semantic_language(self):
        assert lint_report_text("the whale says hello") != []
        assert lint_report_text("coda translates to food") != []
        assert lint_report_text("timing structure differs") == []
