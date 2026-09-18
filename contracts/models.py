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


class CodaTiming(BaseModel):
    coda_id: str
    source: str = "metadata"
    source_ref: SourceRef
    click_count: int
    click_times_s: list[float]
    icis_s: list[float]
    duration_s_reported: float
    duration_residual_s: float
    duration_consistent: bool
    whale_id_raw: str = ""
    identity_status: IdentityStatus
    coda_type: str = ""
    vowel: str | None = None
    focal: bool | None = None

    @model_validator(mode="after")
    def _timing_is_canonical(self) -> "CodaTiming":
        if len(self.icis_s) != self.click_count - 1:
            raise ValueError(
                f"ICI count {len(self.icis_s)} != click_count - 1 "
                f"({self.click_count - 1}) for coda {self.coda_id}"
            )
        if len(self.click_times_s) != self.click_count:
            raise ValueError(
                f"click_times count {len(self.click_times_s)} != click_count "
                f"({self.click_count}) for coda {self.coda_id}"
            )
        if self.click_times_s and self.click_times_s[0] != 0.0:
            raise ValueError("click_times_s must start at 0.0")
        return self


class DurationMismatch(BaseModel):
    coda_id: str
    residual_s: float


class JoinMismatch(BaseModel):
    codanum: int
    coda_id: str
    duration_codamd_s: float
    duration_dominica_s: float
    residual_s: float


class JoinQC(BaseModel):
    n_codamd_rows: int
    n_joined: int
    n_unjoined: int
    unjoined_codanums: list[int] = Field(default_factory=list)
    n_duration_mismatch: int
    duration_mismatches: list[JoinMismatch] = Field(default_factory=list)


class ExtractionQC(BaseModel):
    n_input: int
    n_timings: int
    n_duration_inconsistent: int
    max_abs_residual_s: float
    duration_mismatches: list[DurationMismatch] = Field(default_factory=list)
    join: JoinQC | None = None


class DetectionState(str, Enum):
    detected = "detected"
    not_observable = "not_observable"
    failed = "failed"


class CodaDetection(BaseModel):
    coda_id: str
    click_times_s: list[float]
    click_count: int


class DetectionMetrics(BaseModel):
    n_clicks: int = 0
    n_codas: int = 0
    parity: str = "unverified"


class DetectionResult(BaseArtifact):
    state: DetectionState
    detector_version: str = "energy-envelope-v1"
    params_hash: str
    source_wav_sha256: str | None = None
    detections: list[CodaDetection] = Field(default_factory=list)
    metrics: DetectionMetrics = Field(default_factory=DetectionMetrics)
    error: str | None = None


class ExtractionResult(BaseModel):
    schema_version: str = SchemaVersion.v0_1_0.value
    code_version: str = "coda-extractor-v1"
    timings: list[CodaTiming]
    gate_partition: list[CodaTiming] = Field(default_factory=list)
    qc: ExtractionQC
    input_hashes: dict[str, str] = Field(default_factory=dict)


class PhonologyFeature(BaseModel):
    coda_id: str
    source: str = "metadata"
    source_ref: SourceRef
    click_count: int
    click_rate_hz: float | None = None
    mean_ici_s: float | None = None
    ici_cv: float | None = None
    npvi: float | None = None
    ici_pattern: list[float] | None = None
    initial_ici_ratio: float | None = None
    terminal_ici_ratio: float | None = None
    rubato_slope: float | None = None
    drift_s: float | None = None
    duration_z: float | None = None
    spectral_quality: str = "not_observable"
    formants: str = "not_observable"
    edge_coarticulation: str = "not_observable"
    whale_id_raw: str = ""
    identity_status: IdentityStatus
    coda_type: str = ""
    vowel: str | None = None


class FeatureContrast(BaseModel):
    feature: str
    n_whales: int
    a_minus_i: float
    ci95_low: float | None = None
    ci95_high: float | None = None


class WhaleFeatureMean(BaseModel):
    whale_id_raw: str
    vowel: str | None
    n: int
    means: dict[str, float | None] = Field(default_factory=dict)


class FeatureSet(BaseModel):
    schema_version: str = SchemaVersion.v0_1_0.value
    code_version: str = "phonology-features-v1"
    input_hashes: dict[str, str] = Field(default_factory=dict)
    n_features: int
    n_gate_partition: int
    partition_features: list[PhonologyFeature] = Field(default_factory=list)
    partition_contrasts: list[FeatureContrast] = Field(default_factory=list)
    whale_feature_means: list[WhaleFeatureMean] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class AnalystEvidence(BaseModel):
    """Frozen evidence bundle handed to the analyst model.

    Everything the model may cite lives inside this document; evidence_refs
    are validated as JSON Pointers against it. Deterministic sample: the
    first N gate-partition feature records by coda_id sort.
    """

    schema_version: str = SchemaVersion.v0_1_0.value
    gate: GateResult
    partition_contrasts: list[FeatureContrast] = Field(default_factory=list)
    whale_feature_means: list[WhaleFeatureMean] = Field(default_factory=list)
    feature_records_sample: list[PhonologyFeature] = Field(default_factory=list)
    evidence_manifest: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ModelCallRecord(BaseModel):
    call_id: str
    model: str
    reasoning_effort: str = ""
    params_hash: str
    request_sha256: str
    response: Any = None
    usage: dict[str, int] = Field(default_factory=dict)
    cache_key: str


class RankedHypothesis(BaseModel):
    rank: int
    score: float
    score_components: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    hypothesis: dict[str, Any]
    uncertainty: dict[str, Any] = Field(default_factory=dict)


class RankedHypotheses(BaseModel):
    schema_version: str = SchemaVersion.v0_1_0.value
    selection_rule_version: str = "rank-v1"
    evidence_manifest: dict[str, str] = Field(default_factory=dict)
    state: str = "ok"
    ranked: list[RankedHypothesis] = Field(default_factory=list)
