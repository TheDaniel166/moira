# Moira

Moira is a pure Python astronomical ephemeris and astrology engine built around JPL DE441 data, modern IAU standards, and a Python 3.14-first codebase.

It is intended to be a serious standalone repository, not a Swiss Ephemeris wrapper and not a slice of a larger mixed project.

## What Moira Covers

- Planetary, lunar, and asteroid positions
- Tropical and sidereal astrology workflows
- Houses, aspects, lots, dignities, progressions, transits, and synastry
- Eclipse search, classification, and local circumstances
- Fixed stars, parans, occultations, and related research tooling
- Validation utilities, fixtures, and reference-driven test suites

## Project Principles

- Pure Python, with readable mathematical code and explicit validation surfaces
- Python 3.14 syntax and standards are the baseline
- `native` Moira models are authoritative inside the engine
- Compatibility modes exist for translation and benchmarking, not as governing truth
- Large runtime kernels are required for full capability, but are intentionally not committed

## Repository Layout

```text
moira/                  Core engine and public API
moira/docs/             Architecture, validation, and model doctrine
moira/data/             Small reference/model data files
scripts/                Diagnostics, validation, and fixture builders
tests/                  Unit, integration, fixtures, snapshots, and tools
sefstars.txt            Fixed-star catalog used by star-related features
```

## Requirements

- Python `3.14`
- `jplephem`
- Local JPL kernel files for full ephemeris-backed functionality

The repo includes a local virtual environment workflow:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Kernel Files

Large ephemeris files are ignored by Git and must be supplied locally.

Expected examples:

- `kernels/de441.bsp`
- `kernels/asteroids.bsp`
- `kernels/centaurs.bsp`
- `kernels/sb441-n373s.bsp`

These files are intentionally excluded from version control because they are too large for a normal repository workflow.

## Quick Start

```python
from datetime import datetime, timezone

from moira import Moira

m = Moira()
chart = m.chart(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))

print(chart.planets["Sun"].longitude)
print(chart.planets["Moon"].longitude)
```

## Testing

Moira ships with a real standalone test environment.

Useful commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_sidereal.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_eclipse_helpers.py -vv
.\.venv\Scripts\python.exe -m pytest tests\unit\test_moira_port_compliance.py -q
```

Notes:

- Some tests require local ephemeris files
- Some integration tests require optional external packages or network-marked execution
- Eclipse-heavy tests can be slow by design

## Documentation

Important internal docs live under [moira/docs](moira/docs):

- `ECLIPSE_MODEL_STANDARD.md`
- `VALIDATION.md`
- `VALIDATION_ASTRONOMY.md`
- `DELTA_T_HYBRID_MODEL.md`
- `BEYOND_SWISS_EPHEMERIS.md`

## Git Policy

The repo intentionally ignores:

- dot-directories such as local virtualenvs and tool caches
- `.cover` files and other local test artifacts
- Python cache/build output
- large binary kernel files

That keeps the repository focused on source, docs, fixtures, and reproducible tests.

## Status

This repository is now separated as a standalone Moira project with:

- its own Git history
- its own Python 3.14 environment
- Moira-only docs, scripts, and tests
- no committed kernel blobs

## License

MIT
