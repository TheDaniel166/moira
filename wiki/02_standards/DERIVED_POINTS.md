# Named derived points

The additional [source-qualified hypothetical constructions](HYPOTHETICAL_MODELS.md)
cover Arta, anchored Selena, Abramov Proserpina, prescribed Waldemath/Vulcan
orbits and historical prediction realizations under a separate discovery API.

`moira.derived_points` admits four explicit models in three families:

| Model ID | Meaning | Dated calculation needs a kernel? |
|---|---|---|
| `baker_vulcan` | Baker's symbolic Sun/Mercury longitude rule | Yes |
| `mean_priapus` | Mean lunar perigee, opposite the selected mean apogee | No |
| `osculating_priapus` | Osculating lunar perigee, opposite the existing true apogee | Yes |
| `orbital_second_focus` | Geometric second focus of a bound osculating ellipse | Yes |

Discover them with `derived_point_catalog()` or
`GET /v1/derived-points/catalog`. These are separate model identities, with no
physical NAIF IDs of their own. They are opt-in calculations and are not added
to the default planetary chart or Hamburg Uranian body catalog. Bare `Vulcan`,
`Priapus`, `Selena`, `Arta`, and `Proserpina` are not implicit selectors here.

## Baker Vulcan

[Solar Fire's official Vulcan calculation documentation](https://www.esotech.com.au/SFHelp/vulcan_calculation.htm)
describes Baker's rule: move Mercury three degrees toward Sun, stopping at Sun
when Mercury is within three degrees. There is no generally accepted physical
Vulcan ephemeris. This implementation admits the named rule, not the asserted
existence of a planet, Weston's orbital model, or Hamburg Vulkanus.

For the signed shortest separation `d = Mercury - Sun`, in `(-180, 180)`:

```text
longitude = (Sun + sign(d) * max(abs(d) - 3, 0)) mod 360
```

`baker_vulcan_from_longitudes(sun_longitude, mercury_longitude)` is kernel-free.
Its inputs must share a longitude frame; its receipt says the frame is supplied
by the caller. Inputs are normalized separately. Exactly antipodal inputs fail
because the direction toward Sun is ambiguous. Both the clamp and zodiac
wraparound are explicit. No latitude, distance, motion, retrograde flag, or
physical state is fabricated.

`baker_vulcan_at(jd_ut, reader=...)` uses the existing apparent geocentric Sun
and Mercury reductions in the true ecliptic/equinox of date. Its result retains
those input longitudes, UT1/TT/TDB epochs, kernel identity and source convention.
The result is a symbolic longitude derived from those positions.

## Mean and osculating Priapus

`mean_priapus(jd_ut, nutation=True)` is the exact antipode of
`moira.nodes.mean_lilith()` in the same selected frame. The default frame is
true ecliptic/equinox of date; `nutation=False` selects mean ecliptic/equinox of
date. The inherited IERS polynomial speed **excludes the nutation derivative**
even in the true frame. The result makes that limitation explicit.

`osculating_priapus(jd_ut, reader=...)` is the exact antipode of
`moira.nodes.true_lilith_with_truth()`. It retains the signed speed and the
complete **parent apogee** receipt, including clock, Earth-Moon gravitational
parameter, frame, kernel identity and finite-difference rate policy. A constant
180-degree translation preserves the signed rate. This API does not introduce
a new lunar dynamical model.

These names do not denote the seven-year White Moon Selena, Avestan Priap,
Arta, or the independently defined interpolated/natural perigee convention.

## Orbital second focus

For an ellipse with semimajor axis `a` and eccentricity vector `e_vector`, the
center lies at `-a * e_vector` relative to its first focus. Reflecting the first
focus through that center gives:

```text
second_focus_vector = -2 * a * e_vector
focal_distance = 2 * a * eccentricity
```

This is different from apocenter, whose distance is `a * (1 + eccentricity)`.
For any point on the ellipse, the distances to its two foci sum to `2a`.

`orbital_second_focus(body, jd_ut, center=..., frame=..., reader=...)` delegates
body admission, time binding, state extraction, gravity and singularity policy
to `moira.orbits.osculating_elements()`. Both center and frame are **required**:

- Centers: `OrbitalCenter.SUN` or `OrbitalCenter.EARTH`, subject to strict core
  body/center admission.
- Frames: `J2000_ECLIPTIC`, `MEAN_ECLIPTIC_OF_DATE`, or
  `TRUE_ECLIPTIC_OF_DATE`, subject to the existing frame validity intervals.

Coordinates are relative to the **selected central focus**, in AU. This is
instantaneous geometric conic geometry, without apparent-place corrections,
light time, or an Earth-observer translation of a Sun-relative result. The
source body retains its real identity; the focal point does not inherit its
NAIF ID as a new body. The full typed source elements and provenance survive
Python and REST transport. `second_focus_from_elements(elements)` also accepts
an existing `OsculatingElements` result without another kernel evaluation.

| Status | Vector and distance | Angular result |
|---|---|---|
| `DEFINED` | Finite elliptic second-focus vector and distance | Longitude/latitude; longitude is null at an exact ecliptic pole |
| `COINCIDENT_FOCI` | Exactly circular: zero vector and distance | Both null |
| `CIRCULAR_DIRECTION_UNDEFINED` | Nonzero eccentricity below the source circular threshold: vector null, distance retained | Both null |
| `NON_ELLIPTIC` | Parabolic/hyperbolic: vector and distance null | Both null |

The last status means this elliptic product is not evaluable; it makes no claim
that hyperbolas lack a second geometric focus. Strict orbital input, resource,
coverage, center and frame errors propagate unchanged.

## Python and facade usage

All listed functions and result vessels are exported by `moira` and
`moira.facade`, as well as their owning module.

```python
from datetime import datetime, timezone
from moira import Moira, OrbitalCenter, OrbitalFrame, mean_priapus

mean = mean_priapus(2451545.0, nutation=False)  # UT1; kernel-free

engine = Moira(kernel_path="/path/to/de441.bsp")
dt = datetime(2026, 10, 26, tzinfo=timezone.utc)
vulcan = engine.baker_vulcan(dt)
perigee = engine.osculating_priapus(dt)
mean = engine.mean_priapus(dt, nutation=False)
focus = engine.orbital_second_focus(
    "Moon", dt, center=OrbitalCenter.EARTH,
    frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE,
)
```

Datetime facade methods convert UTC to UT1 and use the instance-owned reader
for kernel-bound computations. Numerical function epochs and REST `jd_ut` are
UT1, not UTC, TT or TDB.

## REST endpoints

| Method | Path | Request |
|---|---|---|
| GET | `/v1/derived-points/catalog` | None; kernel-free |
| POST | `/v1/derived-points/baker-vulcan/from-longitudes` | `sun_longitude`, `mercury_longitude`; kernel-free |
| POST | `/v1/derived-points/baker-vulcan` | `jd_ut` |
| POST | `/v1/derived-points/priapus/mean` | `jd_ut`, optional Boolean `nutation` (default true); kernel-free |
| POST | `/v1/derived-points/priapus/osculating` | `jd_ut` |
| POST | `/v1/derived-points/second-focus` | `body` (name or integer ID), `jd_ut`, `center`, `frame` |

Requests forbid extra fields, Boolean numeric inputs, nonfinite numbers and
implicit numeric-string coercion. Responses use named typed schemas in OpenAPI,
under the Derived Points catalog family. There is no generic unqualified
hypothetical-body dispatcher.

Validation covers documented Baker examples and boundaries, covariance under
zodiac rotation, independently constructed rotated ellipses and the focal
distance-sum invariant, circular/polar/non-elliptic outcomes, existing frozen
Horizons holdouts at identical TDB epochs, lunar rate/truth retention, facade
clock/reader binding, and REST schema/receipt behavior. No scientific fixture
or existing acceptance threshold is changed.
