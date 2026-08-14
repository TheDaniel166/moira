# Moira 6.2.1 - Wheel Asteroid Catalog

**Release date:** 2026-08-14

**Public upgrade path:** 6.2.0 to 6.2.1. Callers still on 6.1.x inherit the
6.2.0 admitted baseline plus this wheel catalog.

Moira 6.2.1 is a packaging and install-honesty patch. It ships a complete
25-body Type-13 catalog inside the `moira-astro` wheel so Chiron and the
locked named set compute after `pip install` plus a planetary kernel. It
does not change interpolation, light-time, public function signatures, or
REST schemas.

## In this release

- **Wheel catalog `moira-asteroids-wheel` `2026.08.14.1`** — one Type-13
  shard, 25 named bodies, discovered as a second complete small-body
  catalog under `moira/kernels/asteroids_wheel/`.
- **Honest kernel installer** — `moira-download-kernels` no longer lists
  `centaurs.bsp` or `minor_bodies.bsp` as bundled wheel files. Those files
  do not ship and do not auto-load.
- **Clearer misses** — when a known asteroid identity has no loaded
  segment, `asteroid_at` names catalog `2026.08.12.1` and
  https://moira-astro.com/ephemerides.

The 25 bodies are Ceres, Pallas, Juno, Vesta, Astraea, Iris, Hygiea,
Psyche, Eros, Lilith (1181), Amor, Chiron, Pholus, Nessus, Asbolus,
Chariklo, Hylonome, Varuna, Ixion, Quaoar, Sedna, Orcus, Haumea, Eris,
and Makemake.

## Not in 6.2.1

- The 10,025-body catalog `2026.08.12.1` still does **not** ship in the
  wheel. It remains a separate complete install from the public archive.
- `centaurs.bsp` and `minor_bodies.bsp` are not hosted, bundled, or
  revived.
- No Track B, visibility, Track C, or website entitlement change.
- Generic JPL `asteroids.bsp` and `sb441-n373s.bsp` remain optional
  caller-managed files. They do not install Chiron and do not substitute
  for either Moira catalog.

## Install

```text
pip install moira-astro==6.2.1
moira-download-kernels --yes    # planetary kernel only is enough for Chiron
```

```python
from datetime import datetime, timezone
from moira import Moira, Body

print(Moira().chart(
    datetime(1990, 6, 15, 12, tzinfo=timezone.utc),
    bodies=[Body.CHIRON],
))
```

`list_kernels` reports `moira-asteroids-wheel 2026.08.14.1  OK (wheel)`
when the packaged catalog verifies.

## Dual-catalog admission

If both the wheel catalog and a complete `2026.08.12.1` install are
present, both load. `KernelPool` first-match prefers the
higher-precedence complete catalog. Duplicate NAIF IDs are allowed.
The 10,025-body package metadata manifest stays metadata-only and is
not admitted.

## Closes

[TheDaniel166/moira#17](https://github.com/TheDaniel166/moira/issues/17)
once the published wheel is confirmed to contain
`moira/kernels/asteroids_wheel/asteroid_shard_000.bsp`.
