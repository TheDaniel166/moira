# Wheel Asteroid Catalog — Design Spec

**Date:** 2026-08-14
**Status:** Approved
**Closes:** [TheDaniel166/moira#17](https://github.com/TheDaniel166/moira/issues/17)

## Problem

On a clean `pip install moira-astro==6.2.0`, `Body.CHIRON` cannot be
computed. `moira-download-kernels` fetches DE440 and the generic JPL
300-body `asteroids.bsp`, then lists `centaurs.bsp` and
`minor_bodies.bsp` as wheel-bundled. Those files are not in the wheel,
are not in the download registry, and no longer auto-load.

Since 4.0.0 the compute path is already correct: `Body.CHIRON` bridges
to `asteroid_at()`, which asks the active reader for NAIF `2002060`.
The 10,025-body catalog `2026.08.12.1` contains Chiron (shard 082) and
the other named centaurs and TNOs. Live
`POST /v1/asteroids/position` for Chiron already returns a sovereign
position from that catalog.

The gap is install-time, not ephemeris. A clean pip user who follows
the official CLI never receives a complete small-body catalog, and
automatic admission of `2026.08.12.1` requires all 401 shards
(~18 GB). Dropping one published shard next to the 10,025-body
manifest would admit that manifest and then fail completeness.

## Decision

Ship a **new complete one-shard Type-13 catalog** of 25 named bodies
inside the `moira-astro` wheel. Do not reuse published 10,025-body
shards. Do not revive `centaurs.bsp`.

## Goals

- After `pip install moira-astro` with only a planetary kernel, the 25
  named bodies compute. No `moira-download-kernels` asteroid step.
- Chiron, the six centaurs, the four module TNOs, the four classicals,
  and the remaining named fillers in the locked roster all work.
- The 10,025-body catalog remains the live / Workspace / optional full
  source. Installing it must not conflict with the wheel catalog.
- `moira-download-kernels` stops claiming `centaurs.bsp` /
  `minor_bodies.bsp` are bundled.
- Missing-segment errors for bodies outside the 25 name catalog
  `2026.08.12.1` and https://moira-astro.com/ephemerides.

## Non-goals

- Hosting or auto-loading `centaurs.bsp` or `minor_bodies.bsp`.
- Downloading the 10,025-body catalog from `moira-download-kernels`.
- Changing interpolation, light-time, or `asteroid_at` math.
- Adding Hidalgo (not in `2026.08.12.1`).
- A second PyPI data package.
- Shipping more than one wheel shard in this release.
- Changing free/Enhanced website entitlement lists.

## Locked roster

Exactly these 25 identities, already present in catalog
`2026.08.12.1`. Canonical names match the unified master. NAIF IDs
are `2_000_000 + MPC number`.

| Order | Name | NAIF | Group |
| ---: | --- | ---: | --- |
| 1 | Ceres | 2000001 | classical |
| 2 | Pallas | 2000002 | classical |
| 3 | Juno | 2000003 | classical |
| 4 | Vesta | 2000004 | classical |
| 5 | Astraea | 2000005 | main-belt |
| 6 | Iris | 2000007 | main-belt |
| 7 | Hygiea | 2000010 | main-belt |
| 8 | Psyche | 2000016 | main-belt |
| 9 | Eros | 2000433 | near-Earth |
| 10 | Lilith | 2001181 | asteroid Lilith, not mean apogee |
| 11 | Amor | 2001221 | near-Earth |
| 12 | Chiron | 2002060 | centaur |
| 13 | Pholus | 2005145 | centaur |
| 14 | Nessus | 2007066 | centaur |
| 15 | Asbolus | 2008405 | centaur |
| 16 | Chariklo | 2010199 | centaur |
| 17 | Hylonome | 2010370 | centaur |
| 18 | Varuna | 2020000 | TNO |
| 19 | Ixion | 2028978 | TNO |
| 20 | Quaoar | 2050000 | TNO |
| 21 | Sedna | 2090377 | distant |
| 22 | Orcus | 2090482 | TNO |
| 23 | Haumea | 2136108 | dwarf |
| 24 | Eris | 2136199 | dwarf |
| 25 | Makemake | 2136472 | dwarf |

The shard writes bodies in **NAIF ID ascending order** (the table
order). The roster is frozen in
`moira/kernels/asteroids_wheel/targets.json` and must not be edited
without a new catalog version.

## Catalog identity

| Field | Value |
| --- | --- |
| `catalog_id` | `moira-asteroids-wheel` |
| First `catalog_version` | `2026.08.14.1` |
| `manifest_schema` | `moira.small-body-catalog/v1` |
| Install directory | `moira/kernels/asteroids_wheel/` |
| Shard file | `asteroid_shard_000.bsp` |
| `shard_count` | 1 |
| `body_count` | 25 |

This directory is distinct from `moira/kernels/asteroids/`, which
keeps the metadata-only 10,025-body manifest. Discovery already walks
`<kernel-root>/<subdir>/manifest.json`. A second complete catalog is
the supported shape.

The wheel catalog is **release-finalized**: `manifest.json` carries a
`release` object, `SHA256SUMS`, per-shard metadata, `LICENSE`, and
`NOTICE.md` (the existing small-body notice). Load-time
`verify_release` therefore runs and will refuse a truncated copy.

## Build

Reuse the unified Type-13 writer. Do not invent a second interpolation
layout.

- Source: JPL Horizons `VECTORS`, `CENTER=500@10`, `REF_PLANE=FRAME`,
  `OUT_UNITS=KM-S`, `STEP_SIZE=10d`, window `1600-01-01`–
  `2500-01-01`, Type-13 `window_size=7`.
- Builder: a dedicated script
  `scripts/build_wheel_asteroid_catalog.py` that reads the frozen
  25-row targets file, fetches the 25 bodies, writes one shard, and
  emits a pre-release `manifest.json` plus
  `asteroid_shard_000.metadata.json`.
- Finalize with `python -m moira.small_body_catalog_release prepare`
  into a staging directory, then replace
  `moira/kernels/asteroids_wheel/` with those bytes.
- Coverage policy is the same as the unified builder: if Horizons or
  SBDB reports a narrower trustworthy arc for a roster body, record a
  `coverage_exceptions` entry. Do not invent wider coverage than
  Horizons will give.
- Expected size is one standard 25-body shard, about 46,090,240
  bytes (~44 MB). That cost is accepted. Twenty published wheels will
  each carry the same 44 MB.

The finalized BSP, metadata, manifest, receipt, license, and notice
are **committed to the repository**. Wheel and sdist builds must not
call Horizons. A later roster or sampling change is a new
`catalog_version` and new bytes; published `2026.08.14.1` is never
rewritten.

## Runtime admission

`find_all_small_body_manifests()` already discovers
`moira/kernels/asteroids_wheel/manifest.json` because the directory
contains an installed shard. The 10,025-body package manifest stays
metadata-only and is not admitted.

When both catalogs are present (typical live box: user/data
`asteroids/` plus the wheel `asteroids_wheel/`):

1. Search-root order is unchanged: env dir, `~/.moira/kernels/`,
   package `moira/kernels/`, repo `kernels/`.
2. `KernelPool` first match wins.
3. A full `2026.08.12.1` install under a higher-precedence root
   therefore supplies Chiron when both exist. The wheel catalog is
   the fallback for clean pip installs.

Do not delete or hide wheel bodies when the large catalog is present.
Duplicate NAIF IDs are allowed; the higher-precedence complete catalog
wins.

`available_kernels` continues to list planetary kernels only.
Small-body catalogs remain manifest-discovered.

## Packaging

`pyproject.toml` package-data today is `kernels/**/*.json`. Add the
wheel catalog binaries without opening the door to accidental BSPs:

```
"kernels/asteroids_wheel/*.json",
"kernels/asteroids_wheel/*.bsp",
"kernels/asteroids_wheel/SHA256SUMS",
"kernels/asteroids_wheel/LICENSE",
"kernels/asteroids_wheel/NOTICE.md",
```

Keep `kernels/**/*.json` so the 10,025-body and comet metadata
manifests still ship.

A smoke test of the built wheel must assert
`asteroid_shard_000.bsp` is present and
`verify_release(<package>/kernels/asteroids_wheel)` succeeds.

## Installer and errors

`moira/download_kernels.py`:

- Delete the `bundled = ["centaurs.bsp", "minor_bodies.bsp"]` list
  and the module-docstring claim that those files ship in the wheel.
- `list_kernels` reports the wheel catalog as present when
  `find_sovereign` / the `asteroids_wheel` manifest verifies, e.g.
  `moira-asteroids-wheel 2026.08.14.1  OK (wheel)`.
- Do not add a download URL for `centaurs.bsp`.
- Leave the generic JPL `asteroids.bsp` and `sb441-n373s.bsp`
  entries as optional caller-managed compatibility inputs. Their
  descriptions must say they do not install Chiron and do not
  substitute for either Moira catalog.

When `asteroid_at` / the kernel pool raises “no segment” for a known
catalog identity that is not in the loaded readers, the message must
name `2026.08.12.1` and the ephemerides archive. Do not mention
`centaurs.bsp`.

## Documentation

Update the sentences that still describe the pre-4.0.0 four-kernel
world:

- `README.md` kernel / small-body sections: the wheel carries
  `moira-asteroids-wheel` (25 named bodies). The 10,025-body catalog
  remains a separate complete install.
- `moira/centaurs.py`, `moira/tno.py`, `moira/classical_asteroids.py`
  module docs: drop “requires `centaurs.bsp` / `sb441-n373s.bsp` /
  `asteroids.bsp`”. Positions come from any admitted small-body
  reader that has the NAIF ID; the wheel catalog is sufficient for
  these named sets.
- `moira/constants.py` `Body.CHIRON` comment: no longer “requires
  separate kernel”.
- `wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md`: `SE_CHIRON`
  maps to `Body.CHIRON` and works after `pip install` plus a
  planetary kernel.
- `CHANGELOG.md` for the release that first ships the catalog.

After the engine release that contains the wheel catalog, comment on
and close issue #17: Chiron is in the wheel catalog; `centaurs.bsp`
is retired; the 10,025-body archive remains the full source.

## Version

Ship in the next `moira-astro` patch after 6.2.0 (`6.2.1`). This is a
packaging and install-honesty fix. No public function signatures
change.

## Tests

- Roster file has exactly the 25 NAIF IDs and names above.
- Finalized `asteroids_wheel` manifest: `catalog_id`, version,
  `shard_count == 1`, `body_count == 25`, release identity present.
- `verify_release` on the committed directory passes.
- `find_all_small_body_manifests()` includes the wheel catalog when
  the package tree is a search root, and still excludes the
  metadata-only 10,025-body package manifest.
- `download_kernels.list_kernels` does not print `centaurs.bsp` or
  `minor_bodies.bsp` as bundled.
- With only a planetary kernel plus the wheel catalog, `asteroid_at`
  succeeds for `Chiron`, `Ceres`, `Eris`, and `Amor` at
  `1990-06-15T12:00Z`.
- `asteroid_at("Mani")` (or another 10,025-only identity) still
  raises, and the error names the full catalog.
- Wheel package-data / an installed-package inspection test fails if
  the BSP is missing.

## Risks

- **44 MB per wheel.** Accepted. Do not split to a second package in
  this release.
- **Horizons availability while building.** The build is a one-time
  maintainer action. The committed bytes are the release.
- **Git size.** One 44 MB binary is committed once. Do not store the
  10,025-body shards in git to “match”.
- **Duplicate NAIF when both catalogs load.** First match wins;
  higher-precedence full catalog is preferred. No merge of shards.
- **Partial copy of `asteroids_wheel/`.** `verify_release` fails
  closed. That is required.

## Out of scope leftovers

`asteroids.py` still documents the old PRIMARY/SECONDARY/TERTIARY/
QUATERNARY file paths. Cleaning that module doc is allowed in the
same patch if it is touched; rewriting the unused
`_TERTIARY_KERNEL_PATH` machinery is not required to close #17.
