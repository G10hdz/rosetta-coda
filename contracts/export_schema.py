from __future__ import annotations

import json
from pathlib import Path

from contracts.models import (
    CodaRecord,
    GateResult,
    LoadResult,
    MixedModelResult,
    NormalizationResult,
    NormalizedCoda,
    PerWhaleEffect,
    QuarantinedRow,
    WhaleBaseline,
)

MODELS = (
    CodaRecord,
    QuarantinedRow,
    LoadResult,
    WhaleBaseline,
    NormalizedCoda,
    NormalizationResult,
    PerWhaleEffect,
    MixedModelResult,
    GateResult,
)


def export_schema(output: str | Path = "contracts/schema-0.1.0.json") -> Path:
    target = Path(output)
    payload = {
        "schema_version": "0.1.0",
        "models": {model.__name__: model.model_json_schema() for model in MODELS},
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


if __name__ == "__main__":
    export_schema()
