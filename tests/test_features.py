from __future__ import annotations

import pytest

from contracts.models import CodaTiming, IdentityStatus, SourceRef
from data.loader import load_dominica_codas
from phonology.features import (
    build_feature_set,
    compute_features,
    gate_members,
    partition_contrasts,
    whale_feature_means,
)
from phonology.timing import extract_all

DOMINICA = "external/sw-combinatoriality/data/DominicaCodas.csv"
CODAMD = "external/phonology-osf-9t6qu/codamd.csv"


def make_timing(icis: list[float], num: int = 1, **kw) -> CodaTiming:
    n = len(icis) + 1
    times = [0.0]
    for ici in icis:
        times.append(times[-1] + ici)
    duration = icis and sum(icis) or kw.pop("duration", 0.0)
    return CodaTiming(
        coda_id=f"dominica:{num}",
        source="metadata",
        source_ref=SourceRef(dataset="DominicaCodas.csv", row=num + 1),
        click_count=n,
        click_times_s=times,
        icis_s=icis,
        duration_s_reported=kw.pop("duration", duration),
        duration_residual_s=0.0,
        duration_consistent=True,
        whale_id_raw=kw.pop("whale", "5586"),
        identity_status=IdentityStatus.resolved,
        coda_type=kw.pop("coda_type", "5R1"),
        vowel=kw.pop("vowel", None),
    )


class TestFeatureValues:
    def test_uniform_rhythm(self):
        f = compute_features(make_timing([0.2, 0.2, 0.2, 0.2]))
        assert f.mean_ici_s == pytest.approx(0.2)
        assert f.ici_cv == pytest.approx(0.0)
        assert f.npvi == pytest.approx(0.0)
        assert f.ici_pattern == pytest.approx([1.0, 1.0, 1.0, 1.0])
        assert f.initial_ici_ratio == pytest.approx(1.0)
        assert f.terminal_ici_ratio == pytest.approx(1.0)
        assert f.rubato_slope == pytest.approx(0.0)
        assert f.drift_s == pytest.approx(0.0)

    def test_accelerating_coda(self):
        f = compute_features(make_timing([0.1, 0.2, 0.3, 0.4]))
        assert f.mean_ici_s == pytest.approx(0.25)
        assert f.ici_cv == pytest.approx(0.129099 / 0.25, rel=1e-4)
        # nPVI: 100 * mean(|.1-.2|/.15, |.2-.3|/.25, |.3-.4|/.35)
        assert f.npvi == pytest.approx(
            100 * ((0.1 / 0.15 + 0.1 / 0.25 + 0.1 / 0.35) / 3)
        )
        assert f.initial_ici_ratio == pytest.approx(0.1 / (0.9 / 3))
        assert f.terminal_ici_ratio == pytest.approx(0.4 / 0.2)
        assert f.rubato_slope == pytest.approx(0.1 / 0.25)
        assert f.drift_s == pytest.approx(0.3)

    def test_click_rate(self):
        f = compute_features(make_timing([0.2, 0.2, 0.2]))
        assert f.click_rate_hz == pytest.approx(4 / 0.6)


class TestNullBoundaries:
    def test_single_click(self):
        f = compute_features(make_timing([], duration=0.0))
        assert f.click_rate_hz is None
        assert f.mean_ici_s is None
        assert f.ici_cv is None
        assert f.npvi is None
        assert f.ici_pattern is None
        assert f.rubato_slope is None
        assert f.drift_s is None

    def test_two_clicks(self):
        f = compute_features(make_timing([0.25]))
        assert f.mean_ici_s == pytest.approx(0.25)
        assert f.ici_cv is None
        assert f.npvi is None
        assert f.initial_ici_ratio is None
        assert f.drift_s is None
        assert f.ici_pattern == pytest.approx([1.0])

    def test_three_clicks(self):
        f = compute_features(make_timing([0.2, 0.4]))
        assert f.ici_cv is not None
        assert f.initial_ici_ratio == pytest.approx(0.2 / 0.4)
        assert f.terminal_ici_ratio == pytest.approx(0.4 / 0.2)
        assert f.drift_s == pytest.approx(0.2)
        assert f.npvi is None
        assert f.rubato_slope is None

    def test_audio_fields_not_observable(self):
        f = compute_features(make_timing([0.2, 0.2]))
        assert f.spectral_quality == "not_observable"
        assert f.formants == "not_observable"
        assert f.edge_coarticulation == "not_observable"


@pytest.fixture(scope="module")
def corpus():
    loaded = load_dominica_codas(DOMINICA, qc_mode="permissive")
    extraction = extract_all(loaded, codamd_path=CODAMD)
    features, feature_set = build_feature_set(extraction)
    return extraction, features, feature_set


class TestCorpusFeatures:
    def test_counts(self, corpus):
        _, features, feature_set = corpus
        assert len(features) == 8714
        assert feature_set.n_features == 8714
        # 627 of 628 gate codas carry timing (5092 unjoined upstream).
        assert feature_set.n_gate_partition == 627
        assert len(feature_set.partition_features) == 627

    def test_gate_membership_filter(self, corpus):
        extraction, _, _ = corpus
        members = gate_members(extraction.gate_partition)
        assert len(members) == 627
        for t in members:
            assert t.coda_type == "1+1+3"
            assert t.vowel in ("a", "i")
            assert t.whale_id_raw in {"ATWOOD", "FORK", "PINCHY", "TBB"}

    def test_duration_effect_sign_reproduces(self, corpus):
        """The published a>i duration effect must appear in mean_ici terms."""
        _, _, feature_set = corpus
        contrast = next(
            c for c in feature_set.partition_contrasts if c.feature == "mean_ici_s"
        )
        assert contrast.a_minus_i > 0
        assert contrast.n_whales == 4

    def test_whale_means_cover_all_vowels(self, corpus):
        _, _, feature_set = corpus
        pairs = {(m.whale_id_raw, m.vowel) for m in feature_set.whale_feature_means}
        for whale in ("ATWOOD", "FORK", "PINCHY", "TBB"):
            assert (whale, "a") in pairs
            assert (whale, "i") in pairs

    def test_deterministic_replay(self, corpus):
        extraction, _, _ = corpus
        _, second_set = build_feature_set(extraction)
        _, _, first_set = corpus
        assert first_set.model_dump_json() == second_set.model_dump_json()


class TestAggregates:
    def test_contrast_bootstrap_deterministic(self):
        timings = []
        for i, (whale, vowel, ici) in enumerate(
            [
                ("W1", "a", [0.30, 0.30, 0.30]),
                ("W1", "i", [0.20, 0.20, 0.20]),
                ("W2", "a", [0.32, 0.32, 0.32]),
                ("W2", "i", [0.22, 0.22, 0.22]),
            ]
        ):
            timings.append(make_timing(ici, num=i + 1, whale=whale, vowel=vowel))
        features = [compute_features(t) for t in timings]
        first = partition_contrasts(features, iterations=2000)
        second = partition_contrasts(features, iterations=2000)
        assert [c.model_dump() for c in first] == [c.model_dump() for c in second]
        mean_ici = next(c for c in first if c.feature == "mean_ici_s")
        assert mean_ici.a_minus_i == pytest.approx(0.1)
        assert mean_ici.n_whales == 2

    def test_whale_means_null_handling(self):
        features = [
            compute_features(make_timing([0.2], num=1, whale="W1", vowel="a")),
            compute_features(make_timing([0.4], num=2, whale="W1", vowel="a")),
        ]
        means = whale_feature_means(features)
        assert len(means) == 1
        assert means[0].n == 2
        assert means[0].means["mean_ici_s"] == pytest.approx(0.3)
        assert means[0].means["npvi"] is None
