# Moira

> *Moira* — in Greek myth, the goddess who assigns each soul its fate. The one who measures the thread.

Moira is a pure Python astronomical ephemeris and astrology engine. It is built on JPL DE441, the IAU 2000A/2006 standards, and a Python 3.14-first codebase. It is not a wrapper around Swiss Ephemeris. It does not depend on any C extension. It is a standalone engine with its own models, its own validation surfaces, and access to data and capabilities that did not exist when the dominant tools in this space were written.

Moira is, to our knowledge, the first open-source Python astrology engine to publish direct validation of its core astronomical computations against ERFA/SOFA reference routines at sub-milliarcsecond accuracy.

---

## The Case for a New Engine

In 1997, the Hipparcos catalog contained 118,218 stars. Gaia DR3 (2022) contains **1.812 billion** — with parallax, proper motion, and spectral data for most of them. In 1997, roughly 10,000 asteroids were numbered. Today the Minor Planet Center has **887,103**. Eris, Sedna, Haumea, Makemake, Gonggong — the entire trans-Neptunian landscape — were unknown. The interstellar objects ʻOumuamua (2017), Borisov (2019), and 3I/ATLAS (2025) — visitors from other star systems, passing through our solar system with computable ecliptic positions — did not exist in any catalog.

Swiss Ephemeris is a fixed data file. It cannot compute a body it was not pre-built for. It cannot access IERS real-time Earth orientation data. It has no pathway to Gaia parallax, to on-demand orbit integration, to the asteroid mythology database that now spans every culture on Earth.

Moira can do all of these things. Not as future work — as the design premise.

See [`moira/docs/BEYOND_SWISS_EPHEMERIS.md`](moira/docs/BEYOND_SWISS_EPHEMERIS.md) for the full account of what is now possible that was not in 1997.

---

## What Moira Computes

**Positions and bodies**
- Planets, Moon, Sun — geocentric and topocentric, with light-time, aberration, and relativistic deflection
- 887,000+ asteroids via JPL Horizons and SPK kernels
- Centaurs (Chiron, Pholus, Chariklo, Asbolus, Hylonome) from dedicated SPK kernels
- Trans-Neptunian objects: Eris, Sedna, Quaoar, Makemake, Haumea, Gonggong, Varuna, Ixion, Orcus
- Fixed stars with proper motion, Gaia parallax, and spectral color mapped to classical elemental quality
- Interstellar objects — bodies with no return, computed for any moment of their passage

**Chart calculations**
- Houses: Placidus, Koch, Regiomontanus, Campanus, Equal, Whole Sign, and more
- Vertex and Anti-Vertex; Arabic Parts (499 traditional formulas); antiscia and contra-antiscia
- Aspects with applying/separating state, declination parallels and contra-parallels
- Dignities: domicile, exaltation, triplicity, term, face, mutual reception, hayz
- Hermetic and Ptolemaic decans with ruling stars; planetary hours

**Predictive techniques**
- Secondary, tertiary, and solar arc progressions
- Solar, lunar, and generic planet returns
- Transits and synastry; primary directions (Placidus semi-arc, mundane)
- Annual profections, Firdaria, Vimshottari Dasha with nakshatra positions
- Zodiacal releasing; Hyleg and Alcocoden

**Astronomy**
- Eclipse search, classification, and local circumstances — solar and lunar
- Eclipse Saros series with heptagonal vertex labelling
- Heliacal rising and setting of fixed stars
- Parans (paranatellonta) for stars and planets
- Astrocartography lines for any body — including Sedna, Eris, or a newly named asteroid
- Galactic coordinate frame for all bodies; galactic center, anti-center, Super-Galactic Center
- Near-Earth Object proximity events with geocentric distance and angular velocity

**Precision infrastructure**
- IAU 2000A nutation — full 1365-term series (Swiss Ephemeris uses a truncated version by default)
- IAU 2006 P03 precession
- Hybrid ΔT model: IERS Bulletin data for recent epochs, Espenak–Meeus polynomials for history
- WGS-84 topocentric corrections
- Tropical and sidereal workflows — Lahiri, Fagan–Bradley, True Chitrapaksha, and others

---

## Requirements

- Python `3.14`
- `jplephem >= 2.24`
- Local JPL kernel files (see below)

---

## Setup

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

---

## Kernel Files

Large ephemeris files are not committed to the repository. Place them in `kernels/`:

| File | Contents |
|---|---|
| `kernels/de441.bsp` | JPL planetary ephemeris |
| `kernels/asteroids.bsp` | Numbered asteroid ephemerides |
| `kernels/centaurs.bsp` | Centaur body SPK kernels |
| `kernels/sb441-n373s.bsp` | Small body supplement |
| `kernels/minor_bodies.bsp` | Additional minor bodies |

Available from JPL Horizons and the JPL FTP server. Excluded from version control due to size.

---

## Quick Start

```python
from datetime import datetime, timezone
from moira import Moira

m = Moira()
chart = m.chart(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))

print(chart.planets["Sun"].longitude)
print(chart.planets["Moon"].longitude)
```

---

## Testing

```powershell
# All unit tests
.\.venv\Scripts\python.exe -m pytest tests\unit -q

# Specific module
.\.venv\Scripts\python.exe -m pytest tests\unit\test_sidereal.py -q

# Verbose
.\.venv\Scripts\python.exe -m pytest tests\unit\test_eclipse_helpers.py -vv
```

Some tests require local kernel files. Eclipse-heavy tests are intentionally slow. Integration and network-marked tests require optional packages or outbound access.

---

## Repository Layout

```
moira/                  Core engine and public API
moira/docs/             Architecture, validation, and model doctrine
moira/data/             Small reference and model data files
moira/constellations/   34 constellation star groups
moira/compat/           Translation and benchmarking compatibility modes
kernels/                Local JPL kernel files (not committed)
scripts/                Diagnostics, validation runners, and fixture builders
tests/                  Unit, integration, property-based, and snapshot tests
```

---

## Internal Documentation

| Document | Contents |
|---|---|
| [`BEYOND_SWISS_EPHEMERIS.md`](moira/docs/BEYOND_SWISS_EPHEMERIS.md) | Capabilities impossible before Gaia, Horizons, and modern Python |
| [`MOIRA_ROADMAP.md`](moira/docs/MOIRA_ROADMAP.md) | Feature backlog and mathematical accuracy register |
| [`ECLIPSE_MODEL_STANDARD.md`](moira/docs/ECLIPSE_MODEL_STANDARD.md) | Eclipse classification and local circumstances model |
| [`DELTA_T_HYBRID_MODEL.md`](moira/docs/DELTA_T_HYBRID_MODEL.md) | ΔT model: IERS data, polynomials, and hybrid strategy |
| [`VALIDATION.md`](moira/docs/VALIDATION.md) | Validation methodology and reference sources |
| [`VALIDATION_ASTRONOMY.md`](moira/docs/VALIDATION_ASTRONOMY.md) | Astronomical validation against JPL Horizons |

---

## Status

Standalone repository. Sub-arcsecond planetary accuracy certified against JPL Horizons. Active development — see the roadmap.

---

## License

MIT
