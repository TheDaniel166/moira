# Phase And Photometry Backend Standard

Version: 0.1
Date: 2026-06-13
Status: backend standard for Phase 12 evaluation

## Scope

This standard governs the phase, elongation, angular-diameter, and apparent
visual magnitude surface:

- `moira.phase`

It covers:

- Sun-body-Earth phase angle
- illuminated fraction
- geocentric elongation from the Sun
- synodic ecliptic phase angle between two bodies
- coarse synodic phase-state labeling
- apparent angular diameter
- apparent visual magnitude

It does not govern:

- moon phase event searches
- conjunction event searches
- eclipse geometry
- visibility scoring
- heliacal phenomena
- variable-star magnitude models
- comet or asteroid photometry

## Authority And Provenance

The geometric phase products are derived from Moira's astronomical substrate:

- raw barycentric vectors from `moira.planets`
- Earth and Sun vectors from the loaded SPK reader
- geocentric ecliptic positions from `planet_at`

The apparent-magnitude models documented by the engine are:

- Mallama and Hilton 2018 and associated Astronomical Almanac treatments for
  supported planets
- Schaefer 1993 approximate lunar phase law for the Moon

The current engine explicitly excludes Pluto from apparent magnitude and does
not admit dwarf-planet, comet, asteroid, or fixed-star photometry here.

## Governing Objects

The current backend exposes scalar functions rather than a single result
vessel:

- `phase_angle(body_name, jd_ut)`
- `illuminated_fraction(phase_ang)`
- `elongation(body_name, jd_ut)`
- `synodic_phase_angle(body1, body2, jd_ut)`
- `synodic_phase_state(angle_deg)`
- `angular_diameter(body_name, jd_ut)`
- `apparent_magnitude(body_name, jd_ut)`

Future transport may introduce response vessels, but those vessels must
preserve the scalar truth and provenance of each requested product. A combined
response must not imply that every product has the same support set.

## Product Boundaries

### Phase angle

`phase_angle` computes the Sun-body-Earth angle in degrees, where:

- `0` means full phase
- `180` means new phase

It requires kernel-backed barycentric vectors.

### Illuminated fraction

`illuminated_fraction` is a pure scalar transform over a supplied phase angle:

```text
k = (1 + cos(beta)) / 2
```

It does not fetch ephemeris data.

### Elongation

`elongation` computes angular separation from the Sun as seen from Earth using
the apparent ecliptic longitude and latitude returned by `planet_at`.

The module documentation states that this is a spherical-law-of-cosines
calculation over ecliptic positions and may differ from a true
three-dimensional vector angle.

### Synodic phase

`synodic_phase_angle` returns the forward ecliptic longitude difference from
`body1` to `body2`, normalized to `[0, 360)`.

`synodic_phase_state` classifies that angle into:

- `conjunction`
- `waxing`
- `opposition`
- `waning`

These are conventional labels, not a physical partition.

### Angular diameter

`angular_diameter` uses a local physical-radius table and geocentric distance
from `planet_at`. The admitted radius table covers:

- Sun
- Moon
- Mercury
- Venus
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune
- Pluto

Unsupported bodies raise `ValueError`.

### Apparent magnitude

`apparent_magnitude` currently admits:

- Moon
- Mercury
- Venus
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune

It intentionally does not support:

- Sun
- Pluto
- dwarf planets
- asteroids
- comets
- fixed stars
- variable stars

Saturn includes a ring-aware branch where the engine's conditions fall within
the admitted validity range. Mars, Uranus, and Neptune include additional
body-specific terms documented in the module.

## Required Transport Invariants

Any REST transport for this family must preserve:

- requested body or body pair
- resolved body identity
- `jd_ut`
- product requested
- coordinate or vector basis for each product
- reader/kernel requirement truth
- support-set truth for each product
- magnitude model name where apparent magnitude is returned
- limitations for Moon, Saturn, Uranus, Neptune, Mars, and unsupported bodies
- angular units
- scalar range guarantees

Transport must reject:

- non-finite `jd_ut`
- empty body names
- unsupported bodies for a requested product
- non-finite phase angles for `illuminated_fraction`
- attempts to request apparent magnitude for unsupported bodies
- attempts to treat synodic phase labels as physical visibility states

Transport must not:

- collapse elongation and phase angle into one quantity
- imply topocentric observer correction
- imply atmospheric or visibility modeling
- imply apparent magnitude is available for all bodies accepted by
  `planet_at`
- silently substitute a weaker photometric model

## Validation Requirements

The current targeted validation corpus includes:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_synodic_phase.py -q
```

Before public REST admission, additional backend or server tests must cover:

- non-finite JD rejection at transport
- unsupported apparent-magnitude body rejection
- supported apparent-magnitude body list
- angular-diameter support list
- phase-angle range `[0, 180]`
- illuminated-fraction range `[0, 1]`
- elongation range `[0, 180]`
- synodic phase angle range `[0, 360)`
- synodic phase-state boundary labels
- kernel-missing behavior for kernel-backed products

Magnitude validation should be product-specific. A passing synodic-phase test
does not validate apparent photometry.

## REST Admission Guidance

The first admissible transport targets are direct one-epoch primitives:

1. Synodic phase angle and state.
2. Illuminated fraction from a supplied phase angle.
3. Elongation for one body at one epoch.
4. Phase angle for one body at one epoch.
5. Angular diameter for supported bodies.
6. Apparent magnitude only after explicit model/provenance response fields
   are designed.

Range searches, visibility judgments, and observation planning should stay out
of this route family.

## Non-Goals

This standard does not admit:

- topocentric phase or magnitude
- atmospheric extinction
- visual limiting magnitude
- heliacal visibility
- eclipse darkening
- variable-star light curves
- minor-body photometry
- comet brightness laws
- moon-phase event search routes
- interpretive astrological phase text
- rendered charts or sky diagrams
