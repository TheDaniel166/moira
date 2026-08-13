# Planetary Reduction Pipeline

**Engine baseline:** Moira 6.1.0
**Last verified:** 2026-08-13
**Primary implementation:** `moira/planets.py`, `moira/corrections.py`,
`moira/coordinates.py`, `moira/precession.py`, and `moira/obliquity.py`

## Governing object

The planetary reduction pipeline transforms a state read from an admitted JPL
SPK kernel into a declared observer-relative position. The caller chooses the
physical mode, output centre, output frame, and optional topocentric observer.
Those choices are part of the result's meaning; they are not presentation
options.

The public low-level entry point is `planet_at(...)`. `Moira.planet_at(...)`
binds that computation to the facade's active reader. The website-facing REST
alias is `POST /v1/pipeline/positions/planet`.

## Time and kernel binding

`planet_at(...)` accepts a Julian Day in UT1. The engine converts it to the
reader-bound TT coordinate used to evaluate the active kernel. Historical
Delta-T translation is bound to the content-identified DE/LE product rather
than inferred from a filename.

The ordinary planetary path accepts admitted DE430, DE440, and DE441 readers.
Coverage is determined by the loaded kernel, not by this document.

### Major-body target identity

The public body name does not always imply a planet-center SPK target. Moira
returns the endpoint owned by the active reader's admitted NAIF route:

| Public body | DE441 route endpoint | Comparison identity |
|---|---:|---|
| Sun | `10` | Sun center |
| Moon | `301` | Moon center |
| Mercury | `199` | Mercury center |
| Venus | `299` | Venus center |
| Mars | `4` | Mars system barycenter |
| Jupiter | `5` | Jupiter system barycenter |
| Saturn | `6` | Saturn system barycenter |
| Uranus | `7` | Uranus system barycenter |
| Neptune | `8` | Neptune system barycenter |
| Pluto | `9` | Pluto system barycenter |

External comparisons must use that exact endpoint. Comparing a Moira system
barycenter with a Horizons planet center tests two different physical targets
and cannot establish kernel or reduction accuracy.

### Execution-context ownership

`planet_at(...)` remains the public validation and routing wrapper. Its internal
reduction path receives one opaque workspace that binds the reader, resolved TT
epoch, apparent/geometric mode, nutation policy, derived Earth state, and the
workspace-owned vector cache. Injected contexts are accepted only when those
provenance fields match the active call. Reader-bound reusable contexts are
bounded per reader and per thread, so a result computed for one explicit TT
epoch or policy cannot poison another call.

This is internal correctness hardening. No REST route, request model, response
model, or final planetary-position meaning is added or removed. The five
legacy underscored Python workspace hooks remain accepted for the current
compatibility cycle, are validated against the opaque workspace contract, and
emit `DeprecationWarning` when used.

## Apparent geocentric sequence

With the default `apparent=True`, `center="geocentric"`, and
`frame="ecliptic"` policy, the reduction proceeds through these named stages:

1. **Geometric geocentric state** — subtract the Earth barycentric state from
   the target barycentric state at the reception epoch.
2. **Reception light-time iteration** — evaluate the target at its retarded
   emission epoch until the travel-time solution converges.
3. **Gravitational deflection** — apply the admitted Sun, Jupiter, and Saturn
   point-mass deflectors.
4. **Annual aberration** — use Earth's reception-epoch barycentric velocity in
   the relativistic aberration transform.
5. **IAU 2006 frame bias** — rotate ICRF coordinates into the dynamical mean
   J2000 frame.
6. **IAU 2006 precession** — rotate to the mean equator of date with the P03
   Fukushima-Williams construction.
7. **IAU 2000A nutation** — rotate from the mean to the true equator of date
   when `nutation=True`.
8. **Topocentric parallax** — when a complete observer tuple is supplied,
   translate the geocentric vector by the WGS-84 observer position.
9. **Topocentric diurnal aberration** — for that same observer, apply the
   rotational observer velocity under the engine's Earth-rotation policy.
10. **Output projection** — return ecliptic longitude, latitude, and distance,
    or equatorial-of-date Cartesian coordinates when `frame="cartesian"`.

`planet_reduction_breakdown_at(...)` exposes the named stage list, enabled
flags, per-stage longitude deltas, stage longitudes, and total applied
longitude delta. It is an inspectability product over the same engine
functions; the REST pipeline route serializes this result rather than
re-implementing astronomy in the HTTP layer.

## Policy switches

- `apparent=False` omits reception light time, gravitational deflection, and
  annual aberration while retaining the declared of-date frame transform.
- `aberration=False` and `grav_deflection=False` independently disable those
  corrections only on an apparent observer-centred path.
- `nutation=False` selects the mean equator/ecliptic of date and mean
  obliquity. It is an output-frame policy in both apparent and geometric
  modes.
- `center="barycentric"` returns a Solar-System-barycentric position.
  Observer-centred aberration and deflection do not apply, while declared
  frame rotations still do.
- Topocentric correction requires latitude, longitude, and local sidereal time
  together. Partial observer input fails rather than silently falling back to
  geocentric output.

## Result semantics

The default result is `PlanetData`. Its longitude and latitude describe the
selected centre, physical mode, observer policy, and ecliptic-of-date frame.
`frame="cartesian"` returns `CartesianPosition` in the corresponding
equatorial-of-date frame.

`PlanetData.speed` remains the astrometric geocentric longitude rate even when
the selected output centre is barycentric. Consumers must not reinterpret that
field as a derivative of every selectable output surface.

Small-body names route through their admitted asteroid or comet readers. Their
installed ephemeris availability is a different fact from catalog identity or
asteroid-family membership; a metadata-only manifest does not make a body
position-capable.

## Validation boundary

The astronomy validation report records the external-reference suites for
frame construction, apparent planetary positions, wide-range vectors, and
topocentric positions. The public Mars J2000 reduction trace is a versioned
historical receipt, not a claim that one example validates every body, epoch,
kernel, observer, or policy combination.

The current major-body Horizons contracts were refreshed on 2026-08-13:

| Product | Matched contract | Enforced envelope | Recorded maximum |
|---|---|---|---|
| Apparent geocentric | Same route endpoint; reader-resolved ephemeris JD sent as discrete Horizons `TLIST` with `TIME_TYPE=TT` | `0.35"`; `0.1 km` | `0.277781"` (Saturn barycenter); `0.066846 km` (Mercury center) |
| Geometric ICRF vector | Same route endpoint; same numeric ephemeris JD sent as discrete `TLIST` with `TIME_TYPE=TDB`; `VEC_CORR=NONE` | `0.001"`; `0.01 km` | `0.000021829"` (Moon center); `0.002937 km` (Mercury center) |

The apparent angular result is a cross-reduction-model envelope, not a direct
measure of DE441 interpolation error: Moira uses IAU 2006 precession and IAU
2000A nutation, while Horizons apparent quantity 2 uses its documented
EOP-corrected IAU 1976/1980 true-equator/equinox-of-date output. The geometric
suite isolates target/vector geometry; because both services receive the same
numeric ephemeris JD, it does not independently validate TT-to-TDB conversion.
See the [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html), the
[Horizons API documentation](https://ssd-api.jpl.nasa.gov/doc/horizons.html),
and the astronomy validation report for the full qualification.

Relevant executable surfaces include:

- `tests/integration/test_horizons_planet_apparent.py`
- `tests/integration/test_horizons_planet_vectors_wide.py`
- `tests/integration/test_horizons_sky.py`
- `tests/unit/test_planet_position_switches.py`
- `tests/server/test_server_website_routes.py`

See also:

- [Astronomy validation](../03_validation/VALIDATION_ASTRONOMY.md)
- [REST API reference](../02_services/REST_API_REFERENCE.md)
- [Frame-specific positions standard](FRAME_SPECIFIC_POSITIONS_BACKEND_STANDARD.md)
