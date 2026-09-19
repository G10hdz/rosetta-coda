"""Smoke test for the public research console.

Guards the deploy footgun that made `/research` (no trailing slash) 404 its
CSS and JS, and the `.vercelignore` `*.md` rule that dropped the citable report.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RESEARCH = REPO_ROOT / "research"
RELEASE = REPO_ROOT / "artifacts" / "release"


def test_research_assets_present() -> None:
    for name in ("index.html", "research.css", "research.js"):
        path = RESEARCH / name
        assert path.is_file(), f"missing {name}"
        assert path.stat().st_size > 0


def test_research_wires_root_absolute_assets() -> None:
    html = (RESEARCH / "index.html").read_text(encoding="utf-8")
    js = (RESEARCH / "research.js").read_text(encoding="utf-8")
    assert 'href="/research/research.css"' in html
    assert 'src="/research/research.js"' in html
    assert 'href="research.css"' not in html
    assert 'src="research.js"' not in html
    assert 'const BASE = "/artifacts/release/"' in js


def test_citable_report_markdown_is_not_vercelignored() -> None:
    ignore = (REPO_ROOT / ".vercelignore").read_text(encoding="utf-8")
    assert "*.md" in ignore
    assert "!artifacts/release/*.md" in ignore
    assert (RELEASE / "spec-010-report.md").is_file()


def test_research_states_not_a_translator() -> None:
    html = (RESEARCH / "index.html").read_text(encoding="utf-8")
    assert "Not a whale translator" in html


def test_evidence_nav_points_at_instrument() -> None:
    html = (RESEARCH / "index.html").read_text(encoding="utf-8")
    assert 'href="/"' in html
    assert 'href="/evidence"' in html
    assert 'canonical" href="/evidence"' in html


def test_vercel_maps_evidence_and_keeps_research_files() -> None:
    import json

    cfg = json.loads((REPO_ROOT / "vercel.json").read_text(encoding="utf-8"))
    redirects = {(r["source"], r["destination"]) for r in cfg["redirects"]}
    rewrites = {(r["source"], r["destination"]) for r in cfg["rewrites"]}
    assert ("/research", "/evidence") in redirects
    assert ("/evidence", "/research") in rewrites
    assert not any(r["source"] == "/" for r in cfg["redirects"])
