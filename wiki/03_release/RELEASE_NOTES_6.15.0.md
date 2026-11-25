# Release Notes - Moira 6.15.0

**Release date** 24 November 2026.

## Eclipse evidence

The new bounded solar and lunar eclipse APIs expose the computed occurrence,
contacts, extrema, and applicable geometry alongside the model and evaluation
limits. The solar API includes central-path transitions, instantaneous topology,
swept-footprint evidence, and geographic cross-track width on WGS84. The lunar
API supports the geometric-Moon Danjon angular and static finite-cone models.
The Python calculator and REST routes expose the same evidence products.
[Bounded eclipse evidence](../../docs/eclipse-bounded-evidence.md)

The solar and lunar search order now follows the represented maximum. A
location-specific solar search orders events by the local maximum. Solar path
availability responses identify the geometry that prevents a legacy support
width from being returned.
[Eclipse search ordering](../../docs/ECLIPSE_EVENT_ORDERING.md)

## Planetary moons and Galactic ayanamsas

`PlanetaryMoons` produces geometric states, Earth-view offsets, illumination,
and planet–moon event states for four Jupiter moons and eight Saturn moons.
The calculation uses DE441 and verified JUP365 and SAT441 extracts.
[Planetary moon snapshots](../../docs/PLANETARY_MOONS.md)

Eight Galactic ayanamsa presets expose their astronomical source, projection,
and sidereal target in mean and true modes. The Pullen Sinusoidal Delta solver
also preserves its width law through the 30° narrow-quadrant threshold.
[Ayanamsa doctrine](../02_standards/AYANAMSA_DOCTRINE_STANDARD.md)
[Pullen admission doctrine](../01_doctrines/houses/pullen_sinusoidal_admission_doctrine.md)

## Asteroid catalog and Type 13

Asteroid catalog `2026.11.24.1` contains 11,250 bodies across 450 shards,
including the 27 provisionally designated trans-Neptunian objects admitted in
the preceding catalog. The Type 13 reader and writer follow NAIF's window
encoding, centering, and epoch conventions. Known historical Moira files keep
their historical decoding. The full catalog is a separately installed artifact.
[Catalog provenance](../../PROVENANCE.md)
[Compatibility notes](COMPATIBILITY_NOTES_6.15.0.md)

## Validation

The catalog's largest sampled residuals against the corresponding JPL
references were 0.99993 m and 0.009997 mm/s. The qualification report records
the Moira and CSPICE sample counts and distinguishes direct Horizons vectors
from the continuous references used for the full-coverage sampled checks.
All six packing controls reproduced their stand-alone Type 13 states exactly
at 801 epochs each. The remaining engine checks include independent ERFA
comparisons for the Galactic frames, CSPICE checks for planetary moons, and
the version-bound eclipse acceptance record.
[Eclipse acceptance](../../docs/architecture/ECLIPSE_STAGE7_READINESS.md)
