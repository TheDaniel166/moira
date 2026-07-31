# Physical Heliacal Visibility Phase 4 Directional-Horizon Checkpoint

Date: 2026-07-31
Status: implemented and locally verified; Phase 4 remains open

## Scope

This checkpoint begins Phase 4 with the bounded environmental component whose
doctrine and event mathematics are complete: a caller-supplied local terrain
horizon. It does not admit Jones moonlight, a global airglow model, an observer
population factor, weather, or live terrain acquisition.

The protected legacy heliacal path remains unchanged. The new behavior is
available only through `PhysicalVisibilityPolicy.directional_horizon`.

## Governing Object

`PhysicalHorizonProfile` is a source-identified circular field of apparent
horizon altitude as a function of local azimuth. It contains:

- typed `PhysicalHorizonSample` values;
- a profile identifier;
- a source identifier;
- a lowercase SHA-256 source receipt;
- the fixed `circular_linear_azimuth_v1` interpolation method;
- the admitted and actual maximum circular segment width; and
- the exact maximum absolute slope of all linear segments.

Azimuths are normalized to `[0, 360)`. The implementation explicitly repairs
the floating-point modulo edge in which a negative value very close to zero
can yield exactly `360.0`; that result is canonicalized to `0.0` before
validation.

## Admission and Ambiguity Policy

- Every sample altitude is an apparent altitude in `[-5, 90)` degrees.
- The maximum gap, including the segment across north, is 10 degrees.
- Normalized duplicate azimuths fail construction.
- Missing circular coverage fails construction.
- Interpolation wraps linearly from the final sample through 360 degrees to
  the first sample.
- A nonzero scalar horizon and a directional profile are competing
  authorities and cannot be supplied together.
- The profile applies to both the target and the Sun.
- The target's effective event boundary is the maximum of terrain altitude
  and the separately identified refracted data-pack altitude floor.
- No coordinate, online service, elevation model, or zero-altitude fallback
  supplies a missing direction.

The scalar `local_horizon_altitude_deg` calculation and all pre-existing
fields remain behaviorally compatible for callers that do not opt into a
profile. New horizon metadata is additive; no claim of byte-identical
dataclass serialization is made.

## Event Completeness Certificate

Directional terrain changes the target/Sun horizon signal and therefore could
invalidate the Phase 3 crossing proof if treated as a display-only field. A
naive `apparent altitude - H(azimuth)` certificate is also invalid at the
zenith, where azimuth is undefined. This checkpoint instead certifies a signal
defined from the local unit direction:

```text
g = z - r * tan(H(theta))
```

Here `z` is the direction's vertical component, `r` is the magnitude of its
horizontal projection, and `theta` is horizontal direction away from the
zenith. For admitted apparent altitudes and terrain values, `g` has the same
sign and zeros as `apparent altitude - H`. At the zenith, `r = 0`, so
`g = z` and does not depend on an undefined azimuth.

For a circular-linear profile, let:

- `S` be the exact maximum absolute terrain slope;
- `T` be the maximum `abs(tan(H))`;
- `Q` be the maximum `sec(H)^2`; and
- `K = sqrt(T^2 + (Q*S)^2)` be the horizontal cone's Lipschitz factor.

The admitted local-direction angular-rate ceiling is the conservative binary
ceiling of 1024 degrees/day. The runtime certificate therefore uses:

```text
L = radians(1024) * (1 + K) signal units/day
```

The effective target horizon is the maximum of the profile and a constant
pack floor. That maximum has slope no greater than `S`, and the floor altitude
is included when bounding `T` and `Q`.

The immutable derivation receipt is:

```text
scripts/visibility_reference_lab/phase4_directional_horizon_certificate.json
SHA-256 3baf162ffd5f3e659b1489d60502e409f76c3b20cf6e90ef004eabb06fa029d6
```

If the resulting certificate leaves any possible-zero interval unresolved,
the existing Phase 3 solver returns
`crossing_completeness_not_certified`; it never treats dense sampling as proof.

## Receipt Coverage

Single-epoch and event results preserve:

- scalar versus directional horizon model identity;
- profile, source, and source-receipt identity;
- interpolation method;
- sample count;
- admitted and actual maximum gap;
- maximum absolute segment slope;
- queried target and solar azimuths when an assessment exists;
- local and effective target/Sun boundary altitudes;
- pack-floor narrowing truth; and
- event-certificate identity, source SHA-256, and rate ceiling.

The effective horizon also appears in the component receipts. Event results
with no selected event still carry the profile-level horizon receipt.

## Jones 2013 Research Gate

The Phase 4 source review confirmed that Jones et al. 2013 is a
Cerro-Paranal-conditioned spectral radiative-transfer model over the evaluated
0.36–0.89 μm optical range. It combines the solar spectrum, lunar albedo,
molecular/aerosol scattering, absorption, and multiple scattering. It is not a
scalar coefficient update to Krisciunas-Schaefer.

The eventual admitted identifier is reserved as:

```text
jones_paranal_scattered_moonlight_2013_v1
```

No Jones numerical path enters this checkpoint. Admission still requires a
separate immutable spectral component artifact, source and generator receipts,
an explicit lunar/site/atmosphere domain, independent numerical fixtures, and
a licensing boundary that does not copy or runtime-link ESO's GPL code into
the MIT engine.

The existing `krisciunas_schaefer_1991` identifier and behavior remain
unchanged.

## Local Verification

The checkpoint's targeted verification is:

```text
.\.venv\Scripts\python.exe -m pytest
  tests\unit\test_visibility_phase4_horizon.py
  tests\unit\test_physical_visibility_event.py -q
```

Result at checkpoint creation: `25 passed`.
Result after the zenith-safe cone-certificate hardening: `31 passed`.

The tests cover modulo normalization, north-wrap interpolation, duplicate and
coverage rejection, scalar/profile conflict, single-epoch target obstruction,
event-boundary displacement, certificate identity, existing scalar horizon
behavior, all four event phases, pack-floor ownership, typed failure, and
determinism.

The widened unit compatibility gate selected every test module whose filename
contains `heliacal` or `visibility`: `455 passed`. The visibility and phase
server-route gate added `24 passed`. The immutable certificate validator,
scoped Ruff check, Python compilation, and scoped `git diff --check` also
passed.

## Remaining Phase 4 Work

- implement and independently validate the separately versioned Jones
  spectral moonlight component;
- expose lunar phase, separation, altitude, atmosphere, and scattering inputs
  in its receipt;
- preserve measured total background as the highest authority while adding
  explicitly separated modeled airglow, zodiacal light, integrated starlight,
  and artificial-light components;
- keep ESO/PALACE comparisons visibly site-bound;
- define the admitted observer-factor range; and
- derive explicit environmental sensitivity envelopes.

Phase 4 is not closed by this checkpoint.
