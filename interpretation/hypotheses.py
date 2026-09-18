from __future__ import annotations

import hashlib
import json
import os
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from contracts.models import (
    AnalystEvidence,
    FeatureSet,
    GateResult,
    GateState,
    ModelCallRecord,
)

# OpenAI-compatible default (DeepSeek). Override with ROSETTA_MODEL / ROSETTA_BASE_URL.
DEFAULT_MODEL = os.environ.get("ROSETTA_MODEL", "deepseek-chat")
# Empty = provider default. deepseek-chat exposes no reasoning knob.
DEFAULT_REASONING_EFFORT = os.environ.get("ROSETTA_REASONING_EFFORT", "")
DEFAULT_BASE_URL = os.environ.get("ROSETTA_BASE_URL", "https://api.deepseek.com")

INSTRUCTIONS = """You are the hypothesis stage of a scientific instrument.
Propose falsifiable phonological hypotheses using only the supplied, frozen
evidence document. This is not whale-language translation: never claim
meaning, intent, words, messages, or semantic content. Distinguish observations
from hypotheses. Cite evidence only as exact JSON Pointer paths that exist in
the supplied document. Include plausible alternatives, decisive falsifiers,
uncertainty, and limitations. Do not invent measurements or external facts."""

_EVIDENCE_CONTEXT = (
    "The evidence document is an analyst evidence bundle: `gate` holds the "
    "frozen SPEC-004 reproduction-gate artifact, `partition_contrasts` the "
    "bootstrapped a-i feature contrasts, `whale_feature_means` per-whale "
    "aggregates, and `feature_records_sample` a deterministic sample of "
    "per-coda feature records."
)

_SEMANTIC_CLAIM_PATTERNS = (
    r"\b(?:whale|coda)s?\s+(?:mean|means|communicate|communicates|say|says)\b",
    r"\btranslates?\s+(?:as|to)\b",
    r"\bword\s+for\b",
    r"\bmessage\s+(?:is|that)\b",
    r"\bintent\s+(?:is|was)\b",
)


class UncertaintyKind(str, Enum):
    sampling = "sampling"
    model = "model"
    measurement = "measurement"
    epistemic = "epistemic"


class HypothesisCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    claim: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    uncertainty_kind: UncertaintyKind
    alternatives: list[str] = Field(min_length=1)
    falsifiers: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)

    @field_validator("title", "claim", "alternatives", "falsifiers", "limitations")
    @classmethod
    def reject_semantic_claims(cls, value: str | list[str]) -> str | list[str]:
        text = value if isinstance(value, str) else " ".join(value)
        if any(
            re.search(pattern, text, flags=re.IGNORECASE) for pattern in _SEMANTIC_CLAIM_PATTERNS
        ):
            raise ValueError("semantic claims are forbidden")
        return value

    @field_validator("evidence_refs")
    @classmethod
    def require_json_pointers(cls, value: list[str]) -> list[str]:
        if any(not ref.startswith("/") for ref in value):
            raise ValueError("evidence references must be JSON Pointer paths")
        return value


class CandidateSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypotheses: list[HypothesisCandidate] = Field(min_length=1)


class HypothesisRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.1.0"
    model: str
    reasoning_effort: str = ""
    source_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gate_state: GateState
    hypothesis: HypothesisCandidate


def _schema_instructions(schema: dict[str, Any]) -> str:
    return (
        "Reply with a single JSON object that validates against this JSON Schema. "
        "No prose, no markdown fences.\n" + json.dumps(schema, sort_keys=True)
    )


def _resolve_json_pointer(document: Any, pointer: str) -> Any:
    current = document
    for raw_part in pointer.removeprefix("/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(pointer)
    return current


def _validate_evidence_refs(candidate: HypothesisCandidate, document: dict[str, Any]) -> None:
    for pointer in candidate.evidence_refs:
        try:
            _resolve_json_pointer(document, pointer)
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"evidence reference does not exist: {pointer}") from exc


def _default_client() -> Any:
    from openai import OpenAI

    # OpenAI SDK as generic OpenAI-compat client (DeepSeek/OR/Ollama).
    api_key = os.environ.get("ROSETTA_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("ROSETTA_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=api_key, base_url=base_url or None)


def _structured_call(
    document: dict[str, Any],
    instructions: str,
    response_schema: dict[str, Any],
    *,
    call_id: str,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> tuple[Any, ModelCallRecord]:
    """One structured model call with a single schema-repair retry."""
    api_client = client if client is not None else _default_client()
    system = f"{instructions}\n\n{_schema_instructions(response_schema)}"
    payload = json.dumps(document, indent=2, sort_keys=True)
    params = {"model": model, "reasoning_effort": reasoning_effort, "format": "json_object"}
    request_hash = hashlib.sha256(
        json.dumps({"system": system, "user": payload}, sort_keys=True).encode()
    ).hexdigest()

    parsed: Any = None
    last_error: Exception | None = None
    response = None
    for attempt in range(2):
        messages = [{"role": "system", "content": system}]
        if attempt == 0:
            messages.append({"role": "user", "content": payload})
        else:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Your previous reply failed schema validation: {last_error}. "
                        "Return only a corrected JSON object.\n" + payload
                    ),
                }
            )
        response = api_client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            **({"reasoning_effort": reasoning_effort} if reasoning_effort else {}),
        )
        content = response.choices[0].message.content
        if not content:
            last_error = RuntimeError("model returned empty content")
            continue
        try:
            parsed = json.loads(content)
            last_error = None
            break
        except json.JSONDecodeError as exc:
            last_error = exc
    if last_error is not None or parsed is None or response is None:
        raise RuntimeError(f"model returned no schema-valid JSON: {last_error}")

    usage = getattr(response, "usage", None)
    record = ModelCallRecord(
        call_id=call_id,
        model=model,
        reasoning_effort=reasoning_effort,
        params_hash=hashlib.sha256(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest(),
        request_sha256=request_hash,
        response=parsed,
        usage={
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        },
        cache_key=hashlib.sha256(
            f"{model}|{json.dumps(params, sort_keys=True)}|{request_hash}".encode()
        ).hexdigest(),
    )
    return parsed, record


def generate_hypothesis(
    gate: GateResult,
    *,
    source_artifact_sha256: str,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> HypothesisRun:
    """Single-candidate hypothesis over the bare gate artifact (demo path)."""
    if gate.state != GateState.pass_:
        raise ValueError("hypothesis generation requires a passing scientific gate")

    document = gate.model_dump(mode="json")
    instructions = (
        "Propose exactly one falsifiable hypothesis.\n"
        + INSTRUCTIONS.replace("hypotheses", "hypothesis", 1)
    )
    parsed, _record = _structured_call(
        document,
        instructions,
        HypothesisCandidate.model_json_schema(),
        call_id="call-0001",
        client=client,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    candidate = HypothesisCandidate.model_validate(parsed)
    _validate_evidence_refs(candidate, document)
    return HypothesisRun(
        model=model,
        reasoning_effort=reasoning_effort,
        source_artifact_sha256=source_artifact_sha256,
        gate_state=gate.state,
        hypothesis=candidate,
    )


def build_analyst_evidence(
    gate: GateResult,
    feature_set: FeatureSet,
    *,
    sample_size: int = 60,
    evidence_manifest: dict[str, str] | None = None,
) -> AnalystEvidence:
    """Freeze the evidence bundle handed to the analyst model."""
    if gate.state != GateState.pass_:
        raise ValueError("analyst evidence requires a passing scientific gate")
    sample = sorted(feature_set.partition_features, key=lambda f: f.coda_id)[
        :sample_size
    ]
    notes: list[str] = []
    for name in ("spectral_quality", "formants", "edge_coarticulation"):
        notes.append(f"{name}: not_observable (no WAV input in this run)")
    return AnalystEvidence(
        gate=gate,
        partition_contrasts=feature_set.partition_contrasts,
        whale_feature_means=feature_set.whale_feature_means,
        feature_records_sample=sample,
        evidence_manifest=evidence_manifest or {},
        notes=notes,
    )


def generate_evidence_hypothesis(
    evidence: AnalystEvidence,
    *,
    evidence_sha256: str,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> tuple[HypothesisRun, ModelCallRecord]:
    """Single-candidate hypothesis over the full evidence bundle."""
    if evidence.gate.state != GateState.pass_:
        raise ValueError("hypothesis generation requires a passing scientific gate")

    document = evidence.model_dump(mode="json")
    instructions = f"{INSTRUCTIONS}\n{_EVIDENCE_CONTEXT}\nPropose exactly one hypothesis."
    parsed, record = _structured_call(
        document,
        instructions,
        HypothesisCandidate.model_json_schema(),
        call_id="call-0001",
        client=client,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    candidate = HypothesisCandidate.model_validate(parsed)
    _validate_evidence_refs(candidate, document)
    run = HypothesisRun(
        model=model,
        reasoning_effort=reasoning_effort,
        source_artifact_sha256=evidence_sha256,
        gate_state=evidence.gate.state,
        hypothesis=candidate,
    )
    return run, record


def generate_candidates(
    evidence: AnalystEvidence,
    k: int = 3,
    *,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> tuple[list[HypothesisCandidate], list[ModelCallRecord]]:
    """List-mode call producing up to k distinct validated candidates."""
    if evidence.gate.state != GateState.pass_:
        raise ValueError("hypothesis generation requires a passing scientific gate")

    document = evidence.model_dump(mode="json")
    instructions = (
        f"{INSTRUCTIONS}\n{_EVIDENCE_CONTEXT}\n"
        f"Propose up to {k} DISTINCT hypotheses in one JSON object "
        '{"hypotheses": [...]}. Each must differ in claim or evidence.'
    )
    parsed, record = _structured_call(
        document,
        instructions,
        CandidateSet.model_json_schema(),
        call_id="call-0001",
        client=client,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    candidate_set = CandidateSet.model_validate(parsed)

    seen: set[str] = set()
    valid: list[HypothesisCandidate] = []
    for candidate in candidate_set.hypotheses:
        if candidate.claim in seen:
            continue
        _validate_evidence_refs(candidate, document)
        seen.add(candidate.claim)
        valid.append(candidate)
    return valid[:k], [record]


__all__ = [
    "HypothesisCandidate",
    "HypothesisRun",
    "UncertaintyKind",
    "build_analyst_evidence",
    "generate_candidates",
    "generate_evidence_hypothesis",
    "generate_hypothesis",
]
