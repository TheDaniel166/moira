# Heliacal / Visibility Implementation Roadmap

Status:
- roadmap

Purpose:
- define the implementation sequence for Moira's generalized heliacal and
  visibility subsystem
- preserve the distinction between astronomical substrate, visibility model,
  observer environment, and event semantics
- make room for light-pollution-aware visibility policy without collapsing the
  engine into a loose workflow surface

This roadmap assumes the current baseline:
- concrete planetary heliacal/acronychal event functions already exist
- `moira.heliacal` already defines `HeliacalEventKind`, `VisibilityModel`, and
  `HeliacalPolicy`
- many physical ingredients already exist elsewhere in the engine

What remains open is not basic event computation.

What remains open is the generalized visibility doctrine:
- configurable visibility criteria
- observer-environment policy
- light pollution
- generalized event family semantics
- summit-grade validation

---

## 1. Governing Decision

Moira should not implement a Swiss-style visibility flag matrix.

The subsystem must instead preserve four distinct strata:

1. astronomical substrate
2. observer environment
3. visibility model / contrast doctrine
4. event semantics and search logic

Only after those strata are explicit should Moira expose a generalized public
visibility surface.

---

## 2. Existing Baseline

Already present in the engine:
- topocentric geometry
- rise/set doctrine
- twilight structure
- atmospheric refraction helpers
- brightness-related planetary quantities in existing result surfaces
- concrete heliacal/acronychal planetary event functions
- typed heliacal doctrine vessels in `moira.heliacal`

Therefore the missing work is compositional, not foundational.

---

## 3. Core Law

Moira must keep these categories distinct:

1. exact astronomical state
2. visibility-model policy
3. observer-environment policy
4. event-search policy

Light pollution belongs to observer-environment policy.

It must not be smuggled in as:
- a loose keyword on event functions
- an undocumented limiting-magnitude tweak
- a hidden convenience adjustment

If visibility depends on the observer's site conditions, that dependency must
be visible in a typed policy object.

---

## 4. Layer Model

### 4.1 Astronomical substrate

This layer answers:
- where is the body?
- where is the Sun?
- how bright is the body geometrically/apparently?
- what is the twilight state?
- what is the topocentric horizon geometry?

This layer should remain in the owning astronomical modules.

### 4.2 Observer environment

This layer answers:
- what sky quality does the observer have?
- what local horizon obstruction exists?
- what effective dark-sky limit applies?
- what observing aid is being used?

This is where light pollution belongs.

### 4.3 Visibility doctrine

This layer answers:
- what contrast or threshold law defines "visible"?
- how is extinction applied?
- how is twilight brightness treated?
- what relationship between body brightness and sky background is required?

### 4.4 Event semantics

This layer answers:
- what event kind is being searched?
- what counts as first visibility vs last visibility?
- what search horizon is admissible?
- what transition criterion closes the event?

---

## 5. Phase V0 — Constitutional Cleanup

Goal:
- turn the current heliacal design vessel into a true subsystem constitution
  record

Deliverables:
- document the current implemented event functions versus the still-deferred
  generalized family
- state explicitly that `VisibilityModel` is currently too narrow to serve as
  the full future policy surface
- define the engine boundary:
  - astronomy stays outside `moira.heliacal`
  - event search may live in heliacal/visibility code
  - workflow/service orchestration remains out of scope

Exit criteria:
- the constitution says exactly what is already implemented
- the deferred frontier is named explicitly

---

## 6. Phase V1 — Observer Environment Policy

Goal:
- define the observer environment layer cleanly before adding more visibility
  doctrine

Deliverables:

### V1.1 Observer environment vessel

Introduce a dedicated immutable vessel, for example:

```python
ObserverVisibilityEnvironment
    light_pollution_class
    limiting_magnitude
    local_horizon_altitude_deg
    temperature_c
    pressure_mbar
    relative_humidity
    observer_altitude_m
    observing_aid
```

Notes:
- `light_pollution_class` should not be a free-form descriptive string.
  It should be a closed policy field representing a recognized observing-sky
  darkness class, preferably a Bortle-style enum or equivalent ordinal scale.
  Its role is environmental classification, not direct photometric truth.
- `limiting_magnitude` should remain directly settable, but its semantics must
  be explicit: it is the operative visibility-threshold value used by the
  engine. It may be supplied as an explicit user override or derived from the
  active light-pollution policy.
- `local_horizon_altitude_deg` remains a separate geometric constraint. It
  must not be conflated with atmospheric refraction or sky-brightness policy.
  It describes obstruction of the observer's actual horizon profile.

These fields belong to different domains:
- `light_pollution_class` is a site-environment classifier
- `limiting_magnitude` is a visibility-threshold parameter
- `local_horizon_altitude_deg` is a geometric horizon constraint
- atmospheric refraction is an apparent-altitude correction

Do not let these fields pretend to do the same job.

### V1.2 Light pollution doctrine

Define a typed light-pollution policy:
- minimum admitted representation: Bortle class or equivalent
- optional direct sky-brightness override later if justified

The first implementation should be simple and explicit:
- one typed classification
- one documented mapping into limiting magnitude / sky-brightness assumptions

Policy law:
- light pollution influences limiting magnitude, but is not identical to it
- local horizon altitude affects whether something is geometrically visible
  above the observer's horizon, but not how bright the sky is
- atmospheric refraction alters apparent altitude near the horizon, but is not
  the same thing as the terrain/building horizon

Precedence law:
- if `limiting_magnitude` is explicitly provided, it supersedes any value
  derived from `light_pollution_class`
- if it is absent, the engine may derive an estimated limiting magnitude from
  the active light-pollution policy and other declared observing assumptions

### V1.3 Aid policy

Replace bare `optical_aid: str` style policy with a typed observer-aid enum.

Keep the first admitted family narrow:
- naked eye
- binoculars
- telescope

### V1.4 Backward-compatibility relation

Current `VisibilityModel` should either:
- become a narrower internal/input vessel consumed by the new environment
  policy, or
- be deprecated in favor of the fuller environment object

Exit criteria:
- light pollution has a declared home
- observer environment is no longer conflated with visibility doctrine

---

## 7. Phase V2 — Visibility Physics / Contrast Doctrine

Goal:
- define what "visible" means mathematically

Deliverables:

### V2.1 Visibility criterion family

Introduce a typed criterion family, for example:

```python
VisibilityCriterionFamily
    LIMITING_MAGNITUDE
    CONTRAST_THRESHOLD
    SCHAEFER_STYLE
```

The exact admitted names can differ, but Moira must not pretend one criterion
family stands for all visibility doctrine.

### V2.2 Visibility policy

Introduce a fuller immutable policy, for example:

```python
VisibilityPolicy
    criterion_family
    extinction_model
    twilight_model
    environment
    use_refraction
    moonlight_policy
```

This policy governs:
- extinction treatment
- twilight brightness treatment
- whether moonlight is ignored, included, or approximated
- how the environment is applied

### V2.3 Initial admitted criterion

Admit only one narrow first criterion family.

Recommended first freeze:
- limiting-magnitude / extinction / twilight threshold family

Reason:
- Moira already has many of the ingredients
- it is easier to validate than a more ambitious contrast-physics model
- it provides a clean place for light pollution to matter

This first admitted family should be named explicitly, for example:
- `LIMITING_MAGNITUDE_THRESHOLD`

In this first family:
- `light_pollution_class` does not directly enter the visibility equations as
  a physical variable
- it is a policy input that maps to an estimated sky condition
- `limiting_magnitude` is the actual operational quantity that enters
  visibility filtering
- `local_horizon_altitude_deg` is a geometric cutoff applied to apparent
  altitude after refraction

### V2.4 Exact vs approximate classification

The subsystem must distinguish:
- exact astronomical geometry
- exact arithmetic under the admitted criterion
- approximate environmental / observational assumptions

Visibility is inherently model-dependent.
That fact must stay visible.

### V2.5 First admitted formula chain

For the first admitted criterion family, the formulas should be layered like
this:

1. derive the operative limiting magnitude
2. compute apparent altitude from true altitude plus refraction
3. apply geometric horizon filtering
4. apply brightness filtering

Canonical precedence law:

```text
effective_limiting_magnitude =
    user_limiting_magnitude
    if user_limiting_magnitude is not None
    else policy_limiting_magnitude(light_pollution_class)
```

Recommended first derivation policy:
- make the light-pollution-to-limiting-magnitude mapping explicit and auditable
- prefer a named policy rather than a hidden heuristic

Admissible first policy examples:

Table form:

```text
Bortle 1 → 7.6
Bortle 2 → 7.1
Bortle 3 → 6.6
Bortle 4 → 6.1
Bortle 5 → 5.6
Bortle 6 → 5.1
Bortle 7 → 4.6
Bortle 8 → 4.1
Bortle 9 → 3.6
```

or the equivalent linear policy:

```text
policy_limiting_magnitude(bortle_class) = 8.1 - 0.5 * bortle_class
```

These values are policy values, not sacred physics. Their importance is that
they remain explicit and inspectable.

Altitude chain:

```text
apparent_altitude =
    true_altitude + refraction_correction(true_altitude, pressure, temperature)
```

Geometric admission:

```text
is_geometrically_visible =
    apparent_altitude >= local_horizon_altitude_deg
```

Brightness admission:

```text
is_bright_enough =
    apparent_magnitude <= effective_limiting_magnitude
```

Combined first-family observational admission rule:

```text
observable =
    is_geometrically_visible and is_bright_enough
```

This keeps the roles clean:
- light pollution informs the threshold but is not the threshold
- threshold filters brightness only
- local horizon filters geometry only
- refraction modifies altitude only

Exit criteria:
- a visibility event can be said to occur under a named criterion family
- light pollution and extinction are applied through declared policy

---

## 8. Phase V3 — Generalized Event Semantics

Goal:
- widen the event family beyond the currently admitted concrete helpers

Deliverables:

### V3.1 Generalized event search surface

Introduce a central search surface, for example:

```python
visibility_event(
    target,
    event_kind,
    jd_start,
    latitude,
    longitude,
    *,
    heliacal_policy,
    visibility_policy,
    search_policy,
)
```

This should not replace the existing narrow helpers immediately.
Those helpers can become thin stable wrappers over the generalized surface.

### V3.2 Search policy

Introduce a dedicated search policy:

```python
VisibilitySearchPolicy
    search_window_days
    coarse_step_days
    refine_tolerance_days
    long_search
```

Search policy must remain separate from visibility doctrine.

### V3.3 Event family expansion

Current concrete family already includes:
- heliacal rising
- heliacal setting
- acronychal rising
- acronychal setting

Future admitted family may also include:
- cosmic rising
- cosmic setting
- generalized first/last visibility under named criterion families

### V3.4 Planet vs star boundary

This phase must keep target-family semantics explicit:
- planets
- stars
- Moon

Stellar events should route through the star subsystem rather than bypass it.

Exit criteria:
- one generalized search surface exists
- current concrete helpers can be expressed through it
- event semantics remain typed and explicit

---

## 9. Phase V4 — Validation Program

Goal:
- establish summit-grade validation before widening public claims

Deliverables:

### V4.1 Validation strata

Validation must be stratified:

1. astronomical geometry validation
   - topocentric altitude / azimuth
   - twilight state
   - elongation
   - apparent magnitude

2. criterion validation
   - visibility threshold behavior under synthetic conditions
   - light-pollution mapping sanity
   - extinction sensitivity

3. event validation
   - known published heliacal events
   - modern planetary apparition windows
   - historical stellar events where source quality is strong enough

### V4.2 Authority hierarchy

Prefer:
- primary observational/astronomical literature
- domain-primary heliacal sources where explicit methods are given
- then specialist secondary software only as comparison layers

Do not let Swiss become the summit authority for visibility doctrine.

### V4.3 Validation corpus

Build a validation corpus split into:
- modern planetary events
- historical planetary events
- stellar events
- edge cases: poor transparency, bright twilight, low-altitude horizons

### V4.4 Tolerance doctrine

Tolerance should be declared by validation family:
- event date windows
- event time windows
- acceptable model divergence under different criterion families

Exit criteria:
- public docs can state what has been validated and under which criterion
- Moira avoids false precision claims in observational-visibility work

---

## 10. Phase V5 — Public Surface Widening

Goal:
- expose the generalized subsystem only after doctrine and validation are stable

Recommended order:

1. keep the owning surface in `moira.heliacal`
2. preserve narrow wrappers for concrete planetary events
3. expose generalized policies and generalized search only after V1-V4 are
   complete
4. delay package-root widening until the criterion family and environment
   policy are stable

Do not start with facade-first convenience.

---

## 11. Phase V6 — Optional Enhancements

These are valid, but should remain later:
- moonlight-aware sky brightness
- terrain/horizon profile integration
- stellar catalog-wide heliacal batch search
- observer-experience scaling
- wavelength-specific visibility refinements
- research comparison against multiple visibility doctrines

These are later because they increase model sensitivity and validation burden
faster than they increase core engine truth.

---

## 12. Proposed Data / Policy Objects

Minimum near-term target set:

```python
LightPollutionClass
ObserverAid
ObserverVisibilityEnvironment
VisibilityCriterionFamily
VisibilityPolicy
VisibilitySearchPolicy
VisibilityAssessment
GeneralVisibilityEvent
```

The exact names may change.
The separation of responsibilities should not.

---

## 13. Recommended Implementation Order

The smallest correct path is:

1. V0 constitutional cleanup
2. V1 observer environment policy
3. V2 one admitted visibility criterion family
4. V3 generalized event search surface
5. V4 validation corpus and tolerance doctrine
6. only then wider public exposure

This order is mandatory if light pollution is to be admitted honestly.

If light pollution is added before V1 and V2 are explicit, it will almost
certainly become an undocumented fudge factor rather than a truthful engine
policy.

---

## 14. Immediate Next Move

The immediate next move should be:

1. revise `moira.heliacal` so it distinguishes:
   - current concrete event surfaces
   - current narrow policy vessels
   - still-deferred generalized visibility doctrine
2. define `ObserverVisibilityEnvironment` and `LightPollutionClass`
3. freeze one initial visibility criterion family before any larger event
   widening

That is the smallest path that makes room for light pollution without losing
Moira's engine discipline.
