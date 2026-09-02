# Moira 6.4.0 - Natal Aspect Grid and Delta-T Scenario

**Release date:** 2026-09-02

**Public upgrade path:** 6.3.0 to 6.4.0.

Moira 6.4.0 is a *timing* minor. It admits one new search product, the
natal aspect grid, and recalibrates the default future Delta-T scenario
from published sources. Every 6.3.0 request body stays valid. The
Hellenistic profile method remains `moira.hellenistic_chart_profile.v2`.

## In this release

- **Natal aspect grid** — `find_aspect_transits_to_longitudes()` and
  `Moira.natal_aspect_transits()` search one moving planet against many
  frozen ecliptic longitudes for many aspect angles at once. One native
  longitude series of the mover is scanned over the window; every
  `(longitude, angle)` pair is refined from it by the existing bisection.
  Results are `AspectTransitEvent` objects ordered by `jd_exact`, the same
  vessel `find_aspect_transits()` returns.
- **Frozen-target native pre-filter** — `find_aspect_transits()` with a
  numeric target now takes the same hybrid native scan that planet-to-planet
  searches already used. The pure-Python search is unchanged and still runs
  when the native scan is unavailable.
- **Native bindings** — `ecliptic_longitude_batch` (true ecliptic longitude
  of date for a body/observer evaluator pair over a JD series) and
  `find_aspects_to_longitude`.
- **Delta-T future scenario** — the default post-observation curve is
  `D0 + 29.09·((year − Y0)/100)²` from Morrison et al. 2021 tidal
  `43.7 s/cy²` and Shahvandi et al. 2024 GIA `−0.80 ms/cy`. The linear
  handoff slope is no longer consumed. `ΔT(2100)` moves from 83.29 s to
  about 85.00 s. Source-era totals, EOP, and `DeltaTPolicy` names are
  unchanged.
- **Doctrine note** — `WHY_MOIRA_DOES_NOT_COMPRESS_DEXX.md` explains reading
  published JPL DExx kernels instead of a second Chebyshev pack, with a
  file-reading comparison against Swiss `.se1` and a locked-TT
  milliarcsecond check against DE441.

## REST contracts

```text
POST /v1/transits/natal-aspects
POST /v1/batch/events   kind: natal_aspect_transits
```

`POST /v1/transits/natal-aspects` takes `body`, `natal_longitudes`,
`aspect_angles`, optional parallel `aspect_orbs`, `jd_start`, `jd_end`, and
`search_motion`. The batch item takes the same three list fields; when
`aspect_orbs` is omitted there, the item's `orb` applies to every angle.
Both return the `aspect_transit` event shape already used by
`/v1/batch/events`. Extra request keys remain 422.

## Not in 6.4.0

- Transit interpretation, scoring, or narrative
- A second aspect solver or a Gantt/timeline product
- Mixed-technique timing bundles (progressions, directions, returns in one
  call)
- Climate ice-melt terms in the Delta-T scenario
- Website or Urania Workspace surfaces

## Install

```text
pip install moira-astro==6.4.0
```

```python
from moira import Moira, Body
from moira.facade import find_aspect_transits_to_longitudes

m = Moira()
hits = m.natal_aspect_transits(Body.SATURN, natal_points, [0.0, 90.0, 180.0], jd_start, jd_end, aspect_orbs=[1.0, 1.0, 1.0])
```

Read `COMPATIBILITY_NOTES_6.4.0.md` before regenerating OpenAPI clients or
comparing future-dated `delta_t` values against 6.3.0 output.
