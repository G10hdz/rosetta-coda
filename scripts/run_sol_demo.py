from __future__ import annotations

import argparse
from pathlib import Path

from contracts.models import GateResult
from interpretation.sol_hypotheses import generate_hypothesis
from storage.io import sha256_file, write_json_atomic

DEFAULT_GATE = Path("artifacts/gates/spec-004-duration-gate.json")
DEFAULT_OUTPUT = Path("artifacts/demo/sol-hypothesis.json")


def run_sol_demo(
    gate_path: Path = DEFAULT_GATE,
    output_path: Path = DEFAULT_OUTPUT,
) -> int:
    gate_dict = GateResult.model_validate_json(gate_path.read_text())
    source_hash = sha256_file(str(gate_path))
    result = generate_hypothesis(gate_dict, source_artifact_sha256=source_hash)
    written = write_json_atomic(result, output_path)
    gate_fp = source_hash[:12]
    out_fp = sha256_file(written)[:12]
    h = result.hypothesis
    print(f"Sol hypothesis written to {written}")
    print(f"  gate     {gate_fp}")
    print(f"  output   {out_fp}")
    print(f"  title    {h.title}")
    print(f"  claim    {h.claim}")
    print(f"  evidence  {len(h.evidence_refs)} refs")
    print(f"  uncert.  {h.uncertainty_kind.value}")
    print(f"  alts     {len(h.alternatives)}")
    print(f"  falsif.  {len(h.falsifiers)}")
    print(f"  limits   {len(h.limitations)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a GPT-5.6 Sol phonological hypothesis from a gate artifact."
    )
    parser.add_argument(
        "--gate",
        type=Path,
        default=DEFAULT_GATE,
        help=f"Gate artifact path (default: {DEFAULT_GATE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    return run_sol_demo(args.gate, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
