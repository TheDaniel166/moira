# Moira

> *Moira* — in Greek myth, the goddess who assigns each soul its fate. The one who measures the thread.

Moira is a pure Python astronomical ephemeris and astrology engine. It is built on JPL DE441, the IAU 2000A/2006 standards, and a Python 3.14-first codebase. It is not a wrapper around Swiss Ephemeris. It does not depend on any C extension. It is a standalone engine with its own models, its own validation surfaces, and access to data and capabilities that did not exist when the dominant tools in this space were written.

Moira is, to our knowledge, the first open-source Python astrology engine to publish direct validation of its core astronomical computations against ERFA/SOFA reference routines at sub-milliarcsecond accuracy.

## Before You Install

- Python `3.14` is required. This is intentional.
- The published package includes small bundled kernels for `centaurs.bsp` and `minor_bodies.bsp`.
- Large kernels such as `de441.bsp` are not bundled.
- Import works without kernels, but many core calculations require local kernel files and will fail at runtime if those files are missing.
- The repository contains an exploratory desktop UI under `ui/`, but that UI is not part of the published package.

## Release Notes

Moira is alpha-stage software.

- The engine already covers a wide range of astronomical and astrological calculations.
- The public API is still being hardened through active use and testing.
- Expect iteration in the `0.1.x` line.

---

## The Case for a New Engine

In 1997, the Hipparcos catalog contained 118,218 stars. Gaia DR3 (2022) contains **1.812 billion** — with parallax, proper motion, and spectral data for most of them. In 1997, roughly 10,000 asteroids were numbered. Today the Minor Planet Center has **887,103**. Eris, Sedna, Haumea, Makemake, Gonggong — the entire trans-Neptunian landscape — were unknown. The interstellar objects ʻOumuamua (2017), Borisov (2019), and 3I/ATLAS (2025) — visitors from other star systems, passing through our solar system with computable ecliptic positions — did not exist in any catalog.

Swiss Ephemeris is a fixed data file. It cannot compute a body it was not pre-built for. It cannot access IERS real-time Earth orientation data. It has no pathway to Gaia parallax, to on-demand orbit integration, to the asteroid mythology database that now spans every culture on Earth.

Moira is built to reach all of these things. The architecture is the premise.

See [`moira/docs/BEYOND_SWISS_EPHEMERIS.md`](moira/docs/BEYOND_SWISS_EPHEMERIS.md) for the full account of what is now possible that was not in 1997.

---

## What Moira Computes

**Positions and bodies**
- Planets, Moon, Sun — geocentric and topocentric, with light-time, aberration, and relativistic deflection
- 887,000+ asteroids via JPL Horizons and SPK kernels; 36 named main-belt bodies as a convenience group
- Centaurs (Chiron, Pholus, Nessus, Asbolus, Chariklo, Hylonome) from dedicated SPK kernels
- Trans-Neptunian objects: Quaoar, Varuna, Ixion, Orcus
- True and Mean Node; True and Mean Lilith; orbital nodes and apsides for all planets
- Uranian bodies — Hamburg School (Cupido, Hades, Zeus, Kronos, Apollon, Admetos, Vulkanus, Poseidon) and Transpluto
- Fixed stars — ~1,500 from the SE catalog with proper motion and parallax; Gaia DR3 binary catalog (~290,000 entries) with BP-RP spectral color mapped to classical elemental quality
- Named star groups: 15 Behenian stars, 4 Royal Stars, Pleiades, Hyades, Orion belt, and others
- Variable stars — full phase and magnitude engine; eclipsing binary model; Algol-specific API (`algol_phase()`, `algol_is_eclipsed()`); `malefic_intensity()` and `benefic_strength()` astrological assessors

**Chart calculations**
- Houses: Whole Sign, Equal, Porphyry, Placidus, Koch, Alcabitius, Morinus, Campanus, Regiomontanus, Meridian, Vehlow, Sunshine, Azimuthal, Carter, Topocentric, Krusinski, APC, Pullen SD/SR — 18 systems
- Vertex and Anti-Vertex; antiscia and contra-antiscia
- Arabic Parts — 499 traditional formulas
- 22 zodiacal aspects with applying/separating state; declination parallels and contra-parallels
- 12 aspect patterns including Stellium, T-Square, Grand Trine, Grand Cross, Yod, Kite, Mystic Rectangle, Grand Sextile, Minor Grand Trine, Thor's Hammer, Boomerang Yod, and Wedge
- Midpoints — full midpoint matrix, 90° dial, Uranian midpoint tree
- Dignities: domicile, exaltation, triplicity, term, face, mutual reception, hayz, sect, almuten figuris, phasis
- Hermetic 36-decan system with decan-ruling star `_at()` functions and day/night decan hour sequences; Ptolemaic decans
- Planetary hours (Chaldean sequence); Gauquelin sector positions
- Local space chart (azimuth/altitude for all bodies)
- Harmonic charts with configurable harmonic number and built-in presets

**Predictive techniques**
- Secondary, tertiary, minor, and solar arc progressions — direct and converse
- Solar, lunar, and generic planet returns; prenatal syzygy
- Transits with ingress detection; synastry aspects; composite and Davison charts
- Primary directions — Placidus semi-arc and mundane
- Annual and monthly profections; Firdaria; Vimshottari Dasha with sub-period tree and nakshatra positions
- Zodiacal releasing; Hyleg and Alcocoden
- Vedic divisional charts: D7 (Saptamsa), D9 (Navamsa), D10 (Dashamansa), D12 (Dwadashamsa), D30 (Trimshamsa)

**Astronomy**
- Eclipse search, classification, and local circumstances — solar and lunar; NASA-canon contact solver
- Eclipse Saros series with heptagonal vertex labelling
- Heliacal rising and setting of fixed stars
- Parans (paranatellonta) for stars and planets, with field analysis and contour mapping
- Astrocartography lines for any body computable from an SPK kernel
- Galactic coordinate frame for all bodies; Galactic Center, anti-center, and Super-Galactic Center
- Lunar occultations, stellar occultations, and close approaches
- Planetary phenomena: greatest elongation, perihelion, aphelion, phase angle, illuminated fraction, apparent magnitude
- Rise, set, and transit times; civil, nautical, and astronomical twilight
- Retrograde station detection
- 28-mansion Arabic lunar station system (Manazil) with `moon_mansion()` and `all_mansions_at()`
- Sothic cycle — heliacal risings of Sirius, historical epoch table, drift rate, and Egyptian civil calendar conversion

**Precision infrastructure**
- IAU 2000A nutation — 1,358 luni-solar terms + 1,056 planetary terms (Swiss Ephemeris uses a truncated series by default)
- IAU 2006 P03 precession
- Hybrid ΔT model: IERS Bulletin A lookup → GRACE satellite LOD series → Stephenson–Morrison–Hohenkerk 2016 paleoclimate table → Espenak–Meeus polynomial fallback
- WGS-84 topocentric corrections
- Tropical and sidereal workflows — 30 validated ayanamsa systems including Lahiri, Fagan–Bradley, True Chitrapaksha, and others

---

## Requirements

- Python `3.14`
- `jplephem >= 2.24`
- Local JPL kernel files (see below)

---

## Installation

### From PyPI

```powershell
python -m pip install moira
```

### From Source

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

---

## Kernel Files

Moira can use a mix of bundled and external kernel files.

Bundled with the package:

| File | Contents |
|---|---|
| `centaurs.bsp` | Centaur body SPK kernel |
| `minor_bodies.bsp` | Small packaged minor-body kernel |

Still expected externally in `kernels/`:

| File | Contents |
|---|---|
| `kernels/de441.bsp` | JPL planetary ephemeris |
| `kernels/asteroids.bsp` | Numbered asteroid ephemerides |
| `kernels/sb441-n373s.bsp` | Small body supplement (TNOs, large asteroids) |

The external kernels are available from JPL Horizons and the JPL FTP server. They are excluded from version control due to size.

Without these files, SPK-backed calculations will fail at runtime.

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

If `Moira()` cannot locate the required kernel files, position-dependent calculations will raise at runtime.

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

Sub-arcsecond planetary accuracy is certified against JPL Horizons. Development remains active, and the roadmap is still the authoritative place to track scope and hardening work.

---

## Citation

If you use Moira in research or published work, please cite:

> Burkett, D. (2026). *Moira: A Pure-Python Astronomical Engine with External-Reference Validation*. Zenodo. https://doi.org/10.5281/zenodo.19152529

---

## License

MIT
