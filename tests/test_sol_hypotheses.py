from __future__ import annotations

from typing import Any

import pytest

from contracts.models import GateResult, GateState, MixedModelResult, PerWhaleEffect
from interpretation.sol_hypotheses import (
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    HypothesisCandidate,
    HypothesisRun,
    UncertaintyKind,
    generate_hypothesis,
)


class FakeResponses:
    """Mimics `client.responses` for injection into `generate_hypothesis`."""

    def __init__(self, candidate: HypothesisCandidate | None = None) -> None:
        self.candidate = candidate
        self.last_model: str | None = None
        self.last_reasoning: dict[str, str] | None = None
        self.last_instructions: str | None = None
        self.last_input: str | None = None
        self.last_text_format: type | None = None

    def parse(
        self,
        model: str,
        reasoning: dict[str, str],
        instructions: str,
        input: str,
        text_format: type,
    ) -> FakeParsedResponse:
        self.last_model = model
        self.last_reasoning = reasoning
        self.last_instructions = instructions
        self.last_input = input
        self.last_text_format = text_format
        candidate = self.candidate or HypothesisCandidate(
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
        return FakeParsedResponse(candidate)


class _FakeOutputContent:
    def __init__(self, parsed: Any) -> None:
        self.type = "output_text"
        self.parsed = parsed


class _FakeOutputItem:
    def __init__(self, content: Any) -> None:
        self.type = "message"
        self.content = content


class FakeParsedResponse:
    def __init__(self, parsed: Any) -> None:
        self.output = [_FakeOutputItem([_FakeOutputContent(parsed)])]

    @property
    def output_parsed(self) -> Any:
        for item in self.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text" and content.parsed:
                        return content.parsed
        return None


class FakeClient:
    def __init__(self, candidate: HypothesisCandidate | None = None) -> None:
        self.responses = FakeResponses(candidate)


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
    fb = fake.responses
    assert fb.last_model == DEFAULT_MODEL
    assert fb.last_reasoning == {"effort": DEFAULT_REASONING_EFFORT}
    assert fb.last_text_format is HypothesisCandidate
    assert fb.last_instructions is not None
    assert "translation" in fb.last_instructions.casefold()
    assert fb.last_input is not None
    assert "codamd_hash" in fb.last_input
    assert isinstance(result, HypothesisRun)
    assert result.model == DEFAULT_MODEL
    assert result.reasoning_effort == DEFAULT_REASONING_EFFORT


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
    candidate = FakeResponses().parse("", {}, "", "", HypothesisCandidate).output_parsed
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
    parsed = FakeResponses().parse("", {}, "", "", HypothesisCandidate).output_parsed
    payload = parsed.model_dump()
    payload["claim"] = "This coda means danger."

    with pytest.raises(ValueError, match="semantic claims are forbidden"):
        HypothesisCandidate.model_validate(payload)
