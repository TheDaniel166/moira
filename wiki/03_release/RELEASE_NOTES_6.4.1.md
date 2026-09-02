# Moira 6.4.1 - Natal Grid for Every Mover

**Release date:** 2026-09-02

**Public upgrade path:** 6.4.0 to 6.4.1.

Moira 6.4.1 is a *timing* patch. The natal aspect grid introduced in 6.4.0
now scans one longitude series per mover for every admitted mover, not
only the ten planets, and the dedicated REST route admits the same movers
as the batch kind. Exact event times are unchanged. Every 6.4.0 request
body stays valid.

## In this release

- **One series per mover, three tiers** — `find_aspect_transits_to_longitudes()`
  builds the mover's longitude series once per window: the native
  planetary route for planets, the native Type 13 small-body route for
  named asteroids, and resolver sampling for True Node, Mean Node, Lilith,
  and True Lilith. Every `(longitude, angle)` pair is refined from that
  series by the unchanged bisection. A one-year True Node grid drops from
  about 13 s to under 2 s on the production box.
- **Engine-owned scan step** — the grid follows `_auto_step`, and the two
  osculating points, True Node and True Lilith, now step at 0.25 day. A
  quarter-turn guard halves the step and resamples whenever consecutive
  samples jump by more than 90°, so a fast mover can never hide a double
  crossing behind a coarse step.
- **One admitted mover set** — `NATAL_ASPECT_MOVERS` (planets, True Node,
  Mean Node, Lilith, True Lilith, named asteroids) governs both
  `POST /v1/transits/natal-aspects` and the `natal_aspect_transits` batch
  kind. Both reject an unknown mover with the same message.
- **Asteroid movers in transit searches work again** — the transit and
  declination resolvers still passed `de441_reader=` to `asteroid_at()`
  after that keyword was removed on 2026-05-21, so any transit search with
  an asteroid mover raised `TypeError`. Repaired with a regression test.

## REST contracts

```text
POST /v1/transits/natal-aspects   body: any admitted mover (was planets only)
POST /v1/batch/events             kind: natal_aspect_transits (unchanged)
```

Extra request keys remain 422. Response shapes are unchanged.

## Not in 6.4.1

- A native (C++) node or Lilith series
- Sharing one series across batch items for the same mover
- Any change to `find_aspect_transits()` single-target behaviour
- Workspace or website surfaces

## Install

```text
pip install moira-astro==6.4.1
```

```python
from moira import Moira, Body
from moira.transits_aspects import NATAL_ASPECT_MOVERS

m = Moira()
hits = m.natal_aspect_transits(Body.TRUE_NODE, natal_points, [0.0, 90.0, 180.0], jd_start, jd_end, aspect_orbs=[3.0, 3.0, 3.0])
```

Read `COMPATIBILITY_NOTES_6.4.1.md` if you validate request bodies against
the 6.4.0 OpenAPI document or pin scan steps explicitly.
