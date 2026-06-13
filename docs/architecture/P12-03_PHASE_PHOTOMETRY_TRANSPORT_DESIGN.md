# P12-03 Phase And Photometry Transport Design

Version: 0.2
Date: 2026-06-13
Status: admitted
Scope: phase, elongation, angular diameter, synodic phase, and apparent magnitude REST admission record

## 1. Admission Boundary

P12-03 admits phase and photometry routes in bounded direct stages.

Stage 1, scalar direct routes:

- `POST /v1/phase/illuminated-fraction`
- `POST /v1/phase/synodic`
- `POST /v1/phase/elongation`
- `POST /v1/phase/angle`
- `POST /v1/phase/angular-diameter`

Stage 2, photometry route with explicit model response fields:

- `POST /v1/phase/apparent-magnitude`

Deferred:

- topocentric phase or magnitude
- atmospheric extinction
- visual limiting magnitude
- visibility scoring
- heliacal visibility
- eclipse darkening
- moon-phase event searches
- conjunction event searches
- comet, asteroid, dwarf-planet, fixed-star, or variable-star photometry
- interpretive astrological phase text
- sky rendering

## 2. Governing Object

The governing objects are direct scalar products from `moira.phase`:

- Sun-body-Earth phase angle
- illuminated fraction from a supplied phase angle
- geocentric elongation from the Sun
- synodic ecliptic phase angle and coarse state label
- apparent angular diameter
- apparent visual magnitude for admitted bodies

The route family must not imply that all products share the same support set.
It must preserve the per-product basis and limitations documented by the
backend standard.

## 3. Product Staging

`illuminated_fraction` is pure scalar mathematics. It does not require a
kernel reader.

`synodic_phase_angle` and `elongation` depend on `planet_at(...)` geocentric
ecliptic positions.

`phase_angle`, `angular_diameter`, and `apparent_magnitude` depend on the
astronomical substrate and loaded SPK reader paths, directly or indirectly.

`apparent_magnitude` is not admitted by default in Stage 1 because it has
body-specific model provenance and narrower support than phase or diameter.

## 4. Request Shapes

`POST /v1/phase/illuminated-fraction`

Required fields:

- `phase_angle`: finite degrees

`POST /v1/phase/synodic`

Required fields:

- `body1`: non-empty body name
- `body2`: non-empty body name
- `jd_ut`: finite Julian Day in UT

Optional fields:

- `include_state`: boolean, default `true`

`POST /v1/phase/elongation`

Required fields:

- `body`: non-empty body name
- `jd_ut`: finite Julian Day in UT

`POST /v1/phase/angle`

- same request shape as `/v1/phase/elongation`

`POST /v1/phase/angular-diameter`

- same request shape as `/v1/phase/elongation`

`POST /v1/phase/apparent-magnitude`

Required fields:

- `body`: one admitted apparent-magnitude body
- `jd_ut`: finite Julian Day in UT

Optional fields:

- `include_model_detail`: boolean, default `true`

## 5. Support Sets

Angular diameter should expose only bodies with a radius entry in the engine:

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

Apparent magnitude should expose only bodies admitted by the engine:

- Moon
- Mercury
- Venus
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune

Unsupported apparent-magnitude requests must be rejected. The route must not
silently fall back to a generic magnitude law.

## 6. Response Shape

Illuminated-fraction responses should contain:

- `phase_angle`
- `illuminated_fraction`
- `range`: `[0, 1]`
- `provenance`

Synodic responses should contain:

- `body1`
- `body2`
- `jd_ut`
- `angle`
- `state`, when requested
- `angle_range`: `[0, 360)`
- `state_policy`
- `provenance`

Elongation responses should contain:

- `body`
- `jd_ut`
- `elongation`
- `angle_range`: `[0, 180]`
- `basis`: `geocentric_ecliptic_spherical_law_of_cosines`
- `provenance`

Phase-angle responses should contain:

- `body`
- `jd_ut`
- `phase_angle`
- `angle_range`: `[0, 180]`
- `basis`: `Sun_body_Earth_vector_angle`
- `provenance`

Angular-diameter responses should contain:

- `body`
- `jd_ut`
- `angular_diameter_arcseconds`
- `radius_source`: `moira.phase physical radius table`
- `distance_basis`
- `provenance`

Apparent-magnitude responses should contain:

- `body`
- `jd_ut`
- `apparent_magnitude`
- `magnitude_system`: `V`
- `model_name`
- `model_limitations`
- body-specific context fields where useful
- `provenance`

## 7. Validation Rules

The route family should reject:

- non-finite `jd_ut`
- non-finite `phase_angle`
- empty body names
- identical `body1` and `body2` only if the route policy decides that a zero
  synodic phase is not useful
- unsupported bodies for angular diameter
- unsupported bodies for apparent magnitude
- attempts to request photometry for Pluto, asteroids, comets, fixed stars, or
  variable stars
- malformed product names if a combined product route is ever admitted

The route should surface kernel or body-resolution failures as explicit
validation or dependency errors. It must not substitute another body, model, or
coordinate basis.

## 8. Provenance Rules

Every response should preserve:

- `source_module`: `moira.phase`
- engine entrypoint
- requested product
- requested body or body pair
- `jd_ut`
- coordinate or vector basis
- support-set truth
- kernel requirement truth
- `stage_sequence`: input validation, engine computation, serialization

Apparent-magnitude responses should also preserve:

- `model_family`: `Mallama_Hilton_2018` for admitted planets or
  `Schaefer_1993_moon_phase_law` for the Moon
- body-specific limitations
- unsupported-body exclusions

The provenance must state that this route family does not provide atmospheric,
topocentric, visibility, extinction, or event-search products.

## 9. Verification Record

Route admission added focused server tests for:

- illuminated-fraction boundaries at phase angles 0 and 180
- synodic angle wrap forward and reverse
- synodic state boundary labels
- elongation response range
- phase-angle response range with monkeypatched vector substrate
- angular-diameter supported body acceptance
- angular-diameter unsupported body rejection
- apparent-magnitude supported body acceptance with model provenance
- apparent-magnitude unsupported body rejection for Sun and Pluto
- non-finite `jd_ut` rejection
- empty body-name rejection
- kernel-missing or body-resolution failure reporting

Verification run for admission:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\phase.py moira_server\services\phase.py moira_server\routers\phase.py moira_server\app.py moira_server\routers\__init__.py tests\server\test_server_phase_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_phase_routes.py tests\unit\test_synodic_phase.py -q
```

Result: 20 focused server and unit tests passed.

Apparent magnitude is admitted because the response carries explicit
model-family, model-name, support-set, and unsupported-exclusion truth, and
server tests cover supported-body acceptance plus unsupported Sun, Pluto,
asteroid, and fixed-star style rejection.

## 10. Completion Boundary

P12-03 completion covers scalar illuminated fraction, synodic phase,
elongation, phase angle, angular diameter for the admitted radius table, and
apparent V magnitude for the admitted magnitude support set.

It does not include topocentric phase or magnitude, atmospheric extinction,
visual limiting magnitude, visibility scoring, heliacal visibility, eclipse
darkening, moon-phase or conjunction event searches, minor-body photometry,
fixed-star or variable-star photometry, interpretive astrological phase text,
or sky rendering.
