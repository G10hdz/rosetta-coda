import hashlib
from pathlib import Path

import pytest

from analysis.reproduce_duration import (
    CODAMD_EXPECTED_HASH,
    FOUR_WHALES,
    run_duration_gate,
    write_gate_result,
)
from contracts.models import GateResult, GateState

CODAMD_PATH = Path("external/phonology-osf-9t6qu/codamd.csv")


class TestGateHash:
    def test_codamd_hash_matches(self):
        h = hashlib.sha256()
        with open(str(CODAMD_PATH), "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        assert (
            h.hexdigest() == CODAMD_EXPECTED_HASH
        ), "codamd.csv hash has drifted from pinned value"

    def test_indeterminate_on_hash_mismatch(self):
        result = run_duration_gate(str(CODAMD_PATH))
        assert result.state in (
            GateState.pass_,
            GateState.fail,
            GateState.indeterminate,
        )

    def test_missing_file_is_indeterminate(self):
        result = run_duration_gate("does-not-exist.csv")
        assert result.state == GateState.indeterminate


@pytest.mark.slow
class TestGateExecution:
    """These tests actually run the MixedLM model (~seconds)."""

    def test_gate_runs(self):
        result = run_duration_gate(str(CODAMD_PATH))
        assert result.codamd_hash == CODAMD_EXPECTED_HASH

    def test_cohort_flow_has_keys(self):
        result = run_duration_gate(str(CODAMD_PATH))
        for key in [
            "total_input",
            "after_handv_filter",
            "after_codatype_filter",
            "after_whale_filter",
            "n_a",
            "n_i",
        ]:
            assert key in result.cohort_flow, f"Missing cohort key: {key}"

    def test_eligible_sample_count(self):
        result = run_duration_gate(str(CODAMD_PATH))
        assert result.cohort_flow.get("after_whale_filter") == 628

    def test_vowel_counts(self):
        result = run_duration_gate(str(CODAMD_PATH))
        assert result.cohort_flow.get("n_a") == 338
        assert result.cohort_flow.get("n_i") == 290

    def test_per_whale_effects_four_whales(self):
        result = run_duration_gate(str(CODAMD_PATH))
        assert len(result.per_whale_effects) == 4
        whale_ids = {pe.whale_id for pe in result.per_whale_effects}
        assert whale_ids == set(FOUR_WHALES)

    def test_per_whale_raw_diffs_positive(self):
        result = run_duration_gate(str(CODAMD_PATH))
        for pe in result.per_whale_effects:
            assert pe.raw_diff_a_minus_i > 0, (
                f"{pe.whale_id}: raw a-i diff = {pe.raw_diff_a_minus_i}, expected > 0"
            )

    def test_mixed_model_present(self):
        result = run_duration_gate(str(CODAMD_PATH))
        assert result.mixed_model is not None
        assert result.mixed_model.n_obs == 628
        assert result.mixed_model.n_groups == 4

    def test_i_coefficient_negative(self):
        result = run_duration_gate(str(CODAMD_PATH))
        assert result.mixed_model is not None
        assert result.mixed_model.coefficient_value < 0, (
            f"i coefficient = {result.mixed_model.coefficient_value}, expected < 0"
        )

    def test_gate_passes_and_persists(self, tmp_path):
        result = run_duration_gate(str(CODAMD_PATH))
        assert result.state == GateState.pass_
        output = tmp_path / "gate.json"
        write_gate_result(result, output)
        restored = GateResult.model_validate_json(output.read_text())
        assert restored == result
