# Complete Aspect Catalog

Moira supports **74 registered longitude aspects: 46 standard and 28 optional**,
plus **Parallel and Contra-Parallel** in the separate declination domain. The
longitude registry contains **97 declared aliases**. This reference records
the implemented geometry and defaults as of 2026-10-25.

## Reading the catalog

- Fractions are exact fractions of a full **360° turn**. The target angle is
  `360 * numerator / denominator`; repeating decimals marked **≈** are rounded
  here to six decimal places. Engine angles are floating-point evaluations of
  those targets; the fraction column preserves their mathematical identities.
- Default orbs are maximum deviations in degrees under fixed-orb mode with
  `orb_factor=1`, before caller overrides. These are Moira policy values,
  rather than a claim that all astrological traditions use the same orbs.
- Aliases are the registered input spellings, not additional aspect targets.
  Longitude name resolution ignores case and internal ASCII spaces, hyphens,
  and underscores; leading/trailing whitespace and unknown names are rejected.
  A fraction string is an alias only where the alias column lists it.
- Standard tiers are cumulative. Optional sets require an explicit
  `optional_sets` selection even with `tier=2`; their default selection is empty.

| Catalog group | Members | Selection | Optional set? |
|---|---:|---|---|
| Standard major | 5 | Included in `tier=0`, `1`, and `2` | No |
| Standard common minor | 6 | Added by `tier=1`; included in `tier=2` | No |
| Standard extended minor | 35 | Added by `tier=2` | No |
| H13 | 6 | `optional_sets=("H13",)` | Yes |
| H32 | 8 | `optional_sets=("H32",)` | Yes |
| H36 | 6 | `optional_sets=("H36",)` | Yes |
| H40 | 8 | `optional_sets=("H40",)` | Yes |
| Declination | 2 | Separate declination detector | Separate domain |

Standard membership does not mean every default call scans all 46 aspects:
`find_aspects` and `aspects_from_longitudes` default to the eleven major/common
minor targets, `aspects_between` defaults to the 46 standard targets, and
synastry defaults to the five major targets. Explicit selectors govern each call.

## Standard major aspects — 5

| Canonical name | Degrees | Exact turn fraction | Default orb | Registered aliases |
|---|---:|---:|---:|---|
| Conjunction | 0° | 0/1 | 8° | — |
| Sextile | 60° | 1/6 | 5° | — |
| Square | 90° | 1/4 | 7° | — |
| Trine | 120° | 1/3 | 7° | — |
| Opposition | 180° | 1/2 | 8° | — |

## Standard common minor aspects — 6

| Canonical name | Degrees | Exact turn fraction | Default orb | Registered aliases |
|---|---:|---:|---:|---|
| Semisextile | 30° | 1/12 | 2° | `Duodecile` |
| Semisquare | 45° | 1/8 | 2° | `Octile` |
| Sesquiquadrate | 135° | 3/8 | 2° | `Sesquisquare`; `Trioctile` |
| Quincunx | 150° | 5/12 | 3° | `Inconjunct` |
| Quintile | 72° | 1/5 | 2° | — |
| Biquintile | 144° | 2/5 | 2° | — |

## Standard extended minor aspects — 35

| Canonical name | Degrees | Exact turn fraction | Default orb | Registered aliases |
|---|---:|---:|---:|---|
| Untion | 15° | 1/24 | 1° | `Semiduodecile`; `Quartisextile`; `Quartosextile`; `Quattuorvigintile` |
| Vigintile | 18° | 1/20 | 1° | `Semidecile` |
| Seminovile | 20° | 1/18 | 1° | — |
| Hexadecile | 22.5° | 1/16 | 1° | `Semioctile`; `Sexdecile`; `Quartisquare` |
| Quindecile | 24° | 1/15 | 1° | `Trientquintile`; `Quindecile (24°)` |
| Semiseptile | ≈25.714286° | 1/14 | 1° | — |
| Undecile | ≈32.727273° | 1/11 | 1° | — |
| Decile | 36° | 1/10 | 1.5° | `Semiquintile` |
| Novile | 40° | 1/9 | 1.5° | `Nonile` |
| Biquindecile | 48° | 2/15 | 1° | — |
| Septile | ≈51.428571° | 1/7 | 1.5° | — |
| Trivigintile | 54° | 3/20 | 1° | — |
| Biundecile | ≈65.454545° | 2/11 | 1° | — |
| Sesquioctile | 67.5° | 3/16 | 1° | `Triquartisquare` |
| Squile | 75° | 5/24 | 1° | — |
| Trisemiseptile | ≈77.142857° | 3/14 | 1° | `Tresemiseptile`; `Sesquiseptile` |
| Binovile | 80° | 2/9 | 1.5° | `Binonile` |
| Quadraquindecile | 96° | 4/15 | 1° | `Quadriquindecile` |
| Triundecile | ≈98.181818° | 3/11 | 1° | — |
| Quinseminovile | 100° | 5/18 | 1° | `Quintaseminovile` |
| Biseptile | ≈102.857143° | 2/7 | 1.5° | — |
| Squine | 105° | 7/24 | 1° | — |
| Tredecile | 108° | 3/10 | 1.5° | `Tridecile`; `Sesquiquintile` |
| Quinsemioctile | 112.5° | 5/16 | 1° | `Quintaquartisquare` |
| Septvigintile | 126° | 7/20 | 1° | `Septavigintile` |
| Quinsemiseptile | ≈128.571429° | 5/14 | 1° | `Quintasemiseptile` |
| Quadriundecile | ≈130.909091° | 4/11 | 1° | `QuatroUndecile`; `Quadundecile`; `Quadraundecile` |
| Septseminovile | 140° | 7/18 | 1° | `Septaseminovile` |
| Triseptile | ≈154.285714° | 3/7 | 1.5° | — |
| Septsemioctile | 157.5° | 7/16 | 1° | `Septaquartisquare`; `Sepsemioctile` |
| Quadnovile | 160° | 4/9 | 1.5° | `Quadranovile`; `Quatronovile` |
| Nonavigintile | 162° | 9/20 | 1° | `Novigintile` |
| Quinqueundecile | ≈163.636364° | 5/11 | 1° | `QuintUndecile`; `Quinundecile`; `Quintaundecile` |
| Tao | 165° | 11/24 | 1° | `Quindecile (165°)`; `Quindecile (Tyl)`; `Contraquindecile`; `Undecaquartisextile` |
| Septaquindecile | 168° | 7/15 | 1° | `Sepquindecile`; `Septquindecile` |

## Optional H13 set — 6

| Canonical name | Degrees | Exact turn fraction | Default orb | Registered aliases |
|---|---:|---:|---:|---|
| H13 1/13 | ≈27.692308° | 1/13 | 12/13° | `1/13`; `Tredecile (13th harmonic)` |
| H13 2/13 | ≈55.384615° | 2/13 | 12/13° | `2/13`; `Bitredecile (13th harmonic)` |
| H13 3/13 | ≈83.076923° | 3/13 | 12/13° | `3/13`; `Tritredecile (13th harmonic)` |
| H13 4/13 | ≈110.769231° | 4/13 | 12/13° | `4/13`; `Quadratredecile (13th harmonic)` |
| H13 5/13 | ≈138.461538° | 5/13 | 12/13° | `5/13`; `Quintatredecile (13th harmonic)` |
| H13 6/13 | ≈166.153846° | 6/13 | 12/13° | `6/13`; `Sextatredecile (13th harmonic)` |

## Optional H32 set — 8

| Canonical name | Degrees | Exact turn fraction | Default orb | Registered aliases |
|---|---:|---:|---:|---|
| H32 1/32 | 11.25° | 1/32 | 3/8° | `1/32`; `Quartisemisquare` |
| H32 3/32 | 33.75° | 3/32 | 3/8° | `3/32`; `Triquartisemisquare` |
| H32 5/32 | 56.25° | 5/32 | 3/8° | `5/32`; `Quintaquartisemisquare` |
| H32 7/32 | 78.75° | 7/32 | 3/8° | `7/32`; `Septaquartisemisquare` |
| H32 9/32 | 101.25° | 9/32 | 3/8° | `9/32`; `Nonaquartisemisquare` |
| H32 11/32 | 123.75° | 11/32 | 3/8° | `11/32`; `Undecaquartisemisquare` |
| H32 13/32 | 146.25° | 13/32 | 3/8° | `13/32`; `Tredecaquartisemisquare` |
| H32 15/32 | 168.75° | 15/32 | 3/8° | `15/32`; `Quindecaquartisemisquare` |

## Optional H36 set — 6

| Canonical name | Degrees | Exact turn fraction | Default orb | Registered aliases |
|---|---:|---:|---:|---|
| H36 1/36 | 10° | 1/36 | 1/3° | `1/36`; `Sextisextile`; `Trigintasextile` |
| H36 5/36 | 50° | 5/36 | 1/3° | `5/36`; `Quintasextisextile` |
| H36 7/36 | 70° | 7/36 | 1/3° | `7/36`; `Septasextisextile` |
| H36 11/36 | 110° | 11/36 | 1/3° | `11/36`; `Undecasextisextile` |
| H36 13/36 | 130° | 13/36 | 1/3° | `13/36`; `Tredecasextisextile` |
| H36 17/36 | 170° | 17/36 | 1/3° | `17/36`; `Septendecasextisextile` |

## Optional H40 set — 8

| Canonical name | Degrees | Exact turn fraction | Default orb | Registered aliases |
|---|---:|---:|---:|---|
| H40 1/40 | 9° | 1/40 | 3/10° | `1/40`; `Semivigintile`; `Quadragintile` |
| H40 3/40 | 27° | 3/40 | 3/10° | `3/40` |
| H40 7/40 | 63° | 7/40 | 3/10° | `7/40` |
| H40 9/40 | 81° | 9/40 | 3/10° | `9/40` |
| H40 11/40 | 99° | 11/40 | 3/10° | `11/40` |
| H40 13/40 | 117° | 13/40 | 3/10° | `13/40` |
| H40 17/40 | 153° | 17/40 | 3/10° | `17/40` |
| H40 19/40 | 171° | 19/40 | 3/10° | `19/40` |

## Declination relationships — 2

Declination relationships compare signed equatorial declinations, rather than
separation around the ecliptic. A turn fraction or fixed ecliptic angle does
not apply to either relationship.

| Canonical name | Exact relationship | Ecliptic degrees / turn fraction | Default orb | Registered aliases |
|---|---|---|---:|---|
| Parallel | Equal declinations in the same nonzero hemisphere; two equatorial points also qualify | Not applicable | 1° declination | — |
| Contra-Parallel | Equal-magnitude declinations in opposite nonzero hemispheres | Not applicable | 1° declination | — |

Parallel admission uses `abs(dec1 - dec2) <= orb`; Contra-Parallel admission
uses `abs(dec1 + dec2) <= orb`, after the stated hemisphere qualification.
A single equatorial point paired with a non-equatorial point forms neither.
`DeclinationAspectPolicy.orb` configures their shared default tolerance.

## Selection, identity, and orb policy

To scan all 74 longitude definitions on caller-supplied geometry:

```python
from moira.aspects import (
    OPTIONAL_ASPECT_FRACTIONS,
    aspects_from_longitudes,
    resolve_aspect,
)

analysis = aspects_from_longitudes(
    {"Sun": 0.0, "Moon": 360 / 13},
    tier=2,
    optional_sets=("H13", "H32", "H36", "H40"),
)
assert analysis.optional_sets == ("H13", "H32", "H36", "H40")
assert any(aspect.aspect == "H13 1/13" for aspect in analysis.aspects)
assert OPTIONAL_ASPECT_FRACTIONS["H13 1/13"] == (1, 13)
assert resolve_aspect("1/13").name == "H13 1/13"
assert resolve_aspect("Quindecile").angle == 24
assert resolve_aspect("Tao").angle == 165
assert resolve_aspect("Tredecile").angle == 108
```

The H13 names are qualified: `Tredecile (13th harmonic)` resolves to H13 1/13,
while bare `Tredecile` remains 108°. Bare `Quindecile` remains 24°; the explicitly
qualified 165° aliases resolve to Tao.

Optional sets contain only primitive fractions below half a turn. Reducible
members already represented by lower-harmonic aspects are not duplicated.
Every optional member has a configurable default orb of `12/H` degrees:
H13 = `12/13° ≈ 0.923077°`, H32 = `3/8° = 0.375°`,
H36 = `1/3° ≈ 0.333333°`, and H40 = `3/10° = 0.3°`.

`orbs={angle: maximum_orb}` and `orb_factor` retain their existing behavior.
Traditional `orb_mode="moiety"` uses body-based moieties and remains restricted
to the five major aspects, including when optional sets were requested.

The selector is available on the ordinary longitude detectors, their facade
methods, synastry aspect/contact calls, and relationship transit searches.
`AspectPolicy(optional_sets=...)` freezes the selected keys; an explicit
`AspectPolicy` takes precedence over legacy keyword arguments. Explicit
synastry selectors override the corresponding synastry policy selection.
Keys are case-insensitive, normalized in catalog order, and must be unique.
Unknown keys, untrimmed keys, and invalid container/value types fail closed.

Name resolution alone does not enable an optional detection set. Relationship
forecast filtering requires the corresponding set to be enabled. Asking for a
specific optional motion witness by canonical name or alias is itself an
explicit selection; that single-witness call has no `optional_sets` argument.

### REST access

`GET /v1/aspects/optional-sets` returns all four optional sets with canonical
names, integer numerators/denominators, angles, default orbs, and aliases.
For position-only detection, send this body to
`POST /v1/aspects/from-longitudes`:

```json
{
  "longitudes": {"Sun": 0, "Moon": 9},
  "tier": 2,
  "optional_sets": ["H40"]
}
```

The response includes the canonical `H40 1/40` event and preserves `["H40"]`
in its computation truth. The same selector is supported by synastry,
composite/Davison aspect analyses and relationship-transit requests,
chart-wheel configuration, and asteroid-family resonance requests.

## Harmonic presets — 22

Presets label harmonic chart projections. Listing or choosing a preset does
not automatically enable an optional longitude-aspect set. H1 is the identity
projection (Natal); the other rows show the primitive `360/H` division.
Harmonic-chart conjunction orbs have their own projected/reference-orb policy;
the longitude defaults above do not replace that policy.
The ordinary harmonic-chart default reference is 12°; the separate sampled
mixed-origin harmonic-transit forecast retains its explicit 1° default.
Range products default to a maximum harmonic of 32, so request
`max_harmonic=40` or higher to include H36 and H40 in those sweeps.

| Harmonic | Preset name | Primitive angle | Primitive turn fraction | Optional longitude set |
|---|---|---:|---:|---|
| H1 | Natal | Identity projection | — | — |
| H2 | Opposition | 180° | 1/2 | — |
| H3 | Trine | 120° | 1/3 | — |
| H4 | Square | 90° | 1/4 | — |
| H5 | Quintile | 72° | 1/5 | — |
| H6 | Sextile | 60° | 1/6 | — |
| H7 | Septile | ≈51.428571° | 1/7 | — |
| H8 | Octile | 45° | 1/8 | — |
| H9 | Novile | 40° | 1/9 | — |
| H10 | Decile | 36° | 1/10 | — |
| H11 | Undecile | ≈32.727273° | 1/11 | — |
| H12 | Semi-sextile | 30° | 1/12 | — |
| H13 | H13 1/13 | ≈27.692308° | 1/13 | H13 |
| H14 | Semiseptile | ≈25.714286° | 1/14 | — |
| H15 | Quindecile | 24° | 1/15 | — |
| H16 | Hexadecile | 22.5° | 1/16 | — |
| H18 | Seminovile | 20° | 1/18 | — |
| H20 | Vigintile | 18° | 1/20 | — |
| H24 | Untion | 15° | 1/24 | — |
| H32 | H32 1/32 | 11.25° | 1/32 | H32 |
| H36 | H36 1/36 | 10° | 1/36 | H36 |
| H40 | H40 1/40 | 9° | 1/40 | H40 |

## Source ownership and related references

The [engine and REST consumer audit](../07_audit/ASPECT_CONSUMER_AUDIT_2026-10-25.md)
records the checked entry points, fixes, numeric-only adapters, and
technique-specific aspect domains.

The tables follow the actual registry, rather than inferring aliases from
names or importing rounded angles from external reference tables:

- [Standard definitions and tier membership](../../moira/constants.py)
- [Optional members and exact fraction metadata](../../moira/optional_aspects.py)
- [Canonical longitude definitions and declared aliases](../../moira/aspect_registry.py)
- [Declination geometry and policy](../../moira/declination_aspects.py)
- [Harmonic preset catalog](../../moira/harmonics.py)
- [Aspect Backend Standard](ASPECT_BACKEND_STANDARD.md), including the naming/source collation
- [Harmonics Backend Standard](HARMONICS_BACKEND_STANDARD.md)
- [Python API Reference](API_REFERENCE.md)

`Aspect.ALL` contains the 46 standard longitude definitions.
`ASPECT_DEFINITIONS` contains all 74 registered longitude definitions.
`CANONICAL_ASPECTS` preserves the 48 standard names (46 longitude and two
declination); optional members are declared separately in
`OPTIONAL_ASPECT_SETS` and `OPTIONAL_ASPECT_FRACTIONS`.
