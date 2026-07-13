from __future__ import annotations

import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SchemaVersion(str, Enum):
    v0_1_0 = "0.1.0"


class IdentityStatus(str, Enum):
    resolved = "resolved"
    unresolved_unknown = "unresolved_unknown"
    unresolved_composite = "unresolved_composite"
    unresolved_uncertain = "unresolved_uncertain"


class GateState(str, Enum):
    pass_ = "pass"
    fail = "fail"
    indeterminate = "indeterminate"


class SourceRef(BaseModel):
    dataset: str
    row: int


class BaseArtifact(BaseModel):
    schema_version: str = SchemaVersion.v0_1_0.value
    run_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    producer: str = "rosetta-coda"
    code_revision: str | None = None
    config_hash: str | None = None
    input_hashes: dict[str, str] = Field(default_factory=dict)


class CodaRecord(BaseModel):
    coda_id: str
    source: str = "metadata"
    source_ref: SourceRef
    source_values: dict[str, str] = Field(default_factory=dict)
    click_count: int
    duration_s: float
    icis_s: list[float]
    coda_type: str
    whale_id_raw: str
    whale_id: str | None
    identity_status: IdentityStatus
    unit: str
    clan: str
    date: str | None = None

    @field_validator("duration_s")
    @classmethod
    def _duration_not_nan_inf_neg(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"duration must be finite, got {v}")
        if v < 0:
            raise ValueError(f"duration must be non-negative, got {v}")
        return v

    @field_validator("icis_s")
    @classmethod
    def _icis_not_nan_inf(cls, v: list[float]) -> list[float]:
        for x in v:
            if math.isnan(x) or math.isinf(x):
                raise ValueError(f"ICIs must be finite, got {x}")
            if x <= 0:
                raise ValueError(f"Canonical ICIs must be positive, got {x}")
        return v

    @field_validator("click_count")
    @classmethod
    def _click_count_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"click_count must be >= 1, got {v}")
        return v

    @model_validator(mode="after")
    def _ici_count_matches_click_count(self) -> "CodaRecord":
        expected = self.click_count - 1
        actual = len(self.icis_s)
        if actual != expected:
            raise ValueError(
                f"ICI count {actual} != click_count - 1 ({expected}) "
                f"for coda {self.coda_id}"
            )
        return self

    @model_validator(mode="after")
    def _identity_fields_are_consistent(self) -> "CodaRecord":
        if self.identity_status == IdentityStatus.resolved:
            if not self.whale_id or self.whale_id != self.whale_id_raw:
                raise ValueError("resolved identity requires whale_id == whale_id_raw")
        elif self.whale_id is not None:
            raise ValueError("unresolved identity requires whale_id=null")
        return self


class QuarantinedRow(BaseModel):
    coda_id_raw: str
    source_ref: SourceRef
    reason: str
    raw_values: dict[str, str]


class LoadResult(BaseModel):
    records: list[CodaRecord]
    dataset_hash: str
    schema_version: str = SchemaVersion.v0_1_0.value
    row_count: int
    cohort_counts: dict[str, int]
    quarantined: list[QuarantinedRow] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class WhaleBaseline(BaseModel):
    whale_id: str
    n: int
    mean_s: float
    sd_s: float
    partition_id: str
    input_hash: str
    ineligible_reason: str | None = None


class NormalizedCoda(BaseModel):
    coda_id: str
    whale_id: str | None
    whale_id_raw: str
    identity_status: IdentityStatus
    raw_duration_s: float
    duration_z: float | None = None
    baseline_ref: str | None = None


class NormalizationResult(BaseModel):
    baselines: list[WhaleBaseline]
    normalized: list[NormalizedCoda]
    excluded: list[NormalizedCoda]
    quarantined: list[NormalizedCoda]
    counts: dict[str, int]
    input_hash: str
    partition_id: str


class PerWhaleEffect(BaseModel):
    whale_id: str
    n_a: int
    n_i: int
    raw_mean_a: float
    raw_mean_i: float
    raw_diff_a_minus_i: float
    z_mean_a: float | None = None
    z_mean_i: float | None = None
    z_diff_a_minus_i: float | None = None


class MixedModelResult(BaseModel):
    coefficient_label: str
    coefficient_value: float
    t_value: float
    p_value: float
    converged: bool
    n_obs: int
    n_groups: int


class GateResult(BaseModel):
    state: GateState
    summary: str
    codamd_hash: str
    cohort_flow: dict[str, int]
    per_whale_effects: list[PerWhaleEffect]
    mixed_model: MixedModelResult | None = None
    schema_version: str = SchemaVersion.v0_1_0.value
    details: dict[str, Any] = Field(default_factory=dict)
