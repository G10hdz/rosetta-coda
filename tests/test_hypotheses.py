from __future__ import annotations

from typing import Any

import pytest

from contracts.models import GateResult, GateState, MixedModelResult, PerWhaleEffect
from interpretation.hypotheses import (
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    HypothesisCandidate,
    HypothesisRun,
    UncertaintyKind,
    generate_hypothesis,
)


def default_candidate() -> HypothesisCandidate:
    return HypothesisCandidate(
        title="Replicable a/i duration contrast",
        claim="The observed duration contrast will replicate in a held-out cohort.",
        evidence_refs=[
            "/cohort_flow/after_whale_filter",
            "/per_whale_effects/0/raw_diff_a_minus_i",
        ],
        uncertainty_kind=UncertaintyKind.epistemic,
        alternatives=["Random timing variation cannot be excluded at p<0.001."],
        falsifiers=["A replication with >4 whales showing no effect."],
        limitations=["Limited to four whales from a single population."],
    )


class FakeCompletions:
    """Mimics `client.chat.completions` for injection into `generate_hypothesis`."""

    def __init__(self, candidate: HypothesisCandidate | None = None) -> None:
        self.candidate = candidate
        self.last_model: str | None = None
        self.last_messages: list[dict[str, str]] | None = None
        self.last_response_format: dict[str, str] | None = None
        self.last_kwargs: dict[str, Any] = {}

    def create(
        self,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, str],
        **kwargs: Any,
    ) -> FakeCompletion:
        self.last_model = model
        self.last_messages = messages
        self.last_response_format = response_format
        self.last_kwargs = kwargs
        candidate = self.candidate or default_candidate()
        return FakeCompletion(candidate.model_dump_json())


class _FakeMessage:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str | None) -> None:
        self.message = _FakeMessage(content)


class FakeCompletion:
    def __init__(self, content: str | None) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeChat:
    def __init__(self, completions: FakeCompletions) -> None:
        self.completions = completions


class FakeClient:
    def __init__(self, candidate: HypothesisCandidate | None = None) -> None:
        self.chat = _FakeChat(FakeCompletions(candidate))


PASS_GATE = GateResult(
    state=GateState.pass_,
    summary="All criteria met.",
    codamd_hash="e3fc6b402eeafa94a168ed215255255ed3d3acbeef2d65abe54312526b42a899",
    cohort_flow={
        "total_input": 1375,
        "after_handv_filter": 1142,
        "after_codatype_filter": 709,
        "after_whale_filter": 628,
        "n_a": 338,
        "n_i": 290,
    },
    per_whale_effects=[
        PerWhaleEffect(
            whale_id="ATWOOD",
            n_a=132,
            n_i=128,
            raw_mean_a=1.101,
            raw_mean_i=0.953,
            raw_diff_a_minus_i=0.148,
        ),
    ],
    mixed_model=MixedModelResult(
        coefficient_label="vowel_code (i=1, a=0)",
        coefficient_value=-0.132,
        t_value=-6.614,
        p_value=3.74e-11,
        converged=True,
        n_obs=628,
        n_groups=4,
    ),
)


def test_fake_client_proves_exact_call():
    fake = FakeClient()
    result = generate_hypothesis(
        PASS_GATE,
        source_artifact_sha256="ab" * 32,
        client=fake,
    )
    fc = fake.chat.completions
    assert fc.last_model == DEFAULT_MODEL
    assert fc.last_response_format == {"type": "json_object"}
    assert fc.last_kwargs == {}
    assert fc.last_messages is not None
    system, user = fc.last_messages
    assert "translation" in system["content"].casefold()
    assert "json schema" in system["content"].casefold()
    assert "codamd_hash" in user["content"]
    assert isinstance(result, HypothesisRun)
    assert result.model == DEFAULT_MODEL
    assert result.reasoning_effort == DEFAULT_REASONING_EFFORT


def test_reasoning_effort_forwarded_only_when_set():
    fake = FakeClient()
    result = generate_hypothesis(
        PASS_GATE,
        source_artifact_sha256="ab" * 32,
        client=fake,
        reasoning_effort="medium",
    )
    assert fake.chat.completions.last_kwargs == {"reasoning_effort": "medium"}
    assert result.reasoning_effort == "medium"


@pytest.mark.parametrize("state", [GateState.fail, GateState.indeterminate])
def test_non_pass_gate_raises(state: GateState):
    gate = GateResult(
        state=state,
        summary="failed",
        codamd_hash="abc",
        cohort_flow={},
        per_whale_effects=[],
    )
    with pytest.raises(ValueError, match="requires a passing scientific gate"):
        generate_hypothesis(gate, source_artifact_sha256="ab" * 32, client=FakeClient())


def test_source_hash_propagated():
    fake = FakeClient()
    result = generate_hypothesis(
        PASS_GATE,
        source_artifact_sha256="ff" * 32,
        client=fake,
    )
    assert result.source_artifact_sha256 == "ff" * 32


def test_hypothesis_shape():
    fake = FakeClient()
    result = generate_hypothesis(
        PASS_GATE,
        source_artifact_sha256="ab" * 32,
        client=fake,
    )
    h = result.hypothesis
    assert h.title
    assert h.claim
    assert len(h.evidence_refs) >= 1
    assert all(ref.startswith("/") for ref in h.evidence_refs)
    assert len(h.alternatives) >= 1
    assert len(h.falsifiers) >= 1
    assert len(h.limitations) >= 1


def test_unknown_evidence_pointer_is_rejected():
    candidate = default_candidate()
    payload = candidate.model_dump()
    payload["evidence_refs"] = ["/invented/value"]
    fake = FakeClient(HypothesisCandidate.model_validate(payload))

    with pytest.raises(ValueError, match="evidence reference does not exist"):
        generate_hypothesis(
            PASS_GATE,
            source_artifact_sha256="ab" * 32,
            client=fake,
        )


def test_semantic_claim_is_rejected():
    parsed = default_candidate()
    payload = parsed.model_dump()
    payload["claim"] = "This coda means danger."

    with pytest.raises(ValueError, match="semantic claims are forbidden"):
        HypothesisCandidate.model_validate(payload)
