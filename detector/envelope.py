from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field

from contracts.models import (
    CodaDetection,
    DetectionMetrics,
    DetectionResult,
    DetectionState,
)

DETECTOR_VERSION = "energy-envelope-v1"


class DetectorParams(BaseModel):
    envelope_window_s: float = Field(default=0.001, gt=0)
    threshold_k: float = Field(default=6.0, gt=0)
    refractory_s: float = Field(default=0.003, gt=0)
    max_ici_s: float = Field(default=1.0, gt=0)

    def params_hash(self) -> str:
        canonical = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


class _UnsupportedWavError(Exception):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1:
            raise _UnsupportedWavError(f"expected mono WAV, got {wav.getnchannels()} channels")
        if wav.getsampwidth() != 2:
            raise _UnsupportedWavError(f"expected 16-bit PCM, got {wav.getsampwidth() * 8}-bit")
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float64), sample_rate


def _envelope(samples: np.ndarray, window_samples: int) -> np.ndarray:
    kernel = np.ones(window_samples) / window_samples
    return np.convolve(np.abs(samples), kernel, mode="same")


def _peak_positions(env: np.ndarray, threshold: float) -> list[float]:
    above = env > threshold
    if not above.any():
        return []
    edges = np.diff(np.concatenate(([False], above, [False])).astype(np.int8))
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0]
    peaks = []
    for start, end in zip(starts.tolist(), ends.tolist()):
        weights = env[start:end] - threshold
        peaks.append(float(np.dot(np.arange(start, end), weights) / weights.sum()))
    return peaks


def _apply_refractory(peaks: list[float], env: np.ndarray, refractory_samples: float) -> list[float]:
    merged: list[float] = []
    last = len(env) - 1
    for peak in peaks:
        if merged and peak - merged[-1] < refractory_samples:
            if env[min(int(round(peak)), last)] > env[min(int(round(merged[-1])), last)]:
                merged[-1] = peak
        else:
            merged.append(peak)
    return merged


def _group_codas(times_s: list[float], max_ici_s: float) -> list[list[float]]:
    groups: list[list[float]] = [[times_s[0]]]
    for prev, current in zip(times_s, times_s[1:]):
        if current - prev > max_ici_s:
            groups.append([])
        groups[-1].append(current)
    return groups


def _result(
    state: DetectionState,
    params_hash: str,
    source_wav_sha256: str | None = None,
    detections: list[CodaDetection] | None = None,
    error: str | None = None,
) -> DetectionResult:
    detections = detections or []
    return DetectionResult(
        state=state,
        detector_version=DETECTOR_VERSION,
        params_hash=params_hash,
        source_wav_sha256=source_wav_sha256,
        detections=detections,
        metrics=DetectionMetrics(
            n_clicks=sum(d.click_count for d in detections),
            n_codas=len(detections),
        ),
        error=error,
    )


def detect(path: str | Path | None, params: DetectorParams | None = None) -> DetectionResult:
    params = params or DetectorParams()
    params_hash = params.params_hash()

    if path is None or not Path(path).is_file():
        return _result(DetectionState.not_observable, params_hash)
    wav_path = Path(path)
    digest = _sha256(wav_path)

    try:
        samples, sample_rate = _read_wav(wav_path)
    except _UnsupportedWavError as exc:
        return _result(DetectionState.failed, params_hash, digest, error=str(exc))
    except (wave.Error, EOFError, OSError):
        return _result(DetectionState.not_observable, params_hash)

    window_samples = max(1, int(round(params.envelope_window_s * sample_rate)))
    env = _envelope(samples, window_samples)

    floor = float(np.median(env))
    sigma = float(1.4826 * np.median(np.abs(env - floor)))
    threshold = floor + params.threshold_k * sigma

    peaks = _peak_positions(env, threshold)
    peaks = _apply_refractory(peaks, env, params.refractory_s * sample_rate)
    if not peaks:
        return _result(DetectionState.detected, params_hash, digest)

    times_s = [peak / sample_rate for peak in peaks]
    groups = _group_codas(times_s, params.max_ici_s)
    detections = [
        CodaDetection(
            coda_id=f"wav:{idx}",
            click_times_s=[t - group[0] for t in group],
            click_count=len(group),
        )
        for idx, group in enumerate(groups)
    ]
    return _result(DetectionState.detected, params_hash, digest, detections)


__all__ = ["DETECTOR_VERSION", "DetectorParams", "detect"]
