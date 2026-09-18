from __future__ import annotations

import pytest

from interpretation.hypotheses import HypothesisCandidate
from interpretation.ranking import (
    SELECTION_RULE_VERSION,
    rank_candidates,
    score_candidate,
)

DOC = {
    "gate": {"mixed_model": {"coefficient_value": -0.13, "p_value": 0.01}},
    "contrasts": [{"feature": "mean_ici_s", "a_minus_i": 0.05}],
    "label": "evidence",
}


def make_candidate(
    claim: str,
    refs: list[str],
    falsifiers: list[str],
    alternatives: list[str] | None = None,
    kind: str = "epistemic",
    title: str = "t",
) -> HypothesisCandidate:
    return HypothesisCandidate(
        title=title,
        claim=claim,
        evidence_refs=refs,
        uncertainty_kind=kind,
        alternatives=alternatives or ["individual timing variation"],
        falsifiers=falsifiers,
        limitations=["small resolved sample"],
    )


class TestScoring:
    def test_fully_grounded_candidate_scores_high(self):
        c = make_candidate(
            "a-codas stretch every interval",
            refs=["/gate/mixed_model/coefficient_value", "/gate/mixed_model/p_value"],
            falsifiers=["effect disappears in held-out whales with |a-i| < 0.01 s"],
            alternatives=["vocal effort", "recording noise", "bout position", "click fusion"],
        )
        score, components, reasons = score_candidate(c, DOC)
        assert components["evidence_grounding"] == pytest.approx(0.4)
        assert components["falsifier_specificity"] == pytest.approx(1.0)
        assert components["alternative_coverage"] == pytest.approx(1.0)
        assert components["uncertainty_honesty"] == pytest.approx(1.0)
        assert score == pytest.approx(0.4 * 0.4 + 0.25 + 0.20 + 0.15)
        assert any("2/2" in r for r in reasons)

    def test_unresolvable_refs_ground_nothing(self):
        c = make_candidate(
            "claim",
            refs=["/gate/mixed_model/coefficient_value", "/missing/path"],
            falsifiers=["some falsifier"],
        )
        _, components, _ = score_candidate(c, DOC)
        # 1/2 refs numeric, only 1 resolvable -> 0.5 * min(1,5)/5 = 0.1
        assert components["evidence_grounding"] == pytest.approx(0.1)

    def test_weights_sum_to_one(self):
        from interpretation.ranking import _WEIGHTS

        assert sum(_WEIGHTS.values()) == pytest.approx(1.0)


class TestRanking:
    def test_order_and_determinism(self):
        strong = make_candidate(
            "strong claim",
            refs=["/gate/mixed_model/coefficient_value"],
            falsifiers=["held-out whales |a-i| <= 0"],
            alternatives=["a", "b", "c"],
        )
        weak = make_candidate(
            "weak claim",
            refs=["/label"],
            falsifiers=["maybe it stops"],
            kind="sampling",
        )
        first = rank_candidates([weak, strong], DOC)
        second = rank_candidates([strong, weak], DOC)
        assert [r.model_dump() for r in first.ranked] == [
            r.model_dump() for r in second.ranked
        ]
        assert first.ranked[0].hypothesis["claim"] == "strong claim"
        assert first.ranked[0].rank == 1
        assert first.ranked[1].rank == 2
        assert first.selection_rule_version == SELECTION_RULE_VERSION

    def test_uncertainty_labels(self):
        c = make_candidate("claim", ["/label"], ["x"], kind="epistemic")
        result = rank_candidates([c], DOC)
        assert result.ranked[0].uncertainty == {
            "kind": "epistemic",
            "label": "heuristic",
        }

    def test_empty_candidates_indeterminate(self):
        result = rank_candidates([], DOC)
        assert result.state == "indeterminate"
        assert result.ranked == []

    def test_tie_break_by_first_ref_then_claim(self):
        a = make_candidate("a claim", ["/gate/mixed_model/p_value"], ["held-out < 0"])
        b = make_candidate("b claim", ["/gate/mixed_model/coefficient_value"], ["held-out < 0"])
        result = rank_candidates([a, b], DOC)
        # equal scores; coefficient_value sorts before p_value lexically
        assert result.ranked[0].hypothesis["claim"] == "b claim"
