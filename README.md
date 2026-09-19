# Rosetta Coda

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Deployed](https://img.shields.io/badge/site-rosetta--coda.vercel.app-0aa)](https://rosetta-coda.vercel.app)

**Phonological hypothesis instrument for sperm-whale codas.**

Rosetta Coda is a local-first research instrument for generating falsifiable phonological hypotheses about sperm-whale vocalisations (codas). It is **not** a translator — there is no semantic ground truth. Every transformation is reproducible from immutable inputs, versioned code, configuration, and model identifiers.

---

## Overview

Sperm whales produce rhythmic click patterns called *codas*. Rosetta Coda provides a reproducible pipeline to:

- **Ingest** metadata and optional audio into canonical, validated records
- **Cohort** individuals by identity resolution status (resolved / unresolved)
- **Normalize** per-whale timing baselines with z-scores
- **Gate** against preregistered published results before further analysis
- **Extract** deterministic phonological features (rhythm, tempo, ornament, rubato)
- **Generate** falsifiable, evidence-grounded hypotheses via structured LLM calls
- **Assemble** citable reports with explicit uncertainty and limitations

All stages produce immutable JSON/JSONL artifacts with content-hash manifests for full auditability.

## Repository structure

```
rosetta-coda/
  contracts/       # Pydantic models and exported JSON Schema
  data/            # Metadata loaders, validation, provenance
  analysis/        # Normalization, statistical gates, held-out calibration
  detector/        # Optional WAV click/coda detection
  phonology/       # Timing extraction + deterministic feature engine
  interpretation/  # Analyst adapter + ranked, falsifiable hypotheses
  reporting/       # Citable report.json / report.md assembly
  api/             # Local read-only artifact API (FastAPI)
  demo/            # SPEC-004 gate demo (static)
  research/        # Research console over the sealed release (static)
  artifacts/       # gates/, demo/, release/ (content-addressed)
  specs/           # Accepted implementation contracts
  tests/           # Unit, integration, golden, and fixture tests
```

## Quick start

```bash
uv sync --all-extras
uv run pytest
```

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

### Full pipeline

```bash
export ROSETTA_API_KEY="..."   # DeepSeek-compatible key; omit for --no-model
uv run python -m scripts.run_pipeline            # all stages into artifacts/runs/
uv run python -m scripts.run_pipeline --no-model # deterministic stages only
```

The run id is derived from input hashes (`pipeline-<dataset>-<codamd>`), so
identical inputs always reproduce the same run directory.

### Sealed release and replay

`artifacts/release/` is the golden run, pinned by sha256 in
`artifacts/release/manifest.json`. Verify it end-to-end:

```bash
uv run python -m scripts.replay_release
# verified: 7/7 deterministic replayed, 6/6 sealed verified
```

See [REPRODUCE.md](REPRODUCE.md) for what is replayed vs. sealed.

### Local research API

```bash
uv run uvicorn api.app:app --port 8787
# GET /v1/runs, /v1/runs/{id}/codas, /v1/runs/{id}/artifacts/{name}, SSE events
```

The API is read-only over `artifacts/runs/` — local use only; the public
deployment serves static artifacts instead of a live endpoint.

### Deployed site

The static site is deployed on Vercel: <https://rosetta-coda.vercel.app>

- `/` — redirects to the research console
- `/research/` — research console over `artifacts/release/` (gate, contrasts, hypotheses, calibration, report)
- `/demo/` — SPEC-004 gate instrument panel (live hypothesis artifact included)
- `/artifacts/` — immutable JSON artifacts, served with immutable caching

Deploy: `vercel --prod` from the repo root (`.vercelignore` keeps the Python
pipeline and source CSVs out of the upload).

### Demo site (local preview)

A single-viewport instrument panel that visualises the frozen SPEC-004
duration gate — gate status, cohort flow, the mixed-effects coefficient,
per-whale a − i duration effects, and the frozen artifact hash — alongside a
structured hypothesis panel. Serve the repo root and open the demo:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/demo/
```

The hypothesis panel renders a real, schema-validated model output when
`artifacts/demo/hypothesis.json` exists and the demo manifest flags it;
otherwise it shows a clearly labelled **Preview** mock (never presented as a
model call). No audio, waveform, or semantic data is invented.

### Structured hypothesis demo (optional)

After the deterministic reproduction gate passes, generate one structured,
falsifiable hypothesis over that frozen evidence via any OpenAI-compatible
endpoint (default: DeepSeek — see [docs/model-provider-research.md](docs/model-provider-research.md)):

```bash
export ROSETTA_API_KEY="..."          # or OPENAI_API_KEY
export ROSETTA_BASE_URL="https://api.deepseek.com"   # optional; this is the default
export ROSETTA_MODEL="deepseek-chat"                 # optional
uv run python -m scripts.run_hypothesis_demo
# writes artifacts/demo/hypothesis.json; the manifest flag ships set
```

The model is never used for measurements and may not make translation or
semantic claims. Its output cites exact JSON evidence paths and includes
alternatives, falsifiers, uncertainty, and limitations.

## Principles

1. **No semantic claims.** Never emit claims of meaning or intent.
2. **Deterministic science first.** Extraction, statistics, and features are pure code. LLMs only propose hypotheses over frozen evidence.
3. **Evidence trace, not chain-of-thought.** Every hypothesis includes explicit evidence references, alternatives, uncertainty labels, and falsifiers.
4. **Gates before analysis.** No downstream stage runs until the preregistered reproduction gate passes.
5. **Immutable artifacts.** Every run produces content-addressed, versioned artifacts.

## Status

Spec-driven: SPECs 000–013 implemented. The deterministic pipeline
(load → normalize → gate → extract → features) is verified reproducible;
the model stage (analyst → rank → calibrate → report) ran once against the
frozen evidence and is hash-sealed in `artifacts/release/`. Deployed at
<https://rosetta-coda.vercel.app>. See the [roadmap](docs/roadmap.md) and
[architecture](docs/architecture.md).

## Community

- [Contributing](CONTRIBUTING.md) — setup, spec workflow, PR conventions
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md) — how to report vulnerabilities
- [Changelog](CHANGELOG.md)
- [Citing this work](CITATION.cff) — GitHub renders a "Cite this repository" panel from this file
- License: [MIT](LICENSE)

---

## Rosetta Coda

Instrumento de hipótesis fonológicas para codas de cachalotes.

Rosetta Coda es un instrumento de investigación local-first para generar hipótesis fonológicas falseables sobre las vocalizaciones (codas) de cachalotes. **No** es un traductor — no existe una verdad semántica de referencia. Cada transformación es reproducible a partir de entradas inmutables, código versionado, configuración e identificadores de modelo.

### Resumen

Los cachalotes producen patrones rítmicos de clics llamados *codas*. Rosetta Coda ofrece un pipeline reproducible para:

- **Ingerir** metadatos y audio opcional en registros canónicos validados
- **Cohortar** individuos por estado de resolución de identidad (resuelto / no resuelto)
- **Normalizar** líneas base temporales por individuo con z-scores
- **Gatear** contra resultados publicados preregistrados antes de análisis posteriores
- **Extraer** características fonológicas deterministas (ritmo, tempo, ornamento, rubato)
- **Generar** hipótesis falseables basadas en evidencia mediante llamadas estructuradas a LLMs
- **Ensamblar** informes citables con incertidumbre y limitaciones explícitas

Todas las etapas producen artefactos JSON/JSONL inmutables con manifiestos de hash de contenido para auditoría completa.

### Inicio rápido

```bash
uv sync --all-extras
uv run pytest
```

Requiere Python 3.11+ y [uv](https://docs.astral.sh/uv/).

### Demo de hipótesis estructurada (opcional)

Después de que pase la compuerta determinista de reproducción (endpoint
OpenAI-compatible; por defecto DeepSeek — ver
[docs/model-provider-research.md](docs/model-provider-research.md)):

```bash
export ROSETTA_API_KEY="..."
uv run python -m scripts.run_hypothesis_demo
```

El modelo no realiza mediciones ni puede hacer afirmaciones semánticas o de
traducción. Cada salida cita rutas JSON de evidencia e incluye alternativas,
falseadores, incertidumbre y limitaciones.

### Principios

1. **Sin afirmaciones semánticas.** Nunca emitir afirmaciones de significado o intención.
2. **Ciencia determinista primero.** Extracción, estadísticas y características son código puro. Los LLMs solo proponen hipótesis sobre evidencia congelada.
3. **Traza de evidencia, no cadena de pensamiento.** Cada hipótesis incluye referencias explícitas a evidencia, alternativas, etiquetas de incertidumbre y falseadores.
4. **Gates antes del análisis.** Ninguna etapa posterior se ejecuta hasta que la compuerta de reproducción preregistrada pase.
5. **Artefactos inmutables.** Cada ejecución produce artefactos versionados y direccionados por contenido.

### Estado

Desarrollo guiado por especificaciones: SPECs 000–013 implementados. El
pipeline determinista (carga → normalización → compuerta → extracción →
características) es reproducible verificado; la etapa de modelo corrió una
vez sobre la evidencia congelada y está sellada por hash en
`artifacts/release/`. Desplegado en <https://rosetta-coda.vercel.app>.
Ver [roadmap](docs/roadmap.md) y [arquitectura](docs/architecture.md).
