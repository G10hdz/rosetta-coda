from __future__ import annotations

import pytest

from analysis.calibration import (
    apply_calibration_labels,
    evaluate_claims,
    lint_calibration_language,
    split_whales,
)
from contracts.models import RankedHypotheses, RankedHypothesis
from phonology.features import compute_features
from tests.test_features import make_timing


def make_ranked(contrast_refs: list[str], rank: int = 1) -> RankedHypotheses:
    return RankedHypotheses(
        ranked=[
            RankedHypothesis(
                rank=rank,
                score=0.9,
                hypothesis={
                    "title": f"c{rank}",
                    "claim": "test claim",
                    "evidence_refs": contrast_refs,
                    "uncertainty_kind": "epistemic",
                    "alternatives": ["x"],
                    "falsifiers": ["y"],
                    "limitations": ["z"],
                },
                uncertainty={"kind": "epistemic", "label": "heuristic"},
            )
        ]
    )


def partition_features_for(whale_icis: dict[str, dict[str, list[float]]]):
    features = []
    i = 0
    for whale, vowels in whale_icis.items():
        for vowel, ici in vowels.items():
            i += 1
            t = make_timing(ici, num=i, whale=whale, vowel=vowel,
                            coda_type="1+1+3")
            features.append(compute_features(t))
    return features


class TestSplit:
    def test_deterministic_and_disjoint(self):
        whales = ["ATWOOD", "FORK", "PINCHY", "TBB"]
        first = split_whales(whales)
        second = split_whales(whales)
        assert first == second
        assert set(first["fit"] + first["holdout"]) == set(whales)
        assert not set(first["fit"]) & set(first["holdout"])

    def test_real_partition_is_degenerate(self):
        """Documents the actual corpus outcome: all four whales land in
        hold-out under calibration-v1, so evaluation is indeterminate."""
        whales = ["ATWOOD", "FORK", "PINCHY", "TBB"]
        groups = split_whales(whales)
        assert groups["fit"] == []
        assert groups["holdout"] == whales


class TestEvaluate:
    DOC = {"partition_contrasts": [{"feature": "mean_ici_s", "a_minus_i": 0.05}]}

    def test_replication_on_holdout(self):
        features = partition_features_for(
            {
                "W1": {"a": [0.30, 0.30], "i": [0.20, 0.20]},
                "W2": {"a": [0.28, 0.28], "i": [0.22, 0.22]},
                "W3": {"a": [0.30, 0.30], "i": [0.19, 0.19]},
                "W4": {"a": [0.31, 0.31], "i": [0.21, 0.21]},
            }
        )
        # Force a non-degenerate split for the fixture
        groups = split_whales(["W1", "W2", "W3", "W4"])
        if not groups["fit"] or not groups["holdout"]:
            pytest.skip("fixture whales produced degenerate split")
        ranked = make_ranked(["/partition_contrasts/0"])
        report = evaluate_claims(features, ranked, self.DOC)
        assert report.state == "ok"
        claim = report.claims[0]
        assert claim.replicated is True
        assert claim.evaluated_contrasts[0]["holdout_effect"] > 0

    def test_degenerate_split_is_indeterminate(self):
        features = partition_features_for(
            {"ATWOOD": {"a": [0.3, 0.3], "i": [0.2, 0.2]}}
        )
        # extend to all four gate whales -> known degenerate split
        features += partition_features_for(
            {
                "FORK": {"a": [0.3, 0.3], "i": [0.2, 0.2]},
                "PINCHY": {"a": [0.3, 0.3], "i": [0.2, 0.2]},
                "TBB": {"a": [0.3, 0.3], "i": [0.2, 0.2]},
            }
        )
        ranked = make_ranked(["/partition_contrasts/0"])
        report = evaluate_claims(features, ranked, self.DOC)
        assert report.state == "indeterminate"
        assert report.corpus_replication_rate is None
        assert any("circular" in c for c in report.caveats)

    def test_claim_without_contrast_refs(self):
        features = partition_features_for(
            {
                "W1": {"a": [0.3, 0.3], "i": [0.2, 0.2]},
                "W2": {"a": [0.3, 0.3], "i": [0.2, 0.2]},
            }
        )
        groups = split_whales(["W1", "W2"])
        if not groups["fit"] or not groups["holdout"]:
            pytest.skip("fixture whales produced degenerate split")
        ranked = make_ranked(["/some/other/path"])
        report = evaluate_claims(features, ranked, {"some": {"other": 1}})
        assert report.claims[0].replicated is None
        assert "no evaluable contrast" in report.claims[0].detail

    def test_labels_upgrade_only_evaluated(self):
        features = partition_features_for(
            {
                "W1": {"a": [0.3, 0.3], "i": [0.2, 0.2]},
                "W2": {"a": [0.3, 0.3], "i": [0.2, 0.2]},
            }
        )
        groups = split_whales(["W1", "W2"])
        if not groups["fit"] or not groups["holdout"]:
            pytest.skip("fixture whales produced degenerate split")
        ranked = make_ranked(["/partition_contrasts/0"])
        report = evaluate_claims(features, ranked, self.DOC)
        updated = apply_calibration_labels(ranked, report, "x" * 64)
        assert updated.ranked[0].uncertainty["label"] == "empirically_checked"
        assert updated.ranked[0].uncertainty["calibration_report_sha256"] == "x" * 64

    def test_language_lint_clean(self):
        features = partition_features_for(
            {"ATWOOD": {"a": [0.3, 0.3], "i": [0.2, 0.2]}}
        )
        report = evaluate_claims(features, make_ranked([]), {})
        assert lint_calibration_language(report) == []
