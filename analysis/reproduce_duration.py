from __future__ import annotations

import hashlib
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.regression.mixed_linear_model import MixedLM

from contracts.models import (
    GateResult,
    GateState,
    MixedModelResult,
    PerWhaleEffect,
)
from storage.io import write_json_atomic

CODAMD_EXPECTED_HASH = "e3fc6b402eeafa94a168ed215255255ed3d3acbeef2d65abe54312526b42a899"
FOUR_WHALES = ["ATWOOD", "FORK", "PINCHY", "TBB"]
CODATYPE_TARGET = "1+1+3"
PUBLISHED_I_COEFF = -0.13
PUBLISHED_TOLERANCE = 0.02


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_duration_gate(codamd_path: str) -> GateResult:
    try:
        actual_hash = _file_hash(codamd_path)
    except OSError as exc:
        return GateResult(
            state=GateState.indeterminate,
            summary=f"Cannot read codamd: {exc}",
            codamd_hash="",
            cohort_flow={},
            per_whale_effects=[],
        )
    if actual_hash != CODAMD_EXPECTED_HASH:
        return GateResult(
            state=GateState.indeterminate,
            summary=f"codamd hash mismatch: expected {CODAMD_EXPECTED_HASH}, got {actual_hash}",
            codamd_hash=actual_hash,
            cohort_flow={},
            per_whale_effects=[],
        )

    try:
        df = pd.read_csv(codamd_path)
    except Exception as exc:
        return GateResult(
            state=GateState.indeterminate,
            summary=f"Cannot parse codamd: {exc}",
            codamd_hash=actual_hash,
            cohort_flow={},
            per_whale_effects=[],
        )
    required = {"codanum", "whale", "codatype", "Duration", "handv"}
    missing = required - set(df.columns)
    if missing:
        return GateResult(
            state=GateState.indeterminate,
            summary=f"Missing codamd columns: {sorted(missing)}",
            codamd_hash=actual_hash,
            cohort_flow={},
            per_whale_effects=[],
        )
    total_input = len(df)

    # Filter: exact a or i
    df = df[df["handv"].isin(["a", "i"])].copy()
    after_handv = len(df)

    # Filter: codatype == 1+1+3
    df = df[df["codatype"] == CODATYPE_TARGET].copy()
    after_codatype = len(df)

    # Filter: four whales
    df = df[df["whale"].isin(FOUR_WHALES)].copy()
    after_whales = len(df)

    n_a = int((df["handv"] == "a").sum())
    n_i = int((df["handv"] == "i").sum())

    eligible = len(df)
    if eligible != 628:
        return GateResult(
            state=GateState.indeterminate,
            summary=f"Eligible sample {eligible} != expected 628",
            codamd_hash=actual_hash,
            cohort_flow={
                "total_input": total_input,
                "after_handv_filter": after_handv,
                "after_codatype_filter": after_codatype,
                "after_whale_filter": after_whales,
                "n_a": n_a,
                "n_i": n_i,
            },
            per_whale_effects=[],
        )

    if n_a != 338 or n_i != 290:
        return GateResult(
            state=GateState.indeterminate,
            summary=f"Vowel counts mismatch: a={n_a}, i={n_i} (expected 338, 290)",
            codamd_hash=actual_hash,
            cohort_flow={
                "total_input": total_input,
                "after_handv_filter": after_handv,
                "after_codatype_filter": after_codatype,
                "after_whale_filter": after_whales,
                "n_a": n_a,
                "n_i": n_i,
            },
            per_whale_effects=[],
        )

    df["vowel_code"] = (df["handv"] == "i").astype(float)

    # Mixed model: Duration ~ Vowel with (Vowel | whale)
    n_groups = df["whale"].nunique()

    model_warnings: list[str] = []
    try:
        model = MixedLM.from_formula(
            "Duration ~ vowel_code",
            groups=df["whale"],
            re_formula="1 + vowel_code",
            data=df,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fitted = model.fit(reml=True, maxiter=2000)
        model_warnings = [str(item.message) for item in caught]
        converged = fitted.converged
        coeff_i = fitted.params["vowel_code"]
        t_i = fitted.tvalues["vowel_code"]
        p_i = fitted.pvalues["vowel_code"]
        n_obs = int(fitted.nobs)
    except Exception as exc:
        return GateResult(
            state=GateState.indeterminate,
            summary=f"Mixed model failed: {exc}",
            codamd_hash=actual_hash,
            cohort_flow={
                "total_input": total_input,
                "after_handv_filter": after_handv,
                "after_codatype_filter": after_codatype,
                "after_whale_filter": after_whales,
                "n_a": n_a,
                "n_i": n_i,
            },
            per_whale_effects=[],
        )

    mixed_model = MixedModelResult(
        coefficient_label="vowel_code (i=1, a=0)",
        coefficient_value=coeff_i,
        t_value=t_i,
        p_value=p_i,
        converged=converged,
        n_obs=n_obs,
        n_groups=n_groups,
    )

    # Per-whale raw effects
    per_whale_effects: list[PerWhaleEffect] = []
    for wid in FOUR_WHALES:
        sub = df[df["whale"] == wid]
        a_vals = sub[sub["handv"] == "a"]["Duration"].values
        i_vals = sub[sub["handv"] == "i"]["Duration"].values
        pe = PerWhaleEffect(
            whale_id=wid,
            n_a=int(len(a_vals)),
            n_i=int(len(i_vals)),
            raw_mean_a=float(np.mean(a_vals)) if len(a_vals) > 0 else 0.0,
            raw_mean_i=float(np.mean(i_vals)) if len(i_vals) > 0 else 0.0,
            raw_diff_a_minus_i=float(np.mean(a_vals) - np.mean(i_vals))
            if len(a_vals) > 0 and len(i_vals) > 0
            else 0.0,
        )
        per_whale_effects.append(pe)

    # Normalized per-whale effects (z-scores within this partition)
    for wid in FOUR_WHALES:
        sub = df[df["whale"] == wid]
        durations = sub["Duration"].values
        n = len(durations)
        if n < 2:
            continue
        mean_s = float(np.mean(durations))
        sd_s = float(np.std(durations, ddof=1))
        if sd_s <= 0:
            continue
        sub = sub.copy()
        sub["z"] = (sub["Duration"] - mean_s) / sd_s
        z_a = sub[sub["handv"] == "a"]["z"].mean()
        z_i = sub[sub["handv"] == "i"]["z"].mean()
        for pe in per_whale_effects:
            if pe.whale_id == wid:
                pe.z_mean_a = float(z_a)
                pe.z_mean_i = float(z_i)
                pe.z_diff_a_minus_i = float(z_a - z_i)

    # Evaluate criteria
    issues: list[str] = []
    if not converged:
        issues.append("Mixed model did not converge")
    if coeff_i >= 0:
        issues.append(f"i coefficient {coeff_i:.4f} is not negative")
    elif abs(coeff_i - PUBLISHED_I_COEFF) > PUBLISHED_TOLERANCE:
        issues.append(
            f"i coefficient {coeff_i:.4f} differs from {-0.13:.2f} by more than {PUBLISHED_TOLERANCE}"
        )

    all_raw_pos = all(pe.raw_diff_a_minus_i > 0 for pe in per_whale_effects)
    if not all_raw_pos:
        neg_whales = [
            pe.whale_id for pe in per_whale_effects if pe.raw_diff_a_minus_i <= 0
        ]
        issues.append(f"Raw a-i effects not positive for: {neg_whales}")

    all_z_pos = all(
        pe.z_diff_a_minus_i is not None and pe.z_diff_a_minus_i > 0
        for pe in per_whale_effects
    )
    if not all_z_pos:
        neg_z = [
            pe.whale_id
            for pe in per_whale_effects
            if pe.z_diff_a_minus_i is None or pe.z_diff_a_minus_i <= 0
        ]
        issues.append(f"Normalized a-i effects not positive for: {neg_z}")

    if issues:
        return GateResult(
            state=GateState.fail,
            summary="; ".join(issues),
            codamd_hash=actual_hash,
            cohort_flow={
                "total_input": total_input,
                "after_handv_filter": after_handv,
                "after_codatype_filter": after_codatype,
                "after_whale_filter": after_whales,
                "n_a": n_a,
                "n_i": n_i,
            },
            per_whale_effects=per_whale_effects,
            mixed_model=mixed_model,
            details={"model_warnings": model_warnings},
        )

    return GateResult(
        state=GateState.pass_,
        summary="All criteria met: hash match, sample counts match, i coefficient negative and within tolerance, all four within-whale raw and normalized a-i effects positive",
        codamd_hash=actual_hash,
        cohort_flow={
            "total_input": total_input,
            "after_handv_filter": after_handv,
            "after_codatype_filter": after_codatype,
            "after_whale_filter": after_whales,
            "n_a": n_a,
            "n_i": n_i,
        },
        per_whale_effects=per_whale_effects,
        mixed_model=mixed_model,
        details={"model_warnings": model_warnings},
    )


def write_gate_result(result: GateResult, output_path: str | Path) -> None:
    """Persist a gate artifact atomically."""
    write_json_atomic(result, output_path)


__all__ = ["run_duration_gate", "write_gate_result"]
