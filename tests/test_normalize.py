import numpy as np

from analysis.normalize import normalize_durations
from contracts.models import (
    CodaRecord,
    IdentityStatus,
    SourceRef,
)


def _record(oid, wid, dur, status=IdentityStatus.resolved):
    click_count = 1 if dur == 0 else 3
    icis = [] if click_count == 1 else [dur / 3, dur / 3]
    return CodaRecord(
        coda_id=f"test:{oid}",
        source="metadata",
        source_ref=SourceRef(dataset="test.csv", row=oid),
        click_count=click_count,
        duration_s=dur,
        icis_s=icis,
        coda_type="1-NOISE" if click_count == 1 else "1+1+1",
        whale_id_raw=wid,
        whale_id=wid if status == IdentityStatus.resolved else None,
        identity_status=status,
        unit="A",
        clan="EC1",
    )


class TestNormalize:
    def test_constant_duration_singleton_ineligible(self):
        records = [_record(1, "WHALE1", 0.5)]
        result = normalize_durations(records)
        assert len(result.normalized) == 0
        assert len(result.excluded) == 1
        assert result.baselines[0].ineligible_reason is not None

    def test_two_identical_durations_singleton_ineligible(self):
        """Two identical durations -> sd=0 -> ineligible"""
        records = [
            _record(1, "WHALE1", 0.5),
            _record(2, "WHALE1", 0.5),
        ]
        result = normalize_durations(records)
        assert len(result.normalized) == 0
        assert result.baselines[0].ineligible_reason == "sd=0"

    def test_z_score_approx_zero_mean(self):
        """Synthetic whale with 100 points ~N(1, 0.1) produces z ~N(0,1)"""
        rng = np.random.default_rng(42)
        durs = list(rng.normal(1.0, 0.1, 100))
        records = [_record(i, "SYNTH", durs[i]) for i in range(100)]
        result = normalize_durations(records)
        assert len(result.normalized) == 100
        zs = [n.duration_z for n in result.normalized]
        assert abs(np.mean(zs)) < 0.05
        assert abs(np.std(zs, ddof=1) - 1.0) < 0.05

    def test_two_whales_same_baseline_mean(self):
        records = [
            _record(1, "A", 0.8),
            _record(2, "A", 1.2),
            _record(3, "B", 0.8),
            _record(4, "B", 1.2),
        ]
        result = normalize_durations(records)
        assert len(result.baselines) == 2
        assert all(b.n == 2 for b in result.baselines)
        assert result.baselines[0].mean_s == result.baselines[1].mean_s

    def test_unresolved_always_null_z(self):
        records = [
            _record(1, "REAL", 0.5),
            _record(2, "REAL", 1.5),
            _record(3, "0", 0.8, IdentityStatus.unresolved_unknown),
        ]
        result = normalize_durations(records)
        assert len(result.normalized) == 2
        assert len(result.quarantined) == 1
        assert result.quarantined[0].duration_z is None
        assert result.quarantined[0].whale_id is None
        assert result.quarantined[0].whale_id_raw == "0"

    def test_unresolved_never_in_baseline(self):
        records = [
            _record(1, "REAL", 0.5),
            _record(2, "REAL", 1.5),
            _record(3, "0", 0.8, IdentityStatus.unresolved_unknown),
        ]
        result = normalize_durations(records)
        assert result.baselines[0].whale_id == "REAL"
        assert result.counts["eligible_baselined"] == 2
        assert result.counts["unresolved"] == 1

    def test_deterministic_output(self):
        rng = np.random.default_rng(99)
        durs = list(rng.normal(0.9, 0.15, 20))
        records = [_record(i, "DET", durs[i]) for i in range(20)]
        r1 = normalize_durations(records)
        r2 = normalize_durations(records)
        z1 = [n.duration_z for n in r1.normalized]
        z2 = [n.duration_z for n in r2.normalized]
        assert z1 == z2

    def test_row_order_does_not_change_result(self):
        records = [
            _record(2, "B", 1.2),
            _record(1, "A", 0.8),
            _record(4, "B", 0.8),
            _record(3, "A", 1.2),
        ]
        forward = normalize_durations(records)
        reverse = normalize_durations(list(reversed(records)))
        assert forward == reverse

    def test_zero_duration_is_eligible(self):
        records = [_record(1, "ZERO", 0.0), _record(2, "ZERO", 1.0)]
        result = normalize_durations(records)
        assert len(result.normalized) == 2
        assert result.counts["quarantined"] == 0

    def test_counts_match(self):
        records = [
            _record(1, "WHALE1", 0.5),
            _record(2, "WHALE1", 1.5),
            _record(3, "WHALE2", 0.6),
            _record(4, "WHALE2", 1.4),
            _record(5, "0", 0.8, IdentityStatus.unresolved_unknown),
            _record(6, "9999", 0.9, IdentityStatus.unresolved_unknown),
            _record(7, "A/B", 1.0, IdentityStatus.unresolved_composite),
        ]
        result = normalize_durations(records)
        assert result.counts["total"] == 7
        assert result.counts["resolved"] == 4
        assert result.counts["unresolved"] == 3
        assert result.counts["eligible_baselined"] == 4
        assert result.counts["ineligible_excluded"] == 0
        assert result.counts["quarantined"] == 3
