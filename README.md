# Rosetta Coda

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

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
  analysis/        # Normalization and statistical gates
  detector/        # Optional WAV click/coda detection
  phonology/       # Deterministic rhythm/tempo/ornament/rubato features
  interpretation/  # Ranked, falsifiable hypotheses
  storage/         # Manifests, hashes, atomic artifact writes
  orchestration/   # LangGraph state and stage transitions
  api/             # Versioned local HTTP/SSE API
  web/             # Waveform, time-time plot, evidence trace
  specs/           # Accepted implementation contracts
  tests/           # Unit, integration, golden, and fixture tests
```

## Quick start

```bash
uv sync --all-extras
uv run pytest
```

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

### Demo site (local preview)

A single-viewport instrument panel that visualises the frozen SPEC-004
duration gate — gate status, cohort flow, the mixed-effects coefficient,
per-whale a − i duration effects, and the frozen artifact hash — alongside a
structured GPT-5.6 Sol hypothesis panel. Serve the repo root and open the demo:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/demo/
```

The hypothesis panel renders a real, schema-validated Sol output when
`artifacts/demo/sol-hypothesis.json` exists; otherwise it shows a clearly
labelled **Preview** mock (never presented as a Sol call). No audio,
waveform, or semantic data is invented.

### GPT-5.6 Sol demo (optional)

After the deterministic reproduction gate passes, generate one structured,
falsifiable hypothesis over that frozen evidence:

```bash
export OPENAI_API_KEY="..."
uv run python -m scripts.run_sol_demo
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

Early-stage, spec-driven development. See the [roadmap](docs/roadmap.md) and [architecture](docs/architecture.md).

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

### Demo con GPT-5.6 Sol (opcional)

Después de que pase la compuerta determinista de reproducción:

```bash
export OPENAI_API_KEY="..."
uv run python -m scripts.run_sol_demo
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

Etapa temprana, desarrollo guiado por especificaciones. Ver [roadmap](docs/roadmap.md) y [arquitectura](docs/architecture.md).
