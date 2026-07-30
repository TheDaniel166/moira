# Physical Heliacal Visibility Admission Doctrine

Date: 2026-07-29
Status: Phase 0 doctrine lock; implementation not yet admitted
Governing roadmap:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

## Purpose

This document freezes the meanings, supported domain, failure law, data
boundary, and additive public-contract shape for Moira's physical
heliacal-visibility project.

It is an implementation authority, not a claim that the physical event model
already exists. The existing legacy search remains the admitted public
behavior until the later implementation, validation, transport, and release
gates close.

## Compatibility Boundary

The existing `HeliacalEventKind` enum is frozen with these six strings:

- `heliacal_rising`
- `heliacal_setting`
- `acronychal_rising`
- `acronychal_setting`
- `cosmic_rising`
- `cosmic_setting`

Their current calculations, defaults, return shapes, `None` behavior, facade
behavior, and REST projection remain legacy contracts. The modernization must
not:

- rename or remove a legacy value;
- reinterpret a legacy value through the new physical model;
- change a legacy default;
- add mandatory request fields to a legacy route;
- add physical-only fields to a legacy response;
- route a physical fixed-star event through the legacy native arcus search; or
- describe the legacy values as exact equivalents of the new taxonomy.

The current `CRUMEY_2014_POINT_SOURCE` single-epoch assessment also remains
unchanged. It is not silently widened from its admitted scotopic astronomical
domain into a twilight event criterion.

## Physical Model Identity

The first composite physical model identifier is:

```text
clear_sky_naked_eye_point_source_v1
```

This is a first-class immutable model family, not a moving alias for “best
available.” A policy preset may select it, but the preset must resolve to this
exact identifier and expose every component identity.

The initial component identities are planned as:

| Component | Frozen identifier | Role |
|---|---|---|
| Directional atmosphere | `libradtran_2_0_6_mystic_spherical_v1` | Offline-generated transmission and twilight radiance |
| Point-source detection | `blackwell_crumey_full_range_point_source_v1` | Detection threshold across the generated twilight luminance domain |
| Spectral response | `cie_mes2_2010_v1` | Declared photopic/scotopic interpolation, never an unnamed conversion |
| Observational lineage | `tousey_koomen_twilight_1953_v1` | Independent twilight comparison cases |

These identifiers are reserved by this doctrine. They do not become admitted
API until their source, numerical, packaging, and public-contract gates pass.

## Physical Phase Taxonomy

The new public enum is planned as `PhysicalVisibilityPhase` with exactly these
four strings:

| Value | Within-day event | Across-day ownership |
|---|---|---|
| `morning_first_rising` | Opening of a visible interval connected to the target's apparent rising before apparent sunrise | First qualifying morning after a non-qualifying morning |
| `morning_first_setting` | Closing of a visible interval connected to the target's apparent setting before apparent sunrise | First qualifying morning after a non-qualifying morning |
| `evening_last_rising` | Opening of a visible interval connected to the target's apparent rising after apparent sunset | Last qualifying evening before a non-qualifying evening |
| `evening_last_setting` | Closing of a visible interval connected to the target's apparent setting after apparent sunset | Last qualifying evening before a non-qualifying evening |

This follows the four visible phases summarized from Ptolemy by Schironi:
morning rising and setting are first appearances before sunrise; evening
rising and setting are last appearances after sunset.

The words `heliacal`, `acronychal`, and `cosmic` are not used in this new enum.
Modern usage of those labels is not consistent enough to carry the exact
event law without the morning/evening, first/last, and rising/setting terms.

Legacy cosmic events remain legacy geometrical events. They are outside the
new physical four-phase taxonomy.

## Observation-Day Law

The API receives longitude but not a civil timezone. It therefore must not
invent a civil date.

The physical solver assigns samples to a deterministic local mean solar day:

```text
observation_day_key = floor(jd_ut + 0.5 + longitude_deg / 360)
```

`longitude_deg` uses Moira's existing east-positive convention.

The key identifies the candidate local observing day. Results also return the
complete UT Julian dates, so callers with a civil-time authority can project
the event themselves.

`search_window_days` limits candidate phase-day keys. The solver may inspect
one guard day before or after that interval solely to prove first/last
ownership. A guard day cannot be returned as the requested event unless it is
inside the caller's candidate interval.

## Observation-Window Law

For each candidate day, the solver constructs the connected interval in
which:

- the target is at or above the admitted local horizon;
- the event is on the required morning or evening side of the Sun;
- solar and target geometry remain inside the physical data manifest;
- every required atmosphere, target, observer, and background dependency is
  evaluable; and
- the physical model is otherwise inside its admitted domain.

Morning windows end at apparent sunrise. Evening windows begin at apparent
sunset. Apparent sunrise and sunset use the same refraction and horizon policy
as the returned window receipt.

A day qualifies only when a non-empty visible interval is connected to the
relevant apparent target rising or setting. An isolated visibility island
elsewhere in the night does not qualify as that target phase.

The visibility margin is:

```text
visibility_margin(t)
    = limiting_magnitude(t) - conditioned_target_magnitude(t)
```

The boundary rule is:

- rising phases own the opening boundary, `not_visible -> visible`;
- setting phases own the closing boundary, `visible -> not_visible`.

If the horizon itself creates the transition, the threshold time may coincide
with the apparent target rise or set. Otherwise the event time is the refined
zero of the physical visibility margin inside the connected window.

The event receipt distinguishes `visibility_margin` and `target_horizon`
boundary sources. A margin-root residual is required only for a
`visibility_margin` boundary; it is not fabricated as zero for a horizon
boundary.

The solver must find every candidate crossing and must separately detect a
tangent or near-zero interval. Returning the first sampled visible time is
not an event solution.

## First-Day and Last-Day Law

A morning phase is returned only if:

1. the current morning qualifies;
2. the immediately preceding comparable morning does not qualify; and
3. both day classifications are evaluable.

An evening phase is returned only if:

1. the current evening qualifies;
2. the immediately following comparable evening does not qualify; and
3. both day classifications are evaluable.

Missing evidence on either comparison day is not treated as “not visible.”
It makes first/last ownership not evaluable.

## Supported Physical Domain

### Target class

The first admission is:

- binocular, unaided human vision;
- unresolved, steady point sources;
- a deliberate directed observation at a known target position;
- cloud-free atmosphere;
- deterministic named observer and environment inputs; and
- no live weather or ambient network access.

`binocular` here means use of both unaided eyes, not binocular optical
equipment.

The observer protocol identifier is:

```text
known_location_directed_observation_v1
```

It assumes a continuous non-flickering target, natural pupils, and foveal or
near-foveal attention after adaptation to the modeled directional field.
Casual discovery, wide-field search, peripheral detection, flicker, and a
population probability are different experiments and are not silently
represented by an experience or confidence slider.

If the admitted threshold equations require a fixed field factor, the value
and source equation are part of the component receipt. It is not a mutable
proxy for observer skill.

The first planetary candidates are Mercury, Venus, Mars, Jupiter, and Saturn.
A planet enters the public model only after its dynamic visual magnitude and
target spectral treatment carry source receipts and pass independent
validation.

A fixed star enters only when its identity, visual photometry, and spectral or
color transformation are source-identified and complete. An ambiguous catalog
`color_index` must not be guessed to be B-V, Gaia BP-RP, or another system.

Uranus, Neptune, minor planets, comets, novae, and other targets require
separate target-admission evidence. They are not accepted merely because the
ephemeris layer can calculate a position.

### Excluded bodies and aids

- The Sun is excluded from the point-source model.
- The lunar crescent remains governed by its Yallop-specific policy.
- Telescopes, binoculars, cameras, polarizers, and optical filters are
  excluded.
- Extended objects and resolved-source morphology are excluded.

### Hard outer envelope

Phase 1 may narrow these limits after grid and error measurements. It may not
widen them without amending this doctrine.

| Quantity | Hard outer envelope | Unit or convention |
|---|---:|---|
| Spectral integration | 380 to 780 | nm |
| Solar-center altitude | -18 to 0 | geometric degrees |
| Target altitude used by radiative transfer | -1 to 45 | true geometric degrees |
| Relative solar azimuth | 0 to 180 | absolute degrees |
| Observer altitude | 0 to 5,000 | m above mean sea level |
| Surface pressure | 500 to 1,100 | hPa |
| Aerosol optical depth | 0 to 1 | AOD at 550 nm |
| Angstrom exponent | 0 to 2.5 | dimensionless |
| Total ozone column | 200 to 500 | Dobson units |
| Ground albedo | 0 to 1 | dimensionless |
| Relative humidity | 0 to 100 | percent |
| Near-surface temperature | 180 to 330 | K |

The generated data-pack manifest is the effective numerical domain. A point
inside this outer envelope but outside the manifest still fails closed. No
dimension may be extrapolated.

### Refraction

The horizon/window decision uses apparent altitude. Directional radiative
transfer uses true line-of-sight geometry. Both values and the refraction
model identity survive in the receipt. Refraction is applied exactly once.

### Horizon

The initial physical admission supports an explicit scalar apparent horizon
altitude. A directional azimuth/elevation horizon profile enters only after
Phase 4 closes.

For the later profile:

- azimuth is normalized to `[0, 360)`;
- interpolation is linear between sorted samples;
- the last-to-first segment wraps through 360 degrees;
- duplicate azimuths, gaps beyond the admitted maximum, and missing coverage
  fail validation; and
- no missing direction falls back silently to zero altitude.

## Input Precedence and Completeness

Background authority is resolved in this order:

1. measured directional spectral radiance at the target direction and time;
2. measured directional photopic/scotopic luminance with its weighting
   function and spectral assumptions;
3. the declared libRadtran directional twilight table plus a measured
   dark-sky anchor; or
4. a named atmosphere plus an explicitly enabled coarse Bortle fallback.

Only one authority may supply the same physical component. A measured
background that already contains airglow, zodiacal light, integrated
starlight, or artificial light cannot be combined with modeled copies of
those components.

An SQM input must record:

- device or bandpass identity;
- pointing direction and field;
- observation time or declared temporal applicability;
- source unit;
- conversion formula;
- spectral response or S/P assumption; and
- whether it is the total background or only a dark-sky anchor.

An unqualified scalar SQM value cannot become a spectral twilight background.

A named atmosphere profile must resolve and receipt every value it supplies.
Pressure may be derived from altitude only through a named atmospheric
profile, with the profile, equation, source, and derived value reported.
Caller-supplied values override profile values only when the policy explicitly
allows the override and the receipt marks it.

Required units are:

- pressure: hPa;
- AOD: dimensionless at 550 nm;
- Angstrom exponent: dimensionless;
- ozone: Dobson units;
- albedo: dimensionless;
- temperature: K;
- relative humidity: percent; and
- radiance: SI spectral radiance with wavelength unit named.

Bortle is a coarse compatibility input. It is never inferred from location and
is used only when the caller explicitly selects the coarse fallback.

## Data-Pack and Offline Boundary

The physical reference table is not bundled in the MIT engine wheel.

It is a separately versioned, immutable, checksummed visibility data pack with:

- its own semantic data version;
- format and model identifiers;
- a manifest SHA-256;
- per-file SHA-256 values;
- source and generator receipts;
- a CC BY-SA 4.0 notice for incorporated CIE response data; and
- an explicit compatible engine-contract range.

The engine wheel may include only a metadata-only compatibility manifest. The
runtime accepts an explicit caller-supplied data-pack path. Normal calculation
never downloads or updates the pack.

Missing, incompatible, or corrupt data is a typed non-evaluable outcome.

libRadtran remains an external GPL reference generator. No libRadtran source,
binary, Python binding, or runtime invocation enters the engine or data pack.
Only generated numerical products, complete generator configuration, and
provenance receipts may cross the build boundary.

This is the project's packaging disposition, not legal advice. Release notice
and artifact review remain mandatory before public distribution.

## Additive Public-Contract Sketch

Planned Python types:

- `PhysicalVisibilityPhase`
- `PhysicalVisibilityStatus`
- `PhysicalVisibilityPolicy`
- `PhysicalVisibilityAssessment`
- `PhysicalVisibilityEventResult`
- `VisibilityDataPackReceipt`
- `VisibilityComponentReceipt`

Planned functions:

```text
physical_visibility_assessment(...)
    -> PhysicalVisibilityAssessment

physical_visibility_event(...)
    -> PhysicalVisibilityEventResult
```

The assessment request carries:

- target identity;
- `jd_ut`, latitude, and east-positive longitude;
- the full `PhysicalVisibilityPolicy`; and
- an optional source-identified target photometry vessel where the admitted
  target contract allows caller-supplied photometry.

The event request additionally carries:

- one `PhysicalVisibilityPhase`;
- `search_window_days`; and
- deterministic scan/root policy fields inside a typed search policy.

`PhysicalVisibilityPolicy` carries:

- the exact composite model identifier;
- expected data-pack identifier and optional expected manifest SHA-256;
- named atmosphere profile and permitted explicit overrides;
- exactly one background authority;
- the fixed observer-protocol identifier;
- scalar apparent horizon altitude;
- refraction policy; and
- explicit coarse-fallback permission.

The local data-pack filesystem path is runtime configuration, not scientific
policy. Python receives it through a dedicated `VisibilityDataPackConfig` or
engine configuration. A REST client never supplies an arbitrary server path.
The REST deployment binds its allowed pack path and clients may assert only
the expected public pack identity/checksum.

Planned dedicated REST routes:

```text
POST /v1/visibility/physical-assessment
POST /v1/visibility/physical-event
```

The legacy `/v1/visibility/assessment` and
`/v1/heliacal/visibility-event` routes remain exact compatibility surfaces.

Every physical result returns a status:

- `evaluated`: the requested truth was computed;
- `not_evaluable`: required evidence or domain support was absent; or
- `not_found`: the search was evaluable but no requested phase transition
  occurred inside the candidate interval.

An event result includes:

- target and phase identity;
- `observation_day_key`;
- primary `event_jd_ut`;
- apparent target rise/set JD;
- observation-window start and end JD;
- peak-margin JD and margin;
- boundary role and crossing direction;
- boundary source and an applicable-or-not-applicable root residual;
- target, Sun, observer, horizon, atmosphere, background, refraction,
  ephemeris, model, and data-pack receipts;
- solver scan, bracket, residual, and time tolerances; and
- an optional deterministic sensitivity interval that is not called
  probabilistic confidence.

`VisibilityDataPackReceipt` includes:

- pack identifier and semantic data version;
- format version;
- manifest SHA-256;
- per-file SHA-256 map;
- supported model identifiers;
- generator-receipt SHA-256;
- source dataset identifiers;
- license/notice identifier; and
- declared engine-contract compatibility range.

## Stable Non-Evaluable Reasons

The following identifiers are reserved:

- `visibility_data_pack_missing`
- `visibility_data_pack_incompatible`
- `visibility_data_pack_checksum_mismatch`
- `target_not_admitted`
- `target_spectral_profile_missing`
- `target_photometry_missing`
- `solar_altitude_out_of_domain`
- `target_altitude_out_of_domain`
- `observer_altitude_out_of_domain`
- `atmosphere_input_incomplete`
- `atmosphere_input_out_of_domain`
- `background_input_incomplete`
- `background_components_conflict`
- `local_horizon_coverage_missing`
- `solar_rise_missing`
- `solar_set_missing`
- `target_rise_missing`
- `target_set_missing`
- `no_valid_observation_window`
- `criterion_out_of_domain`
- `adaptation_state_incomplete`
- `observer_protocol_not_admitted`
- `phase_ownership_not_evaluable`
- `solver_domain_disconnected`

The stable `not_found` reason is:

- `no_phase_transition_in_search_window`

Polar day, polar night, circumpolarity, and never-rising geometry are not
collapsed into one label. The specific missing solar or target boundary is
reported.

## Closed Exclusions

The first physical admission excludes:

- clouds and live weather;
- runtime radiative-transfer execution;
- runtime network access and automatic downloads;
- optical aids;
- extended sources;
- direct solar visibility;
- lunar-crescent visibility;
- targets without admitted photometry and spectral treatment;
- global airglow inferred from a single observatory;
- a directional horizon profile before Phase 4;
- observer-population probabilities;
- a synthetic confidence score;
- astrological interpretation; and
- a change to any existing default.

An exclusion is not a backlog defect. Reopening it requires a named source,
new validity domain, additive contract proposal, independent validation, and
an admission receipt.

## Phase 0 Decision

The physical doctrine is frozen for implementation planning:

- exact phase names and first/last ownership are explicit;
- event time is a physical boundary, not the first visible sample;
- legacy names and routes remain untouched;
- supported targets and hard exclusions are explicit;
- input precedence and no-double-counting law are explicit;
- physical data is an offline caller-supplied data pack;
- missing evidence is typed rather than fabricated; and
- the later public work is additive.

Any implementation that contradicts this document must stop and amend Phase 0
before continuing.
