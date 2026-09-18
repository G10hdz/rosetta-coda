from __future__ import annotations

import hashlib
from itertools import accumulate
from pathlib import Path

import pandas as pd

from contracts.models import (
    CodaRecord,
    CodaTiming,
    DurationMismatch,
    ExtractionQC,
    ExtractionResult,
    IdentityStatus,
    JoinMismatch,
    JoinQC,
    LoadResult,
    SourceRef,
)

DURATION_TOLERANCE_S = 1e-6
CODAMD_REQUIRED_COLS = ["codanum", "focal", "whale", "codatype", "Duration", "handv"]


def _file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dominica_num(record: CodaRecord) -> int:
    return int(record.coda_id.split(":", 1)[1])


def extract_timing(record: CodaRecord) -> CodaTiming:
    click_times = [0.0] + list(accumulate(record.icis_s))
    residual = record.duration_s - sum(record.icis_s)
    return CodaTiming(
        coda_id=record.coda_id,
        source=record.source,
        source_ref=record.source_ref,
        click_count=record.click_count,
        click_times_s=click_times,
        icis_s=list(record.icis_s),
        duration_s_reported=record.duration_s,
        duration_residual_s=residual,
        duration_consistent=abs(residual) <= DURATION_TOLERANCE_S,
        whale_id_raw=record.whale_id_raw,
        identity_status=record.identity_status,
        coda_type=record.coda_type,
    )


def extract_codamd_partition(
    codamd_path: str | Path,
    records: list[CodaRecord],
) -> tuple[list[CodaTiming], JoinQC]:
    """Extract canonical timing for codamd rows via the codanum join.

    codamd.csv carries the published vowel labels (handv) but no ICIs; the
    Dominica corpus carries ICIs but no vowel labels. The verified join key
    codanum == codaNUM2018 produces timings that carry both.
    """
    df = pd.read_csv(codamd_path, encoding="utf-8-sig")
    missing = set(CODAMD_REQUIRED_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"codamd missing required columns: {sorted(missing)}")
    if df["codanum"].duplicated().any():
        dupes = sorted(df["codanum"][df["codanum"].duplicated()].unique())
        raise ValueError(f"Ambiguous join: duplicate codanum values {dupes}")

    by_num = {_dominica_num(record): record for record in records}
    timings: list[CodaTiming] = []
    unjoined: list[int] = []
    mismatches: list[JoinMismatch] = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        codanum = int(row["codanum"])
        record = by_num.get(codanum)
        if record is None:
            unjoined.append(codanum)
            continue

        residual_cross = float(row["Duration"]) - record.duration_s
        if abs(residual_cross) > DURATION_TOLERANCE_S:
            mismatches.append(
                JoinMismatch(
                    codanum=codanum,
                    coda_id=record.coda_id,
                    duration_codamd_s=float(row["Duration"]),
                    duration_dominica_s=record.duration_s,
                    residual_s=residual_cross,
                )
            )

        click_times = [0.0] + list(accumulate(record.icis_s))
        residual = float(row["Duration"]) - sum(record.icis_s)
        handv = str(row["handv"]).strip()
        focal_raw = row["focal"]
        focal = (
            focal_raw
            if isinstance(focal_raw, bool)
            else str(focal_raw).strip().lower() == "true"
        )
        timings.append(
            CodaTiming(
                coda_id=record.coda_id,
                source="metadata",
                source_ref=SourceRef(dataset="codamd.csv", row=row_num),
                click_count=record.click_count,
                click_times_s=click_times,
                icis_s=list(record.icis_s),
                duration_s_reported=float(row["Duration"]),
                duration_residual_s=residual,
                duration_consistent=abs(residual) <= DURATION_TOLERANCE_S,
                whale_id_raw=str(row["whale"]).strip(),
                identity_status=IdentityStatus.resolved,
                coda_type=str(row["codatype"]).strip(),
                vowel=handv if handv in ("a", "i") else None,
                focal=focal,
            )
        )

    qc = JoinQC(
        n_codamd_rows=len(df),
        n_joined=len(timings),
        n_unjoined=len(unjoined),
        unjoined_codanums=unjoined,
        n_duration_mismatch=len(mismatches),
        duration_mismatches=mismatches,
    )
    return timings, qc


def extract_all(
    loaded: LoadResult,
    codamd_path: str | Path | None = None,
) -> ExtractionResult:
    timings = [extract_timing(record) for record in loaded.records]
    mismatches = [
        DurationMismatch(coda_id=t.coda_id, residual_s=t.duration_residual_s)
        for t in timings
        if not t.duration_consistent
    ]

    join_qc: JoinQC | None = None
    gate_partition: list[CodaTiming] = []
    input_hashes = {"dominica": loaded.dataset_hash}
    if codamd_path is not None:
        gate_partition, join_qc = extract_codamd_partition(
            codamd_path, loaded.records
        )
        input_hashes["codamd"] = _file_hash(codamd_path)

    qc = ExtractionQC(
        n_input=len(loaded.records),
        n_timings=len(timings),
        n_duration_inconsistent=len(mismatches),
        max_abs_residual_s=max(
            (abs(m.residual_s) for m in mismatches), default=0.0
        ),
        duration_mismatches=mismatches,
        join=join_qc,
    )
    return ExtractionResult(
        timings=timings,
        gate_partition=gate_partition,
        qc=qc,
        input_hashes=input_hashes,
    )


__all__ = ["extract_all", "extract_codamd_partition", "extract_timing"]
