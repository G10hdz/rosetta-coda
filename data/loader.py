from __future__ import annotations

import hashlib
import math
from datetime import datetime
from typing import Literal

import pandas as pd

from contracts.models import (
    CodaRecord,
    IdentityStatus,
    LoadResult,
    QuarantinedRow,
    SourceRef,
)

REQUIRED_COLS = [
    "codaNUM2018", "Date", "nClicks", "Duration",
    "ICI1", "ICI2", "ICI3", "ICI4", "ICI5",
    "ICI6", "ICI7", "ICI8", "ICI9",
    "CodaType", "Clan", "Unit", "UnitNum", "IDN",
]
ICI_COLS = [f"ICI{i}" for i in range(1, 10)]

SENTINEL_ZERO = "0"
SENTINEL_9999 = "9999"


def _parse_date(val: object) -> str:
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {s!r}")


def _classify_identity(idn_raw: str) -> IdentityStatus:
    if not idn_raw or idn_raw.lower() == "nan" or idn_raw in (
        SENTINEL_ZERO,
        SENTINEL_9999,
    ):
        return IdentityStatus.unresolved_unknown
    if "/" in idn_raw:
        return IdentityStatus.unresolved_composite
    if "?" in idn_raw:
        return IdentityStatus.unresolved_uncertain
    return IdentityStatus.resolved


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_ici_consistency(row: dict) -> bool:
    nclicks = int(row["nClicks"])
    expected_icis = nclicks - 1
    if expected_icis < 0:
        return False
    values = [float(row[f"ICI{i}"]) for i in range(1, 10)]
    return all(value > 0 for value in values[:expected_icis]) and all(
        value == 0 for value in values[expected_icis:]
    )


def load_dominica_codas(
    path: str,
    qc_mode: Literal["strict", "permissive"] = "strict",
) -> LoadResult:
    if qc_mode not in ("strict", "permissive"):
        raise ValueError(f"Unknown qc_mode: {qc_mode!r}")

    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )

    missing = set(REQUIRED_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if (df[REQUIRED_COLS] == "").any().any():
        missing_cells = {
            col: [int(i) + 2 for i in df.index[df[col] == ""]]
            for col in REQUIRED_COLS
            if (df[col] == "").any()
        }
        raise ValueError(f"Missing required values: {missing_cells}")

    raw_df = df.copy()

    dupes = df["codaNUM2018"][df["codaNUM2018"].duplicated(keep=False)]
    if not dupes.empty:
        raise ValueError(f"Duplicate codaNUM2018 values: {sorted(dupes.unique())}")

    hash_val = _file_hash(path)
    warnings: list[str] = []
    records: list[CodaRecord] = []
    cohort_counts: dict[str, int] = {e.value: 0 for e in IdentityStatus}

    numeric_cols = ["codaNUM2018", "UnitNum", "nClicks", "Duration"] + ICI_COLS
    for c in numeric_cols:
        try:
            df[c] = pd.to_numeric(df[c], errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric values in {c}") from exc
        if not df[c].map(math.isfinite).all():
            raise ValueError(f"Non-finite values in {c}")
        if (df[c] < 0).any():
            neg_rows = [int(i) + 2 for i in df.index[df[c] < 0]]
            raise ValueError(f"Negative values in {c} at rows: {neg_rows}")

    for c in ("codaNUM2018", "UnitNum", "nClicks"):
        if not df[c].map(lambda value: float(value).is_integer()).all():
            raise ValueError(f"Non-integer values in {c}")
        df[c] = df[c].astype(int)

    quarantined: list[QuarantinedRow] = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # 0-indexed + header + 1 -> 1-indexed CSV row
        idn_str = str(row["IDN"]).strip()
        identity_status = _classify_identity(idn_str)
        cohort_counts[identity_status.value] += 1

        ici_ok = _check_ici_consistency(row)
        if not ici_ok:
            nz = sum(1 for i in range(1, 10) if float(row[f"ICI{i}"]) != 0.0)
            msg = (
                f"Row {row_num} (coda {row['codaNUM2018']}): "
                "ICI layout inconsistent with nClicks-1; "
                f"non-zero count={nz}, expected={int(row['nClicks']) - 1}"
            )
            if qc_mode == "strict":
                raise ValueError(msg)
            warnings.append(f"QUARANTINED: {msg}")
            quarantined.append(
                QuarantinedRow(
                    coda_id_raw=str(row["codaNUM2018"]),
                    source_ref=SourceRef(dataset="DominicaCodas.csv", row=row_num),
                    reason=msg,
                    raw_values={col: str(raw_df.at[idx, col]) for col in REQUIRED_COLS},
                )
            )
            continue

        nclicks = int(row["nClicks"])
        raw_icis = [float(row[c]) for c in ICI_COLS]
        canonical_icis = raw_icis[: nclicks - 1]

        date_str = _parse_date(row["Date"])

        record = CodaRecord(
            coda_id=f"dominica:{row['codaNUM2018']}",
            source="metadata",
            source_ref=SourceRef(dataset="DominicaCodas.csv", row=row_num),
            source_values={col: str(raw_df.at[idx, col]) for col in REQUIRED_COLS},
            click_count=nclicks,
            duration_s=float(row["Duration"]),
            icis_s=canonical_icis,
            coda_type=str(row["CodaType"]).strip(),
            whale_id_raw=idn_str,
            whale_id=idn_str if identity_status == IdentityStatus.resolved else None,
            identity_status=identity_status,
            unit=str(row["Unit"]).strip(),
            clan=str(row["Clan"]).strip(),
            date=date_str,
        )
        records.append(record)

    return LoadResult(
        records=records,
        dataset_hash=hash_val,
        row_count=len(df),
        cohort_counts=cohort_counts,
        quarantined=quarantined,
        validation_warnings=warnings,
        schema_version="0.1.0",
    )


__all__ = ["load_dominica_codas"]
