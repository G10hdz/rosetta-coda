import random
import wave
from array import array

import pytest

from contracts.models import DetectionState
from detector import DETECTOR_VERSION, DetectorParams, detect

SAMPLE_RATE = 16000
BURST_SAMPLES = 32  # ~2 ms
BURST_AMPLITUDE = 20000
NOISE_SD = 500
ONE_SAMPLE_S = 1.0 / SAMPLE_RATE

CODA1 = [0.05, 0.26]
CODA2 = [1.05, 1.20, 1.40]
CLICKS = CODA1 + CODA2


def write_wav(path, samples, channels=1):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(array("h", samples).tobytes())


def synth_samples(clicks, duration_s=2.0, seed=1234):
    rng = random.Random(seed)
    n = int(duration_s * SAMPLE_RATE)
    samples = [int(rng.gauss(0, NOISE_SD)) for _ in range(n)]
    for t in clicks:
        center = round(t * SAMPLE_RATE)
        for i in range(center - BURST_SAMPLES // 2, center + BURST_SAMPLES // 2):
            samples[i] = BURST_AMPLITUDE
    return samples


@pytest.fixture()
def two_coda_wav(tmp_path):
    path = tmp_path / "two_codas.wav"
    write_wav(path, synth_samples(CLICKS))
    return path


class TestRecovery:
    def test_recovers_known_click_times(self, two_coda_wav):
        params = DetectorParams(max_ici_s=0.5)
        result = detect(two_coda_wav, params)

        assert result.state == DetectionState.detected
        assert result.detector_version == DETECTOR_VERSION
        assert result.metrics.n_codas == 2
        assert result.metrics.n_clicks == len(CLICKS)
        assert result.metrics.parity == "unverified"
        assert [d.coda_id for d in result.detections] == ["wav:0", "wav:1"]

        expected = [
            [t - CODA1[0] for t in CODA1],
            [t - CODA2[0] for t in CODA2],
        ]
        for detection, times in zip(result.detections, expected):
            assert detection.click_count == len(times)
            assert detection.click_times_s[0] == 0.0
            for got, want in zip(detection.click_times_s, times):
                assert abs(got - want) <= ONE_SAMPLE_S

    def test_source_hash_and_params_hash_present(self, two_coda_wav):
        result = detect(two_coda_wav)
        assert len(result.source_wav_sha256) == 64
        assert result.params_hash == DetectorParams().params_hash()


class TestGrouping:
    def test_gap_above_max_ici_splits_codas(self, two_coda_wav):
        params = DetectorParams(max_ici_s=0.18)
        result = detect(two_coda_wav, params)

        assert result.state == DetectionState.detected
        assert [d.click_count for d in result.detections] == [1, 1, 2, 1]
        assert result.metrics.n_codas == 4

    def test_gap_below_max_ici_merges(self, two_coda_wav):
        params = DetectorParams(max_ici_s=2.0)
        result = detect(two_coda_wav, params)

        assert result.metrics.n_codas == 1
        assert result.detections[0].click_count == len(CLICKS)


class TestNotObservable:
    def test_missing_file(self, tmp_path):
        result = detect(tmp_path / "does-not-exist.wav")
        assert result.state == DetectionState.not_observable
        assert result.detections == []
        assert result.source_wav_sha256 is None

    def test_no_path(self):
        result = detect(None)
        assert result.state == DetectionState.not_observable

    def test_non_wav_file(self, tmp_path):
        path = tmp_path / "not-audio.wav"
        path.write_bytes(b"this is not a wav file")
        result = detect(path)
        assert result.state == DetectionState.not_observable


class TestFailed:
    def test_stereo_wav_is_failed(self, tmp_path):
        path = tmp_path / "stereo.wav"
        write_wav(path, synth_samples(CLICKS), channels=2)
        result = detect(path)
        assert result.state == DetectionState.failed
        assert result.error is not None


class TestNoiseOnly:
    def test_noise_only_yields_detected_with_zero_detections(self, tmp_path):
        path = tmp_path / "noise.wav"
        write_wav(path, synth_samples([], seed=99))
        result = detect(path)

        assert result.state == DetectionState.detected
        assert result.detections == []
        assert result.metrics.n_clicks == 0
        assert result.metrics.n_codas == 0


class TestDeterminism:
    def test_identical_artifact_except_created_at(self, two_coda_wav):
        params = DetectorParams(max_ici_s=0.5)
        first = detect(two_coda_wav, params)
        second = detect(two_coda_wav, params)

        assert first.model_dump(exclude={"created_at"}) == second.model_dump(
            exclude={"created_at"}
        )
        assert first.model_dump_json(exclude={"created_at"}) == second.model_dump_json(
            exclude={"created_at"}
        )

    def test_params_hash_tracks_params(self):
        assert DetectorParams().params_hash() == DetectorParams().params_hash()
        assert DetectorParams().params_hash() != DetectorParams(threshold_k=8.0).params_hash()
