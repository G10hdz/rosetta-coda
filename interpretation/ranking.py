from __future__ import annotations

import re
from typing import Any

from contracts.models import RankedHypotheses, RankedHypothesis
from interpretation.hypotheses import (
    HypothesisCandidate,
    UncertaintyKind,
    _resolve_json_pointer,
)

SELECTION_RULE_VERSION = "rank-v1"

_WEIGHTS = {
    "evidence_grounding": 0.40,
    "falsifier_specificity": 0.25,
    "alternative_coverage": 0.20,
    "uncertainty_honesty": 0.15,
}

_MEASURABLE_PATTERNS = (
    r"[<>≥≤=]",
    r"\b\d+(?:\.\d+)?\s*(?:s|ms|hz|%|seconds?|codas|whales)\b",
    r"\b(?:threshold|held[\s-]?out|holdout|bootstrap|mixed[\s-]?model|"
    r"p[\s-]?value|confidence|ci95|replicat\w+|effect[\s-]?size|coefficient|"
    r"subset|cohort|partition|within[\s-]?whale)\b",
)

_UNCERTAINTY_HONESTY = {
    UncertaintyKind.epistemic: 1.0,
    UncertaintyKind.model: 1.0,
    UncertaintyKind.measurement: 0.75,
    UncertaintyKind.sampling: 0.5,
}


def _ref_is_numeric(document: dict[str, Any], pointer: str) -> bool | None:
    """True -> numeric, False -> resolves but non-numeric, None -> unresolvable."""
    try:
        value = _resolve_json_pointer(document, pointer)
    except (IndexError, KeyError, TypeError, ValueError):
        return None
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _falsifier_measurable(falsifier: str) -> bool:
    return any(
        re.search(pattern, falsifier, flags=re.IGNORECASE)
        for pattern in _MEASURABLE_PATTERNS
    )


def score_candidate(
    candidate: HypothesisCandidate,
    document: dict[str, Any],
) -> tuple[float, dict[str, float], list[str]]:
    refs = candidate.evidence_refs
    numeric = [r for r in refs if _ref_is_numeric(document, r) is True]
    resolvable = [r for r in refs if _ref_is_numeric(document, r) is not None]
    n = len(refs)
    evidence_grounding = (len(numeric) / n) * min(len(resolvable), 5) / 5

    measurable = [f for f in candidate.falsifiers if _falsifier_measurable(f)]
    falsifier_specificity = len(measurable) / len(candidate.falsifiers)

    alternative_coverage = min(len(candidate.alternatives), 4) / 4
    uncertainty_honesty = _UNCERTAINTY_HONESTY.get(candidate.uncertainty_kind, 0.5)

    components = {
        "evidence_grounding": evidence_grounding,
        "falsifier_specificity": falsifier_specificity,
        "alternative_coverage": alternative_coverage,
        "uncertainty_honesty": uncertainty_honesty,
    }
    score = sum(_WEIGHTS[name] * value for name, value in components.items())
    reasons = [
        f"{len(numeric)}/{n} evidence refs resolve to numerics",
        f"{len(measurable)}/{len(candidate.falsifiers)} falsifiers carry measurable conditions",
        f"{len(candidate.alternatives)} alternatives",
        f"uncertainty kind '{candidate.uncertainty_kind.value}'",
    ]
    return score, components, reasons


def rank_candidates(
    candidates: list[HypothesisCandidate],
    document: dict[str, Any],
    *,
    evidence_manifest: dict[str, str] | None = None,
) -> RankedHypotheses:
    if not candidates:
        return RankedHypotheses(
            evidence_manifest=evidence_manifest or {},
            state="indeterminate",
            ranked=[],
        )

    scored = []
    for candidate in candidates:
        score, components, reasons = score_candidate(candidate, document)
        scored.append((score, components, reasons, candidate))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[3].evidence_refs[0],
            item[3].claim,
        )
    )
    ranked = [
        RankedHypothesis(
            rank=index + 1,
            score=round(score, 6),
            score_components={k: round(v, 6) for k, v in components.items()},
            reasons=reasons,
            hypothesis=candidate.model_dump(mode="json"),
            uncertainty={
                "kind": candidate.uncertainty_kind.value,
                "label": "heuristic",
            },
        )
        for index, (score, components, reasons, candidate) in enumerate(scored)
    ]
    return RankedHypotheses(
        evidence_manifest=evidence_manifest or {},
        state="ok",
        ranked=ranked,
    )


__all__ = ["rank_candidates", "score_candidate", "SELECTION_RULE_VERSION"]
