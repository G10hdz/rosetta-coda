from __future__ import annotations

import json
import os
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from contracts.models import GateResult, GateState

# OpenAI-compatible default (DeepSeek). Override with ROSETTA_MODEL / ROSETTA_BASE_URL.
DEFAULT_MODEL = os.environ.get("ROSETTA_MODEL", "deepseek-chat")
# Empty = provider default. deepseek-chat exposes no reasoning knob.
DEFAULT_REASONING_EFFORT = os.environ.get("ROSETTA_REASONING_EFFORT", "")
DEFAULT_BASE_URL = os.environ.get("ROSETTA_BASE_URL", "https://api.deepseek.com")

INSTRUCTIONS = """You are the hypothesis stage of a scientific instrument.
Propose exactly one falsifiable phonological hypothesis using only the supplied,
frozen gate artifact. This is not whale-language translation: never claim
meaning, intent, words, messages, or semantic content. Distinguish observations
from hypotheses. Cite evidence only as exact JSON Pointer paths that exist in
the supplied artifact. Include plausible alternatives, decisive falsifiers,
uncertainty, and limitations. Do not invent measurements or external facts."""

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


_SCHEMA_INSTRUCTIONS = (
    "Reply with a single JSON object that validates against this JSON Schema. "
    "No prose, no markdown fences.\n"
    + json.dumps(HypothesisCandidate.model_json_schema(), sort_keys=True)
)


class HypothesisRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.1.0"
    model: str
    reasoning_effort: str = ""
    source_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gate_state: GateState
    hypothesis: HypothesisCandidate


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


def _validate_evidence_refs(candidate: HypothesisCandidate, artifact: dict[str, Any]) -> None:
    for pointer in candidate.evidence_refs:
        try:
            _resolve_json_pointer(artifact, pointer)
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"evidence reference does not exist: {pointer}") from exc


def generate_hypothesis(
    gate: GateResult,
    *,
    source_artifact_sha256: str,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> HypothesisRun:
    if gate.state != GateState.pass_:
        raise ValueError("hypothesis generation requires a passing scientific gate")

    artifact = gate.model_dump(mode="json")
    if client is None:
        from openai import OpenAI

        # ponytail: OpenAI SDK as generic OpenAI-compat client (DeepSeek/OR/Ollama).
        api_key = os.environ.get("ROSETTA_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("ROSETTA_BASE_URL", DEFAULT_BASE_URL)
        api_client = OpenAI(api_key=api_key, base_url=base_url or None)
    else:
        api_client = client
    # DeepSeek and most OpenAI-compatible servers only serve /chat/completions
    # with json_object mode, so the schema travels in the prompt and Pydantic
    # does the enforcing.
    response = api_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": f"{INSTRUCTIONS}\n\n{_SCHEMA_INSTRUCTIONS}"},
            {"role": "user", "content": json.dumps(artifact, indent=2, sort_keys=True)},
        ],
        response_format={"type": "json_object"},
        **({"reasoning_effort": reasoning_effort} if reasoning_effort else {}),
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("model returned no structured hypothesis")

    candidate = HypothesisCandidate.model_validate_json(content)
    _validate_evidence_refs(candidate, artifact)
    return HypothesisRun(
        model=model,
        reasoning_effort=reasoning_effort,
        source_artifact_sha256=source_artifact_sha256,
        gate_state=gate.state,
        hypothesis=candidate,
    )
