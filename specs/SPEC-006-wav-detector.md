# SPEC-006 — Optional Python WAV detector

Status: Accepted — parity verification blocked on unavailable reference data  
Owner: Engineering  
Depends on: SPEC-005

## Outcome

Detect clicks and group them into codas from an optional WAV input so that
audio-derived timing uses the same canonical contracts as metadata timing;
when no WAV is supplied, audio-dependent outputs return `not_observable`.

## Scope

Included:

- `detector` module: WAV read (stdlib `wave`, mono PCM 16-bit), energy
  envelope, threshold peak picking with refractory period, coda grouping by
  inter-click gap.
- `DetectionResult` artifact with explicit `state` field:
  `detected | not_observable | failed`.
- Synthetic-WAV golden tests (generated fixtures, known click times).

Excluded:

- Parity against published MATLAB examples: no MATLAB code or reference
  detections exist under `external/`; this acceptance item is **blocked**, not
  silently passed.
- Spectral/formant measurement.
- Real-time or multi-channel processing.

## Input contract

- Optional path to a PCM WAV file plus a versioned parameter set
  (envelope window, threshold k over noise floor, refractory_s,
  max_ici_s for grouping). Parameter hash is stored in the artifact.
- Absent or unreadable input → `state = not_observable`, never an exception
  into the pipeline.

## Output contract

`DetectionResult`:

```json
{
  "state": "detected",
  "detector_version": "energy-envelope-v1",
  "params_hash": "...",
  "source_wav_sha256": "...",
  "detections": [
    {"coda_id": "wav:0", "click_times_s": [0.0, 0.21], "click_count": 2}
  ],
  "metrics": {"n_clicks": 2, "n_codas": 1, "parity": "unverified"}
}
```

Detected codas convert to `CodaTiming` with `source = "detector"`; the
`parity: unverified` label travels in every artifact until reference examples
exist.

## Invariants

1. No WAV input ⇒ `not_observable`; downstream feature fields dependent on
   audio remain `not_observable`.
2. Detector output never overrides metadata timing for the same coda.
3. Deterministic: same WAV + params ⇒ identical artifact hash.

## Acceptance criteria

- [ ] Synthetic WAV with known click times recovers times within one sample.
- [ ] Grouping splits codas at gaps > `max_ici_s`.
- [ ] `not_observable` path covered by test.
- [ ] Parity suite: blocked — documented in artifact and spec status.

## Stop conditions

WAV decode failure returns `failed` for the detection artifact only; the
metadata pipeline is unaffected.
