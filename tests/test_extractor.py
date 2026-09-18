from __future__ import annotations

import pytest

from contracts.models import CodaRecord, IdentityStatus, SourceRef
from data.loader import load_dominica_codas
from phonology.timing import (
    DURATION_TOLERANCE_S,
    extract_all,
    extract_codamd_partition,
    extract_timing,
)

DOMINICA = "external/sw-combinatoriality/data/DominicaCodas.csv"
CODAMD = "external/phonology-osf-9t6qu/codamd.csv"


def make_record(n_clicks: int, icis: list[float], duration: float, num: int = 1) -> CodaRecord:
    return CodaRecord(
        coda_id=f"dominica:{num}",
        source="metadata",
        source_ref=SourceRef(dataset="DominicaCodas.csv", row=num + 1),
        click_count=n_clicks,
        duration_s=duration,
        icis_s=icis,
        coda_type="5R1",
        whale_id_raw="5586",
        whale_id="5586",
        identity_status=IdentityStatus.resolved,
        unit="A",
        clan="EC1",
    )


class TestCanonicalTiming:
    def test_click_times_are_cumulative_from_zero(self):
        timing = extract_timing(make_record(4, [0.2, 0.3, 0.1], 0.6))
        assert timing.click_times_s == pytest.approx([0.0, 0.2, 0.5, 0.6])
        assert timing.duration_consistent

    def test_round_trip_within_tolerance(self):
        icis = [0.21, 0.19, 0.25, 0.22]
        timing = extract_timing(make_record(5, icis, sum(icis)))
        recovered = [
            b - a for a, b in zip(timing.click_times_s, timing.click_times_s[1:])
        ]
        for got, want in zip(recovered, icis):
            assert abs(got - want) <= DURATION_TOLERANCE_S

    def test_duration_residual_flagged_not_repaired(self):
        timing = extract_timing(make_record(3, [0.2, 0.2], 0.5))
        assert not timing.duration_consistent
        assert timing.duration_residual_s == pytest.approx(0.1)
        assert timing.duration_s_reported == 0.5

    def test_single_click_coda(self):
        timing = extract_timing(make_record(1, [], 0.0))
        assert timing.click_times_s == [0.0]
        assert timing.icis_s == []
        assert timing.duration_consistent


@pytest.fixture(scope="module")
def loaded():
    return load_dominica_codas(DOMINICA, qc_mode="permissive")


class TestCorpusExtraction:

    def test_corpus_counts_and_flagged_residuals(self, loaded):
        result = extract_all(loaded)
        assert result.qc.n_timings == 8714
        # 10 raw duration mismatches exist; 3 sit in quarantined rows and
        # never reach extraction.
        assert result.qc.n_duration_inconsistent == 7
        assert result.qc.max_abs_residual_s == pytest.approx(0.0095565, abs=1e-4)
        assert result.qc.join is None
        assert result.gate_partition == []

    def test_every_timing_validates(self, loaded):
        result = extract_all(loaded)
        for timing in result.timings[:200]:
            assert len(timing.click_times_s) == timing.click_count
            assert len(timing.icis_s) == timing.click_count - 1
            assert timing.click_times_s[0] == 0.0

    def test_deterministic_replay(self, loaded):
        first = extract_all(loaded).model_dump_json()
        second = extract_all(loaded).model_dump_json()
        assert first == second


class TestCodamdJoin:

    def test_join_counts(self, loaded):
        timings, qc = extract_codamd_partition(CODAMD, loaded.records)
        assert qc.n_codamd_rows == 1375
        # codanum 5092 sits in the gate partition but its Dominica row was
        # quarantined for ICI-layout inconsistency: surfaced, never guessed.
        assert qc.n_joined == 1374
        assert qc.unjoined_codanums == [5092]
        assert qc.n_duration_mismatch == 4
        assert len(timings) == 1374

    def test_join_carries_labels(self, loaded):
        timings, _ = extract_codamd_partition(CODAMD, loaded.records)
        gate = [t for t in timings if t.coda_type == "1+1+3" and t.vowel in ("a", "i")]
        # 709 vowel-labelled 1+1+3 rows exist in codamd; 5092 is unjoined.
        assert len(gate) == 708
        for timing in gate:
            assert timing.vowel in ("a", "i")
            assert timing.whale_id_raw
            assert timing.icis_s

    def test_gate_partition_in_extract_all(self, loaded):
        result = extract_all(loaded, codamd_path=CODAMD)
        assert len(result.gate_partition) == 1374
        assert result.qc.join is not None
        assert result.qc.join.n_joined == 1374
        assert "codamd" in result.input_hashes
