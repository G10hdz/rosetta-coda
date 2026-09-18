from __future__ import annotations

import statistics
from collections import defaultdict

import numpy as np

from contracts.models import (
    CodaTiming,
    ExtractionResult,
    FeatureContrast,
    FeatureSet,
    NormalizationResult,
    PhonologyFeature,
    WhaleFeatureMean,
)

FEATURE_VERSION = "phonology-features-v1"
BOOTSTRAP_SEED = 20260713
BOOTSTRAP_ITERATIONS = 10_000
GATE_CODA_TYPE = "1+1+3"
GATE_WHALES = frozenset({"ATWOOD", "FORK", "PINCHY", "TBB"})
AGGREGATE_FEATURES = (
    "click_rate_hz",
    "mean_ici_s",
    "ici_cv",
    "npvi",
    "initial_ici_ratio",
    "terminal_ici_ratio",
    "rubato_slope",
    "drift_s",
)


def compute_features(t: CodaTiming, duration_z: float | None = None) -> PhonologyFeature:
    icis = t.icis_s
    n = len(icis)
    duration = t.duration_s_reported

    mean_ici = sum(icis) / n if n else None
    click_rate = t.click_count / duration if duration > 0 else None
    ici_cv = (
        statistics.stdev(icis) / mean_ici if n >= 2 and mean_ici else None
    )
    npvi = (
        100.0
        * sum(
            abs(a - b) / ((a + b) / 2)
            for a, b in zip(icis, icis[1:])
        )
        / (n - 1)
        if n >= 3
        else None
    )
    ici_pattern = [x / mean_ici for x in icis] if n and mean_ici else None
    initial_ratio = (
        icis[0] / (sum(icis[1:]) / (n - 1)) if n >= 2 else None
    )
    terminal_ratio = (
        icis[-1] / (sum(icis[:-1]) / (n - 1)) if n >= 2 else None
    )
    rubato_slope = None
    if n >= 3 and mean_ici:
        slope = float(np.polyfit(np.arange(n, dtype=float), np.asarray(icis), 1)[0])
        rubato_slope = slope / mean_ici
    drift = icis[-1] - icis[0] if n >= 2 else None

    return PhonologyFeature(
        coda_id=t.coda_id,
        source=t.source,
        source_ref=t.source_ref,
        click_count=t.click_count,
        click_rate_hz=click_rate,
        mean_ici_s=mean_ici,
        ici_cv=ici_cv,
        npvi=npvi,
        ici_pattern=ici_pattern,
        initial_ici_ratio=initial_ratio,
        terminal_ici_ratio=terminal_ratio,
        rubato_slope=rubato_slope,
        drift_s=drift,
        duration_z=duration_z,
        whale_id_raw=t.whale_id_raw,
        identity_status=t.identity_status,
        coda_type=t.coda_type,
        vowel=t.vowel,
    )


def gate_members(gate_partition: list[CodaTiming]) -> list[CodaTiming]:
    return [
        t
        for t in gate_partition
        if t.coda_type == GATE_CODA_TYPE
        and t.vowel in ("a", "i")
        and t.whale_id_raw in GATE_WHALES
    ]


def _mean_or_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def whale_feature_means(features: list[PhonologyFeature]) -> list[WhaleFeatureMean]:
    groups: dict[tuple[str, str | None], list[PhonologyFeature]] = defaultdict(list)
    for f in features:
        groups[(f.whale_id_raw, f.vowel)].append(f)
    means: list[WhaleFeatureMean] = []
    for (whale, vowel), members in sorted(groups.items()):
        means.append(
            WhaleFeatureMean(
                whale_id_raw=whale,
                vowel=vowel,
                n=len(members),
                means={
                    name: _mean_or_none([getattr(f, name) for f in members])
                    for name in AGGREGATE_FEATURES
                },
            )
        )
    return means


def _whale_diffs(
    features: list[PhonologyFeature], feature: str
) -> dict[str, float]:
    """Within-whale a-minus-i difference for one feature."""
    by_whale: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for f in features:
        value = getattr(f, feature)
        if value is not None and f.vowel in ("a", "i"):
            by_whale[f.whale_id_raw][f.vowel].append(value)
    diffs: dict[str, float] = {}
    for whale, vowel_values in by_whale.items():
        if vowel_values.get("a") and vowel_values.get("i"):
            diffs[whale] = (
                sum(vowel_values["a"]) / len(vowel_values["a"])
                - sum(vowel_values["i"]) / len(vowel_values["i"])
            )
    return diffs


def partition_contrasts(
    features: list[PhonologyFeature],
    seed: int = BOOTSTRAP_SEED,
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> list[FeatureContrast]:
    rng = np.random.default_rng(seed)
    contrasts: list[FeatureContrast] = []
    for feature in AGGREGATE_FEATURES:
        diffs = _whale_diffs(features, feature)
        if not diffs:
            continue
        values = np.asarray(list(diffs.values()))
        contrast = float(values.mean())
        n = len(values)
        resampled = rng.choice(values, size=(iterations, n), replace=True).mean(axis=1)
        lo, hi = np.percentile(resampled, [2.5, 97.5])
        contrasts.append(
            FeatureContrast(
                feature=feature,
                n_whales=n,
                a_minus_i=contrast,
                ci95_low=float(lo),
                ci95_high=float(hi),
            )
        )
    return contrasts


def build_feature_set(
    extraction: ExtractionResult,
    normalization: NormalizationResult | None = None,
) -> tuple[list[PhonologyFeature], FeatureSet]:
    z_by_coda: dict[str, float | None] = {}
    if normalization is not None:
        z_by_coda = {
            n.coda_id: n.duration_z for n in normalization.normalized
        }

    features = [
        compute_features(t, duration_z=z_by_coda.get(t.coda_id))
        for t in extraction.timings
    ]
    gate_timings = gate_members(extraction.gate_partition)
    gate_z = {t.coda_id: z_by_coda.get(t.coda_id) for t in gate_timings}
    partition_features = [
        compute_features(t, duration_z=gate_z[t.coda_id]) for t in gate_timings
    ]

    feature_set = FeatureSet(
        input_hashes=dict(extraction.input_hashes),
        n_features=len(features),
        n_gate_partition=len(partition_features),
        partition_features=partition_features,
        partition_contrasts=partition_contrasts(partition_features),
        whale_feature_means=whale_feature_means(partition_features),
        details={
            "aggregate_features": list(AGGREGATE_FEATURES),
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "gate_filter": {
                "coda_type": GATE_CODA_TYPE,
                "whales": sorted(GATE_WHALES),
            },
        },
    )
    return features, feature_set


__all__ = [
    "build_feature_set",
    "compute_features",
    "gate_members",
    "partition_contrasts",
    "whale_feature_means",
]
