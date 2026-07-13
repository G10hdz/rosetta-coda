from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict

import numpy as np

from contracts.models import (
    CodaRecord,
    IdentityStatus,
    NormalizationResult,
    NormalizedCoda,
    WhaleBaseline,
)


def normalize_durations(
    records: list[CodaRecord],
    partition_id: str = "default",
    input_hash: str | None = None,
) -> NormalizationResult:
    ordered_records = sorted(records, key=lambda record: record.coda_id)
    if input_hash is None:
        canonical = json.dumps(
            [record.model_dump(mode="json") for record in ordered_records],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        input_hash = hashlib.sha256(canonical).hexdigest()

    eligible = [
        r
        for r in ordered_records
        if r.identity_status == IdentityStatus.resolved
        and r.whale_id is not None
        and math.isfinite(r.duration_s)
        and r.duration_s >= 0
    ]

    eligible_ids = {r.coda_id for r in eligible}

    normalized: list[NormalizedCoda] = []
    baselines: list[WhaleBaseline] = []
    excluded: list[NormalizedCoda] = []
    quarantined: list[NormalizedCoda] = []

    whale_groups: dict[str, list[CodaRecord]] = defaultdict(list)
    for r in eligible:
        assert r.whale_id is not None
        whale_groups[r.whale_id].append(r)

    for wid in sorted(whale_groups):
        group = whale_groups[wid]
        durations = np.array([r.duration_s for r in group])
        n = len(durations)
        mean_s = float(np.mean(durations))
        sd_s = float(np.std(durations, ddof=1)) if n > 1 else 0.0

        if n < 2 or sd_s <= 0:
            reason = (
                "n<2" if n < 2 else "sd=0"
            )
            baselines.append(
                WhaleBaseline(
                    whale_id=wid,
                    n=n,
                    mean_s=mean_s,
                    sd_s=sd_s,
                    partition_id=partition_id,
                    input_hash=input_hash,
                    ineligible_reason=reason,
                )
            )
            for r in group:
                excluded.append(
                    NormalizedCoda(
                        coda_id=r.coda_id,
                        whale_id=wid,
                        whale_id_raw=r.whale_id_raw,
                        identity_status=r.identity_status,
                        raw_duration_s=r.duration_s,
                        duration_z=None,
                        baseline_ref=None,
                    )
                )
            continue

        baseline = WhaleBaseline(
            whale_id=wid,
            n=n,
            mean_s=mean_s,
            sd_s=sd_s,
            partition_id=partition_id,
            input_hash=input_hash,
        )
        baselines.append(baseline)

        for r in group:
            z = (r.duration_s - mean_s) / sd_s
            normalized.append(
                NormalizedCoda(
                    coda_id=r.coda_id,
                    whale_id=wid,
                    whale_id_raw=r.whale_id_raw,
                    identity_status=r.identity_status,
                    raw_duration_s=r.duration_s,
                    duration_z=z,
                    baseline_ref=f"{partition_id}:{wid}",
                )
            )

    # unresolved / excluded rows get null z
    for r in ordered_records:
        if r.coda_id in eligible_ids:
            continue
        if r.identity_status != IdentityStatus.resolved or not (
            math.isfinite(r.duration_s) and r.duration_s >= 0
        ):
            quarantined.append(
                NormalizedCoda(
                    coda_id=r.coda_id,
                    whale_id=None,
                    whale_id_raw=r.whale_id_raw,
                    identity_status=r.identity_status,
                    raw_duration_s=r.duration_s,
                    duration_z=None,
                )
            )

    n_resolved = sum(
        1 for r in ordered_records if r.identity_status == IdentityStatus.resolved
    )
    n_unresolved = len(ordered_records) - n_resolved

    return NormalizationResult(
        baselines=baselines,
        normalized=normalized,
        excluded=excluded,
        quarantined=quarantined,
        counts={
            "total": len(ordered_records),
            "resolved": n_resolved,
            "unresolved": n_unresolved,
            "eligible_baselined": len(normalized),
            "ineligible_excluded": len(excluded),
            "quarantined": len(quarantined),
        },
        input_hash=input_hash,
        partition_id=partition_id,
    )


__all__ = ["normalize_durations"]
