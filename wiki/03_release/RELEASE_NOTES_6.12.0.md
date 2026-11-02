# Release Notes - Moira 6.12.0

**Release date:** 2 November 2026.

This minor release follows published 6.11.1. It adds Python 3.15 wheels, the
Lilly horary perfection routes, fixed-star position products, and a broad
geodetic and Hellenistic expansion. It also repairs the engine's UT1/TT
handling and changes some defaults; read the
[compatibility notes](COMPATIBILITY_NOTES_6.12.0.md) before upgrading.
The full itemised record is in the changelog.

## Python 3.15

`cp315` wheels are built for every platform with cibuildwheel 4.3.5, and every
built wheel is now imported with its compiled extension before upload. A
separate Python 3.15 compatibility gate runs the kernel-free native, time and
frame checks. Python 3.14 remains the canonical CI baseline. `pyyaml` and
`lazrs` have no 3.15 wheel yet, so the `lunar-graze` extra cannot be fully
installed on 3.15.

## Time scales

An audit of every use of UT1, UTC and TT in the engine repaired the places that
mixed them. Sidereal time keeps UT1 (Earth rotation) apart from TT
(precession and nutation); the equation of the equinoxes uses the IAU 2006 mean
obliquity; the star heliacal search and the lunar-limb profile adjustment use
the engine's Earth clock and the DE441 reader path; a leap-second instant no
longer runs the UTC label backwards and displays as `23:59:60`; the Hermetic
decan Ascendant uses the engine's sidereal time. Bundled EOP, polar motion and
leap-second data were re-synced, and `iers_sync` gained failover, checksums and
stale-data rejection.

## Fixed stars

Star positions take `product="apparent"` (default), `"astrometric"` or the
other documented products. The default is now the apparent place. Sirius and
the alpha Centauri pair were also corrected, and catalog radial velocities add
perspective acceleration.

## Horary

`Moira.lilly_reception_at`, `lilly_moon_trace_at`, `lilly_void_of_course_at`
and `lilly_perfection_routes_at` expose Lilly's 1647 reception, Moon and
perfection-route readings, with `POST /v1/horary/lilly-reception`,
`/lilly-moon` and `/perfection-routes`. No verdict is produced; every textual
reading is a required input.

## Geodetic, Hellenistic and other additions

Geodetic analysis, timing and sensitivity are available on the facade and over
REST with explicit result contracts. The aspect catalog, aspect patterns,
derived and hypothetical points, primary-direction targets, Kalachakra
profiles, Hellenistic receipts and ayanamsa doctrine classes were extended.
Horizons system-release provenance is recorded alongside Horizons-derived
artifacts.

## Fixes

Solar eclipse greatest-point search on narrow ridges, orb windows narrower than
the scan step, REST routes that needed a global kernel, REST error responses,
the Vertex branch selection and native Ascendant branch parity, the sidereal
geodetic Ascendant frame, and several Hellenistic and aspect-consumer defects
are repaired. See the changelog for each.
