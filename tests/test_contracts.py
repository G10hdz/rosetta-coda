import math

import pytest
from pydantic import ValidationError

from contracts.models import (
    CodaRecord,
    GateResult,
    GateState,
    IdentityStatus,
    MixedModelResult,
    NormalizedCoda,
    PerWhaleEffect,
    SchemaVersion,
    SourceRef,
    WhaleBaseline,
)


def _make_record(**kw):
    defaults = dict(
        coda_id="dominica:1",
        source="metadata",
        source_ref=SourceRef(dataset="test.csv", row=1),
        click_count=5,
        duration_s=1.0,
        icis_s=[0.2, 0.2, 0.3, 0.3],
        coda_type="5R1",
        whale_id_raw="5586",
        whale_id="5586",
        identity_status=IdentityStatus.resolved,
        unit="A",
        clan="EC1",
    )
    defaults.update(kw)
    return CodaRecord(**defaults)


class TestCodaRecordValidation:
    def test_valid_record(self):
        r = _make_record()
        assert r.click_count == 5
        assert len(r.icis_s) == 4

    def test_rejects_nan_duration(self):
        with pytest.raises(ValidationError):
            _make_record(duration_s=math.nan)

    def test_rejects_inf_duration(self):
        with pytest.raises(ValidationError):
            _make_record(duration_s=math.inf)

    def test_rejects_negative_duration(self):
        with pytest.raises(ValidationError):
            _make_record(duration_s=-0.5)

    def test_allows_zero_duration(self):
        r = _make_record(duration_s=0.0, click_count=1, icis_s=[])
        assert r.duration_s == 0.0

    def test_rejects_ici_count_mismatch(self):
        with pytest.raises(ValidationError, match="ICI count"):
            _make_record(click_count=5, icis_s=[0.2, 0.2, 0.3])

    def test_rejects_negative_click_count(self):
        with pytest.raises(ValidationError):
            _make_record(click_count=0)

    def test_json_round_trip(self):
        r = _make_record()
        data = r.model_dump()
        r2 = CodaRecord(**data)
        assert r2 == r

    def test_schema_version_enum(self):
        assert SchemaVersion.v0_1_0.value == "0.1.0"

    def test_identity_status_values(self):
        assert IdentityStatus.resolved.value == "resolved"
        assert IdentityStatus.unresolved_unknown.value == "unresolved_unknown"
        assert IdentityStatus.unresolved_composite.value == "unresolved_composite"
        assert IdentityStatus.unresolved_uncertain.value == "unresolved_uncertain"


class TestEdgeCases:
    def test_ici_nan_rejected(self):
        with pytest.raises(ValidationError):
            _make_record(icis_s=[0.2, math.nan, 0.3, 0.3])

    def test_ici_inf_rejected(self):
        with pytest.raises(ValidationError):
            _make_record(icis_s=[0.2, math.inf, 0.3, 0.3])

    def test_canonical_zero_ici_rejected(self):
        with pytest.raises(ValidationError):
            _make_record(icis_s=[0.2, 0.0, 0.3, 0.3])

    def test_normalized_coda_null_z(self):
        nc = NormalizedCoda(
            coda_id="test:1",
            whale_id=None,
            whale_id_raw="0",
            identity_status=IdentityStatus.unresolved_unknown,
            raw_duration_s=1.0,
            duration_z=None,
        )
        assert nc.duration_z is None

    def test_whale_baseline_ineligible(self):
        wb = WhaleBaseline(
            whale_id="TEST",
            n=1,
            mean_s=0.5,
            sd_s=0.0,
            partition_id="test",
            input_hash="abc123",
            ineligible_reason="n<2",
        )
        assert wb.ineligible_reason == "n<2"

    def test_gate_result_states(self):
        for state in [GateState.pass_, GateState.fail, GateState.indeterminate]:
            gr = GateResult(
                state=state,
                summary="test",
                codamd_hash="abc",
                cohort_flow={},
                per_whale_effects=[],
            )
            assert gr.state == state

    def test_per_whale_effect_defaults(self):
        pe = PerWhaleEffect(
            whale_id="ATWOOD",
            n_a=10,
            n_i=10,
            raw_mean_a=0.5,
            raw_mean_i=0.4,
            raw_diff_a_minus_i=0.1,
        )
        assert pe.z_diff_a_minus_i is None

    def test_mixed_model_result(self):
        mm = MixedModelResult(
            coefficient_label="test",
            coefficient_value=-0.13,
            t_value=-6.84,
            p_value=0.017,
            converged=True,
            n_obs=628,
            n_groups=4,
        )
        assert mm.coefficient_value == -0.13
