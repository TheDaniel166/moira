# P12-02 Harmonics Transport Design

Version: 0.4
Date: 2026-07-19
Status: admitted
Scope: bounded harmonic projection, analysis, orb-policy, and sampled transit-forecast REST record

## 1. Admission Boundary

P12-02 admits these pure direct routes:

- `GET /v1/harmonics/presets`
- `POST /v1/harmonics/chart`
- `POST /v1/harmonics/age-chart`

It admits these bounded pattern-analysis routes:

- `POST /v1/harmonics/conjunctions`
- `POST /v1/harmonics/pattern-score`
- `POST /v1/harmonics/aspects`
- `POST /v1/harmonics/sweep`
- `POST /v1/harmonics/fingerprint`
- `POST /v1/harmonics/composite`

It also admits one bounded sampled forecast route:

- `POST /v1/harmonics/transit-forecast`

Deferred:

- unbounded sweeps, body maps, samples, or candidate work
- automatic chart, ephemeris, or transit-sample construction
- progression harmonic search
- interpolated or exact harmonic transit event solving
- fractional-H transit forecasting
- harmogram or spectral-analysis routes
- chart rendering, background jobs, and interpretive narrative
- Sirius numerical, algorithmic, or feature parity
- generic `/v1/special/*` exposure

## 2. Governing Transformation

The direct governing object is harmonic transformation over caller-supplied
ecliptic longitudes:

```text
normalized_longitude = longitude mod 360, in [0, 360)
harmonic_longitude = (normalized_longitude * harmonic) mod 360
```

Single-harmonic chart, conjunction, pattern-score, and composite routes accept
`harmonic` as a positive finite real number in the transport range. Integer
values are ordinary cyclic harmonics. Non-integer values are explicit
zero-Aries-anchored continuous multipliers over the canonical `[0, 360)` input
branch; they are not rounded or truncated.

Age harmonic remains a separate time-derived product. Sweep, aspects,
fingerprint, and transit-forecast harmonic collections remain integer.

The REST layer does not derive chart positions, houses, signs, or event times.
It validates caller-owned values, invokes the named engine module, and
serializes the resulting vessels.

## 3. Orb Policy

Conjunction-bearing routes accept:

- `orb`: a finite `0..30` degree H1-reference/projected-chart threshold,
  default `1.0`
- optional `orb_policy`: `{ "scaling_mode": "addey_inverse_harmonic" }`

The optional vessel makes doctrine selection explicit; `orb` continues to
carry the numeric reference value for request compatibility. The service
constructs `HarmonicOrbPolicy(reference_orb_deg=orb)` and reports:

- `reference_harmonic=1.0`
- `reference_orb_deg=orb`
- `projected_orb_limit_deg=orb` for a resolved single H
- `source_orb_limit_deg=orb/H` for a resolved single H's local source allowance
- authority, source locator, formula `O_H = O_1 / H`
- whether the request explicitly selected the policy or used the legacy orb
  adapter
- whether a non-integer H used the declared continuous extension

The engine compares projected separations with the projected limit. Transport
must not divide that threshold by H again.

## 4. Request Shapes

`GET /v1/harmonics/presets`

- no request body

`POST /v1/harmonics/chart`

- `longitudes`: non-empty map of body names to finite ecliptic longitudes
- `harmonic`: real number from `1` through `128`

`POST /v1/harmonics/age-chart`

- `longitudes`
- finite `jd_birth`
- finite `jd_now >= jd_birth`

`POST /v1/harmonics/conjunctions`

- `longitudes`
- real `harmonic` from `1` through `128`
- optional `orb`, default `1.0`
- optional `orb_policy`

`POST /v1/harmonics/pattern-score`

- same request shape as `/v1/harmonics/conjunctions`

`POST /v1/harmonics/aspects`

- `longitudes`
- optional integer `max_harmonic`, default `32`, maximum `128`
- optional `orb`, default `1.0`
- optional `orb_policy`

`POST /v1/harmonics/sweep`

- same request shape as `/v1/harmonics/aspects`

`POST /v1/harmonics/fingerprint`

- same request shape as `/v1/harmonics/aspects`

`POST /v1/harmonics/composite`

- `longitudes_a` and `longitudes_b`
- real `harmonic` from `1` through `128`
- optional `orb` and `orb_policy`
- optional `label_a` and `label_b`, default `A` and `B`

`POST /v1/harmonics/transit-forecast`

- `natal_longitudes`: caller-supplied natal body map
- `transit_samples`: timestamped records `{jd_ut, longitudes}` in strictly
  increasing order with consistent transit body identity
- `harmonics`: non-empty unique list of integers from `1` through `128`
- optional `modes`: unique subset of `one_transit_two_natal` and
  `two_transits_one_natal`; both default on
- optional `orb` and `orb_policy`
- optional non-negative `minimum_observed_duration_days`, default `0.0`
- optional positive `maximum_sample_gap_days`, default `1.0`

## 5. Bounds And Runtime Policy

Direct route bounds are:

- maximum body count per single chart: 64
- maximum body count per composite side: 32
- harmonic range: `1..128`
- default `max_harmonic`: 32
- orb range: `0..30` projected degrees
- maximum label length: 64 characters

Forecast route bounds are:

- maximum natal bodies: 12
- maximum transit bodies: 12
- maximum samples: 512
- maximum harmonic-list length: 16
- maximum candidate evaluations: 25,000

These are transport resource bounds, not harmonic doctrine. Strict numeric
validation rejects booleans, strings, and non-finite values for longitude,
orb, and single-H fields, plus fractional values on integer-only fields,
rather than relying on coercion. Forecast timestamp sequences require finite
adjacent gaps and a finite total span.

## 6. Response Shape

Preset responses contain the ordered catalogue, count, bounds, and provenance.

Chart and age-chart responses contain positions, requested/effective harmonic,
`harmonic_kind`, input count, and provenance. Each position preserves body,
normalized source longitude, projected longitude, harmonic, sign, sign symbol,
and sign degree.

Conjunction, pattern-score, aspect, sweep, fingerprint, and composite
responses preserve their prior result collections and compatibility `orb`
field. Their provenance additionally carries the resolved or unresolved orb
policy truth. For a range product, limits are resolved per harmonic by the
engine, so response policy provenance omits one misleading single-H limit.

Transit-forecast responses contain:

- `windows` and `window_count`
- deterministic `natal_bodies` and `transit_bodies`
- `transit_sample_count`
- the resolved forecast and orb policy
- provenance naming `moira.harmonic_transits`, caller ownership, supplied
  `jd_ut`, complete minimum-circular-covering-arc geometry, source locators,
  bounded evaluation, and the no-parity/no-exact-contact claim boundary

Each observed window preserves harmonic, mode, origin-qualified member
identities, first/peak/last sampled JDs, observed duration, sample count, and
all admitted sample records. These timestamps are sampled witnesses, not exact
ingress, perfection, or egress instants.

## 7. Validation Rules

The route family rejects:

- empty or oversized longitude maps
- empty or duplicate-trimmed body names
- non-finite longitudes or timestamps
- `jd_now < jd_birth`
- harmonics below 1 or above 128
- non-real single-H values and non-integer range/forecast values
- negative, non-finite, or oversized orbs
- empty or duplicate forecast harmonics/modes
- inconsistent transit identity or non-advancing forecast samples
- composite label separator ambiguity
- forecast requests above the bounded candidate-evaluation budget

Input longitudes may lie outside `[0, 360)`; the engine records and computes
from their modulo-normalized zero-Aries representative.

## 8. Provenance Rules

Ordinary harmonic responses preserve:

- `source_module=moira.harmonics`
- engine entrypoint
- `input_longitude_owner=caller_supplied`
- `chart_construction_owner=not_this_route`
- `formula_basis=(normalized_longitude * harmonic) mod 360`
- `longitude_origin=zero_aries`
- `input_branch=[0,360)`
- harmonic kind and integer-preset metadata when applicable
- request bounds and stage sequence
- complete orb-policy truth for conjunction-bearing products

Age responses additionally preserve JDs and decimal-age basis. Sweep and
fingerprint responses state that scoring is pattern density, not interpretive
judgment.

Forecast responses use the distinct `moira.harmonic_transits` provenance
contract specified in `HARMONIC_TRANSIT_FORECAST_STANDARD.md`.

## 9. Verification Record

The focused admission commands are:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\harmonics.py moira\harmonic_transits.py moira\_facade_classical.py moira\facade.py moira_server\models\harmonics.py moira_server\services\harmonics.py moira_server\routers\harmonics.py tests\unit\test_harmonics.py tests\unit\test_harmonic_transits.py tests\unit\test_classical_facade.py tests\server\test_server_harmonics_routes.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_harmonics.py tests\unit\test_harmonic_transits.py tests\unit\test_classical_facade.py tests\server\test_server_harmonics_routes.py -q
```

This corpus covers fractional-H non-truncation and OpenAPI type, zero-Aries
branch truth, Addey projected/source limits and provenance, legacy-orb
compatibility, integer range policy, mixed-origin triple geometry and window
semantics, facade delegation, transport bounds, route discovery, and
serialization.

## 10. Completion Boundary

P12-02 now covers preset discovery; positive-real direct harmonic projection;
age harmonic; one-H conjunction, score, and composite products; integer
aspects, sweep, and fingerprint products; explicit Addey inverse-H orb truth;
and bounded sampled mixed-origin transit forecasts over caller-supplied
longitudes.

It does not cover unbounded work, chart or ephemeris construction, fractional-H
forecasting, progression search, interpolation, exact event contacts,
harmograms, rendered products, interpretive narrative, or Sirius parity.
