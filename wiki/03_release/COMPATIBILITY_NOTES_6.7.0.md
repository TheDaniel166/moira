# Compatibility Notes - Moira 6.7.0

## Additive API, strictly verified astronomical corrections

Moira 6.7.0 preserves the public Python signatures and REST schemas of existing
routes while delivering precision upgrades to coordinate transformations, time
scales, and apsidal passage detection.

## Orbital elements and frames

- `osculating_elements` is the strict, shape-safe modern API returning
  `OsculatingElements` with explicit provenance receipts.
- The legacy `orbital_elements_at` adapter retains its positional signature; its
  `epoch_jd` is now truthfully labeled as TT rather than UT1.
- Frame bias is owned solely by precession, eliminating duplicate bias in
  affected planetary, comet, eclipse, occultation, and lunar-limb routes.

## Apsidal passages and distance extremes

- `apsidal_passages` provides the versioned live-ephemeris extremum root-finder.
- `distance_extremes_at` remains the planet-only compatibility adapter; its
  returned `perihelion_jd` and `aphelion_jd` are truthfully in TT.
- Legacy approximations based on mean motion are deprecated in favor of numeric
  radial velocity passage solutions.

## Planetary nodes

- `planetary_nodes.geometric_node` now operates over `TRUE_ECLIPTIC_OF_DATE`
  and respects the [1900.0, 2100.0] temporal domain.
- Small bodies (asteroids and periodic comets) compute true geometric nodes
  without requiring special-case branching.

## Shadbala Chesta Bala

- B.V. Raman's classical doctrine is fully restored for Chesta Kendra and
  Chesta Bala.
- Systems depending on the previously emitted raw values of Chesta Bala will
  observe numerical shifts for Mercury, Venus, Mars, Jupiter, Saturn, Sun, and
  Moon. In particular, Sun and Moon no longer compute Chesta Kendra from fake
  mandocchas; their Chesta Bala equals their Ayana Bala.
- Output Virupas are bounded strictly in [0, 60].
