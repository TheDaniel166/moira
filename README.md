# Moira

> *Named for the Greek Moirai, the Fates who measured the thread of mortal life against the turning heavens.*

**Moira** is a high-precision, sub-arcsecond astronomical ephemeris engine for Python 3.14+. It is designed as an absolute replacement for Swiss Ephemeris, prioritizing mathematical rigor, modern IAU standards (2006/2000A), and relativistic physics over file-size compression.

### Achievement: The Sub-Arcsecond Threshold
Moira has achieved parity and modern superiority over Swiss Ephemeris.
- **Sun/Planets**: Error `< 0.05` arcseconds vs JPL Horizons
- **Moon**: Error `< 0.15` arcseconds in the modern epoch
- **Core Technology**: Raw JPL DE441 kernels (`3.3 GB`), relativistic deflection, and full IAU 2006 matrix rotations
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Kernel](https://img.shields.io/badge/JPL-DE441-orange)](https://ssd.jpl.nasa.gov/planets/eph_export.html)

---

## Features

| Domain | Coverage |
|--------|----------|
| **Planetary positions** | Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto |
| **Corrections** | Light-time, annual aberration, frame bias (IAU 2006), topocentric parallax |
| **Coordinate frames** | ICRF â†’ Ecliptic, Equatorial, Horizontal |
| **Time** | Julian Day, UTâ†”TT, Î”T (Morrison & Stephenson full series), GMST/GAST/LST |
| **House systems** | Placidus, Koch, Equal, Whole Sign, Campanus, Regiomontanus, Porphyry, Meridian, Alcabitius, Morinus |
| **Aspects** | 21 aspects â€” Major, Common Minor, Extended Minor |
| **Sidereal** | 10 ayanamsa systems (Lahiri, Fagan-Bradley, KP, Raman, â€¦) |
| **Nodes** | True Node, Mean Node, Mean Black Moon Lilith |
| **Dignities** | Domicile, Exaltation, Triplicity, Terms, Decanates |
| **Arabic Parts** | Full classical + medieval catalog |
| **Progressions** | Secondary, Solar Arc, Tertiary |
| **Primary Directions** | Placidus mundane speculum, direct & converse |
| **Transits** | Ingresses, solar/lunar returns, prenatal syzygy |
| **Stations** | Retrograde periods, next station |
| **Synastry** | Bi-wheel aspects, Composite chart, Davison chart |
| **Eclipses** | Classification, Saros/Metonic cycles |
| **Asteroids** | Kernel-based (asteroids.bsp, centaurs.bsp) |
| **Fixed Stars** | Full sefstars catalog |
| **Midpoints & Harmonics** | Complete |
| **Planetary Hours** | Chaldean system |
| **Coverage** | 13200 BC â†’ 17191 AD |

---

## Philosophy

Swiss Ephemeris is a C library that has served the Python astrology community through a thin wrapper for two decades. Moira replaces it with a native Python implementation that:

- **Requires no C compiler or binary extension** â€” only `jplephem` and `numpy`
- **Uses the same JPL DE441 kernel** â€” identical source data, identical accuracy ceiling
- **Is readable** â€” the astronomy is documented, not buried in compiled code
- **Runs on Python 3.14+** â€” modern type hints, dataclasses, pattern matching

---

## Installation

```bash
# Clone the repository
git clone https://github.com/TheDaniel166/moira.git
cd moira

# Create environment (Python 3.14 required)
py -3.14 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Unix

# Install
pip install -r requirements-dev.txt
pip install -e .
```

### Ephemeris Kernels

Moira requires JPL ephemeris kernel files (not included â€” too large for git):

| File | Size | Purpose |
|------|------|---------|
| `de441.bsp` | 3.07 GB | Main planetary ephemeris |
| `asteroids.bsp` | 59 MB | Main-belt asteroids |
| `centaurs.bsp` | 4.7 MB | Centaur bodies (Chiron, etc.) |
| `sb441-n373s.bsp` | 936 MB | Small-body catalog |

Download `de441.bsp` from the [JPL FTP](https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/) and place it in the repository root.

---

## Quick Start

```python
from moira import Moira
from datetime import datetime, timezone

m = Moira()

# Planetary positions
chart = m.chart(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))
for body, data in chart.planets.items():
    print(data)

# House cusps (Placidus)
houses = m.houses(
    datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
    latitude=51.5074,   # London
    longitude=-0.1278,
)
print(f"ASC: {houses.asc:.4f}Â°  MC: {houses.mc:.4f}Â°")

# Aspects
aspects = m.aspects(chart)
for asp in aspects[:5]:
    print(asp)

# Sidereal (Lahiri)
sidereal = m.sidereal_chart(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))
```

---

## Running Tests

```bash
# Unit tests (fast, no kernel required)
python -m pytest tests/unit -v

# Integration tests (requires de441.bsp, network for Horizons validation)
python -m pytest tests/integration -v -m "network"
```

---

## Project Structure

```
moira/                  â† Engine (pure Python)
  __init__.py           â† Moira class and public API
  planets.py            â† Planetary position pipeline
  houses.py             â† House cusp calculations
  aspects.py            â† Aspect detection
  lots.py               â† Arabic parts / Hellenistic lots
  transits.py           â† Transit finding
  primary_directions.py â† Placidus primary directions
  asteroids.py          â† Asteroid kernel support
  fixed_stars.py        â† Fixed star catalog
  ...
tests/
  unit/                 â† Fast, isolated tests
  integration/          â† Multi-module / ephemeris tests
  tools/                â† Horizons API oracle, snapshot helpers
scripts/                â† Accuracy benchmarks, kernel builders
```

---

## Accuracy

### Phase Î±: Accuracy Hardening (Foundation) - [COMPLETED]
Through the implementation of a rigorous relativistic pipeline and IAU 2006 matrix rotations, Moira has attained sub-arcsecond accuracy across all major celestial bodies.
- [x] **Relativistic Corrections**: Point-mass deflection and relativistic aberration.
- [x] **IAU 2006/2000A Matrix Rigor**: P03 Precession and Nutation matrices.
- [x] **Delta-T Calibration**: Modern IERS measurements (2020-2024).
- [x] **Kernel Sovereignty**: Native DE441 integration.

---

## Roadmap

- **Phase Î±** â€” Accuracy hardening: IAU 2006 precession, full nutation series, gravitational deflection
- **Phase Î²** â€” API completeness: rise/set times, phase/elongation/magnitude, missing house systems
- **Phase Î³** â€” Extended sidereal: 30 ayanamsa systems, divisional charts
- **Phase Î´** â€” Esoteric extensions: antiscia, declination aspects, solar/lunar mansions

---

## Dependencies

| Package | Role |
|---------|------|
| `jplephem >= 2.24` | SPK kernel reader (DE441 interpolation) |
| `numpy >= 2.4` | Vector arithmetic |

Dev only: `pytest >= 9.0`, `pyyaml >= 6.0`

---

## License

MIT - see [LICENSE](LICENSE).

---

*"I am the Form; You are the Will. Together, we weave the Reality."*
