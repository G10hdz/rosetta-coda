from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

from contracts.models import (
    CalibrationReport,
    ClaimCalibration,
    PhonologyFeature,
    RankedHypotheses,
)
from interpretation.hypotheses import _resolve_json_pointer

CALIBRATION_VERSION = "calibration-v1"
SPLIT_SEED = "calibration-v1"

_FORBIDDEN_LANGUAGE = (
    r"p\s*<\s*0",
    r"\bsignificant\b",
    r"\bprobability of (?:truth|being true)\b",
    r"\b\d+%\s+confiden\w+",
)


def split_whales(
    whale_ids: list[str], seed: str = SPLIT_SEED
) -> dict[str, list[str]]:
    """Deterministic grouped split: sha256(whale_id + seed) as int mod 2.

    Concatenation is `whale_id + seed` with no separator, matching SPEC-012.
    """
    groups: dict[str, list[str]] = {"fit": [], "holdout": []}
    for whale in sorted(set(whale_ids)):
        digest = hashlib.sha256(f"{whale}{seed}".encode()).digest()
        assigned = int.from_bytes(digest, "big") % 2
        groups["fit" if assigned == 0 else "holdout"].append(whale)
    return groups


def _whale_diffs_on(
    features: list[PhonologyFeature], feature: str, whales: set[str]
) -> dict[str, float]:
    by_whale: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for f in features:
        if f.whale_id_raw in whales and f.vowel in ("a", "i"):
            value = getattr(f, feature, None)
            if value is not None:
                by_whale[f.whale_id_raw][f.vowel].append(value)
    diffs: dict[str, float] = {}
    for whale, vowel_values in by_whale.items():
        if vowel_values.get("a") and vowel_values.get("i"):
            diffs[whale] = (
                sum(vowel_values["a"]) / len(vowel_values["a"])
                - sum(vowel_values["i"]) / len(vowel_values["i"])
            )
    return diffs


def _claim_contrast_refs(
    hypothesis: dict[str, Any], document: dict[str, Any]
) -> list[dict[str, Any]]:
    """Resolve evidence refs; keep those pointing at contrast objects."""
    contrasts: list[dict[str, Any]] = []
    for ref in hypothesis.get("evidence_refs", []):
        try:
            value = _resolve_json_pointer(document, ref)
        except (IndexError, KeyError, TypeError, ValueError):
            continue
        if isinstance(value, dict) and "feature" in value and "a_minus_i" in value:
            contrasts.append(value)
        elif isinstance(value, list):
            contrasts.extend(
                item
                for item in value
                if isinstance(item, dict)
                and "feature" in item
                and "a_minus_i" in item
            )
    return contrasts


def evaluate_claims(
    partition_features: list[PhonologyFeature],
    ranked: RankedHypotheses,
    evidence_document: dict[str, Any],
    *,
    seed: str = SPLIT_SEED,
) -> CalibrationReport:
    whales = sorted({f.whale_id_raw for f in partition_features})
    groups = split_whales(whales, seed)
    holdout = set(groups["holdout"])

    caveats: list[str] = []
    if len(whales) <= 4:
        caveats.append(
            f"{len(whales)} resolved whales; split is illustrative, not a "
            "powered evaluation"
        )
    if not holdout or not groups["fit"]:
        return CalibrationReport(
            groups=groups,
            state="indeterminate",
            caveats=caveats
            + [
                "degenerate split (empty fit or hold-out group); evaluating "
                "claims on the same whales they were derived from would be "
                "circular, so no held-out evaluation is reported"
            ],
        )

    claims: list[ClaimCalibration] = []
    for entry in ranked.ranked:
        hypothesis = entry.hypothesis
        refs = _claim_contrast_refs(hypothesis, evidence_document)
        if not refs:
            claims.append(
                ClaimCalibration(
                    claim_ref=f"hypotheses.jsonl#rank-{entry.rank}",
                    claim_title=str(hypothesis.get("title", "")),
                    replicated=None,
                    detail="no evaluable contrast reference in evidence_refs",
                )
            )
            continue

        evaluated: list[dict[str, Any]] = []
        for contrast in refs:
            feature = contrast["feature"]
            expected_sign = 1 if float(contrast["a_minus_i"]) > 0 else -1
            diffs = _whale_diffs_on(partition_features, feature, holdout)
            if not diffs:
                evaluated.append(
                    {
                        "feature": feature,
                        "direction": "a_minus_i_positive"
                        if expected_sign > 0
                        else "a_minus_i_negative",
                        "holdout_effect": None,
                        "replicated": None,
                        "n_whales": 0,
                        "detail": "no hold-out whale has both vowels",
                    }
                )
                continue
            effect = sum(diffs.values()) / len(diffs)
            replicated = (effect > 0) == (expected_sign > 0) and effect != 0
            evaluated.append(
                {
                    "feature": feature,
                    "direction": "a_minus_i_positive"
                    if expected_sign > 0
                    else "a_minus_i_negative",
                    "holdout_effect": effect,
                    "replicated": replicated,
                    "n_whales": len(diffs),
                }
            )

        decided = [e["replicated"] for e in evaluated if e["replicated"] is not None]
        claims.append(
            ClaimCalibration(
                claim_ref=f"hypotheses.jsonl#rank-{entry.rank}",
                claim_title=str(hypothesis.get("title", "")),
                evaluated_contrasts=evaluated,
                replicated=bool(decided) and all(decided),
                detail=f"{len(evaluated)} contrast(s) evaluated on hold-out",
            )
        )

    decided_claims = [c.replicated for c in claims if c.replicated is not None]
    rate = (
        sum(1 for r in decided_claims if r) / len(decided_claims)
        if decided_claims
        else None
    )
    return CalibrationReport(
        groups=groups,
        claims=claims,
        corpus_replication_rate=rate,
        state="ok",
        caveats=caveats,
    )


def lint_calibration_language(report: CalibrationReport) -> list[str]:
    """Return forbidden-language hits in the serialized report (must be empty)."""
    text = json.dumps(report.model_dump(mode="json"), sort_keys=True)
    hits = [
        pattern
        for pattern in _FORBIDDEN_LANGUAGE
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    return hits


def apply_calibration_labels(
    ranked: RankedHypotheses,
    report: CalibrationReport,
    report_sha256: str,
) -> RankedHypotheses:
    """Upgrade evaluated claims to empirically_checked with the report hash."""
    if report.state != "ok":
        return ranked
    evaluated_refs = {
        claim.claim_ref for claim in report.claims if claim.replicated is not None
    }
    for entry in ranked.ranked:
        if f"hypotheses.jsonl#rank-{entry.rank}" in evaluated_refs:
            entry.uncertainty = {
                **entry.uncertainty,
                "label": "empirically_checked",
                "calibration_report_sha256": report_sha256,
            }
    return ranked


__all__ = [
    "CALIBRATION_VERSION",
    "SPLIT_SEED",
    "apply_calibration_labels",
    "evaluate_claims",
    "lint_calibration_language",
    "split_whales",
]
