---
title: Orbitalis API
emoji: 🛰️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8080
pinned: false
---

# Orbitalis_backend

Python backend for ORBITALIS, a tool for exploring NASA SPHEREx observations through time-lapse visualization.

**Status:** scaffold only — module files are header-docstring placeholders. No implementation yet.

## Documents

- `Docs/ORBITALIS_SDD.md` — build blueprint (layout, modules, API, operations).
- `Docs/ORBITALIS — Product Requirements Document (PRD) v0.1 (2).md`
- `Docs/ORBITALIS — Data and Science Specification v0.1.md`
- `Docs/ORBITALIS — UX Design & User Flows.md`

## Layout

```text
src/orbitalis_core/   pure science library (numpy, astropy, scipy only)
src/orbitalis/        application layer (api, gateway, pipeline, jobs, research, assistant, store, overlays, demo)
tests/                mirrors the modules under src/
config/               presets, releases, stack policy, assistant knowledge
models/               candidate-ranking ONNX model + model card (optional)
demo_bundle/          pre-baked offline demo data
ml/                   training and experiments (ml dependency group; not in the image)
scripts/              bake_demo.py, check_boundaries.sh
```

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked
cp .env.example .env
uv run uvicorn orbitalis.main:app --reload --port 8080
```

## Everyday commands

| Task | Command |
|---|---|
| Tests | `uv run pytest` |
| Lint / format | `uv run ruff check .` / `uv run ruff format .` |
| Check boundaries | `uv run lint-imports` |
| Add runtime dependency | `uv add <pkg>` |
| Add dev dependency | `uv add --dev <pkg>` |
| ML training tools | `uv sync --locked --group ml` |

## Notes

- The database is a disposable cache; deleting it is safe.
- `ORB_OFFLINE=1` serves the demo bundle without calling IRSA.
- The assistant and candidate ranking are optional and capability-flagged.
- Do not start coding before the organizers' coding-start date (SDD D-12).
