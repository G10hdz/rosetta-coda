"""Smoke test for the local demo site.

Cheap, dependency-free checks that the demo ships its required assets and
keeps its scientific disclaimers intact. This guards against the demo
silently losing the honesty guarantees the project is built on.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO = REPO_ROOT / "demo"
GATE = REPO_ROOT / "artifacts" / "gates" / "spec-004-duration-gate.json"

REQUIRED_ASSETS = ("index.html", "styles.css", "app.js")

# The disclaimers the demo must state prominently and verbatim.
REQUIRED_DISCLAIMERS = (
    "Not a whale translator.",
    "Deterministic science first.",
    "No semantic claims.",
)


@pytest.mark.parametrize("asset", REQUIRED_ASSETS)
def test_demo_asset_present_and_nonempty(asset: str) -> None:
    path = DEMO / asset
    assert path.is_file(), f"missing demo asset: {asset}"
    assert path.stat().st_size > 0, f"empty demo asset: {asset}"


def test_index_states_all_disclaimers() -> None:
    html = (DEMO / "index.html").read_text(encoding="utf-8")
    for phrase in REQUIRED_DISCLAIMERS:
        assert phrase in html, f"disclaimer missing from index.html: {phrase!r}"


def test_index_wires_stylesheet_and_script() -> None:
    html = (DEMO / "index.html").read_text(encoding="utf-8")
    assert 'href="styles.css"' in html
    assert 'src="app.js"' in html


def test_app_loads_real_gate_artifact() -> None:
    app = (DEMO / "app.js").read_text(encoding="utf-8")
    assert "/artifacts/gates/spec-004-duration-gate.json" in app


def test_app_never_labels_the_mock_as_a_sol_output() -> None:
    """The preview mock must be clearly labelled and never implied to be a Sol call."""
    app = (DEMO / "app.js").read_text(encoding="utf-8")
    # The preview origin badge is unmistakably illustrative, not a live call.
    assert 'origin.textContent = "Preview · illustrative"' in app
    # The mock generator must exist and be explicitly illustrative.
    assert "mockHypothesis" in app
    assert "not produced by any model" in app
    # The pinned preview note explicitly denies Sol authorship.
    assert "not</strong> a Sol output" in app
    # The live badge branch must be distinct from the mock branch.
    assert 'origin.dataset.origin = "live"' in app


def test_app_no_inter_click_duration_claim() -> None:
    """The gate measures total coda duration, never 'inter-click duration'."""
    app = (DEMO / "app.js").read_text(encoding="utf-8").lower()
    index = (DEMO / "index.html").read_text(encoding="utf-8").lower()
    assert "inter-click" not in app, "app.js still claims 'inter-click duration'"
    assert "inter-click" not in index, "index.html still claims 'inter-click duration'"


def test_app_has_no_invalid_coda_type_alternative_or_falsifier() -> None:
    """The cohort is frozen to exact coda type 1+1+3; alternatives/falsifiers must
    not propose adding/including coda type (or click count) as a covariate."""
    app = (DEMO / "app.js").read_text(encoding="utf-8").lower()
    forbidden = (
        "coda type is added",
        "adding coda type",
        "add coda type",
        "coda type as a fixed effect",
        "including coda type",
        "click count",
    )
    for phrase in forbidden:
        assert phrase not in app, f"invalid coda-type alternative/falsifier: {phrase!r}"


def test_app_distinguishes_raw_coefficient_from_standardized_effect() -> None:
    """The raw-seconds mixed-model coefficient must never be presented as a
    standardized effect; the per-whale bars are the standardized quantity."""
    app = (DEMO / "app.js").read_text(encoding="utf-8")
    index = (DEMO / "index.html").read_text(encoding="utf-8")
    # The mock claim frames the coefficient explicitly as raw seconds.
    assert ("raw −0.132 s" in app) or ("raw -0.132 s" in app)
    # The mixed-model panel labels the coefficient as raw seconds, not normalized.
    assert "not a standardized effect" in index
    # The per-whale panel labels its bars as z-scored / standardized.
    assert "z-scored" in index
    assert "standardized" in index


def test_no_live_sol_artifact_is_fetched_without_a_manifest_flag() -> None:
    """The offline Preview path consults the manifest and does not fetch the live
    Sol artifact (which would 404 in the console) unless it is declared present."""
    app = (DEMO / "app.js").read_text(encoding="utf-8")
    assert "MANIFEST_URL" in app
    assert "sol_hypothesis_available" in app
    manifest = REPO_ROOT / "artifacts" / "demo" / "manifest.json"
    assert manifest.is_file(), "demo manifest missing — Preview path would 404"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["sol_hypothesis_available"] is False


def test_no_google_fonts_network_dependency() -> None:
    """The demo must work offline: no external font/network dependency."""
    index = (DEMO / "index.html").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in index
    assert "fonts.gstatic.com" not in index


def test_gate_artifact_shape_matches_visualisation() -> None:
    """The demo assumes a specific evidence shape; assert the artifact honours it."""
    if not GATE.is_file():
        pytest.skip("gate artifact not present in this checkout")
    gate = json.loads(GATE.read_text(encoding="utf-8"))

    assert gate["state"] == "pass"
    assert len(gate["codamd_hash"]) == 64

    cf = gate["cohort_flow"]
    assert cf["n_a"] + cf["n_i"] == cf["after_whale_filter"] == gate["mixed_model"]["n_obs"]

    effects = gate["per_whale_effects"]
    assert len(effects) == gate["mixed_model"]["n_groups"]
    # Every within-whale a-i normalized effect is positive (a longer than i).
    assert all(e["z_diff_a_minus_i"] > 0 for e in effects)


def test_mock_evidence_refs_resolve_against_real_gate() -> None:
    """Every JSON Pointer the mock cites must exist in the frozen artifact."""
    if not GATE.is_file():
        pytest.skip("gate artifact not present in this checkout")
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    app = (DEMO / "app.js").read_text(encoding="utf-8")

    # Pull the evidence_refs array literal out of mockHypothesis().
    import re

    block = re.search(r"evidence_refs:\s*\[(.*?)\]", app, flags=re.DOTALL)
    assert block, "could not locate mock evidence_refs in app.js"
    refs = re.findall(r'"(/[^"]+)"', block.group(1))
    assert refs, "no JSON Pointer refs found in mock"

    for pointer in refs:
        node = gate
        for raw in pointer.lstrip("/").split("/"):
            key = raw.replace("~1", "/").replace("~0", "~")
            node = node[int(key)] if isinstance(node, list) else node[key]
        assert node is not None, f"pointer resolved to null: {pointer}"
