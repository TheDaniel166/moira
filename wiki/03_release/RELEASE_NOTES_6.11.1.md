# Release Notes - Moira 6.11.1

**Release date:** 27 October 2026.

This bounded patch follows published 6.11.0 and repairs astrocartography
horizon geometry. It retains the published native substrate and excludes
unrelated development-main and uncommitted work.

## Physical circumpolar cutoff

Fixed-direction ASC/DSC curves now use geodetic latitude in the altitude
equation. Replacing the surface normal with the geocentric radius had shifted
the horizon and could admit points beyond the physical crossing domain.

The geometric centre horizon remains 0 degrees. Opt-in refraction retains the
existing constant centre-altitude threshold of -0.5667 degrees; its cutoff is
tested against that threshold rather than an unrefracted latitude formula.

## Lunar parallax

Lunar curves now start with one apparent geocentric vector and evaluate the
WGS-84 observer subtraction and diurnal aberration at each candidate location.
The increasing and decreasing altitude branches are solved independently after
checking each latitude's actual altitude range. Topocentric coordinates at the
MC are no longer reused at rising or setting longitudes.

## Evidence

Independent ERFA horizon and ellipsoid checks cover fixed directions,
finite-distance synthetic Moon vectors, both hemispheres, both horizon modes,
branch orientation and limiting tangency. DE441-backed forward sky checks
cover all returned lunar samples on June 16, 21 and 29, 2026. These are physical
geometry and reference-transform checks, not a new external lunar ephemeris
accuracy claim. See [compatibility notes](COMPATIBILITY_NOTES_6.11.1.md).
