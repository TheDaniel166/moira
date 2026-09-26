# Lunar Orientation And Libration Engine Implementation Plan

**Date:** 2026-09-26

**Goal:** Add a sovereign, public Moira engine product for lunar libration and visible-disc orientation, using the admitted DE441/LE441 translation path and NAIF's high-accuracy DE440 lunar orientation kernel without adding a base Python dependency.

**Architecture:** Python owns the public contract, observer policy, light-time policy, conventions, and provenance. The native extension owns generic DAF summary decoding, binary PCK type-2 Chebyshev evaluation, and the ICRF-to-lunar-PA rotation. Python composes the pinned PA-to-ME fixed rotation, derives sub-observer/subsolar geometry and position angles, and packages an immutable result. Existing lunar-limb/contact code is moved onto the shared internal geometry so Moira has one lunar orientation truth path.

**Primary authorities:**

- NAIF binary PCK and lunar FK documentation and the pinned resources `moon_pa_de440_200625.bpc` and `moon_de440_250416.tf`.
- JPL Horizons observer-table quantities 14-17 as the independent external surface oracle.
- NASA SVS Moon Phase and Libration hourly data as a second geocentric convention/continuity witness.

## Scope

### Included

- Geocentric total apparent libration (optical plus physical) in longitude and latitude.
- Optional topocentric observer support, including diurnal libration.
- Subsolar longitude and latitude.
- Position angle of the lunar north-pole axis.
- Position angle of the bright limb.
- Solar selenographic colongitude.
- Exact kernel/frame/time/light-time provenance and descriptor-derived coverage.
- Native binary PCK type-2 support sufficient for the admitted Moon kernel.
- Public direct function, `moira.sky.observation` export, top-level export, and `Moira` facade method.
- Refactoring of the private lunar-limb/contact path onto the shared orientation substrate.

### Excluded

- Website, Workspace, rendering, texture, NASA image, REST/FastAPI, OpenAPI, or deployment work.
- Optical-versus-physical libration decomposition. V1 exposes the observable total only.
- A low-precision `IAU_MOON` fallback outside the admitted PCK coverage.
- A general-purpose SPICE frame system, arbitrary PCK types 3/20, or arbitrary text-FK evaluation.
- Changes to generic `PlanetPhenomena` phase/illumination semantics.

## Locked Public Contract

Create `moira/lunar_orientation.py` with these public types and function:

```python
@dataclass(frozen=True, slots=True)
class LunarObserver:
    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0


@dataclass(frozen=True, slots=True)
class LunarOrientationSource:
    translation_model: str
    orientation_model: str
    body_fixed_frame: str
    pck_sha256: str
    frame_kernel_sha256: str
    coverage_start_jd_tdb: float
    coverage_end_jd_tdb: float
    light_time_model: str
    input_time_scale: str
    orientation_time_scale: str


@dataclass(frozen=True, slots=True)
class LunarOrientation:
    jd_ut1: float
    observer: LunarObserver | None
    sub_observer_longitude_east_deg: float
    sub_observer_latitude_deg: float
    sub_solar_longitude_east_deg: float
    sub_solar_latitude_deg: float
    axis_position_angle_deg: float
    bright_limb_position_angle_deg: float | None
    solar_colongitude_deg: float
    source: LunarOrientationSource

    @property
    def libration_longitude_deg(self) -> float: ...

    @property
    def libration_latitude_deg(self) -> float: ...


def lunar_orientation_at(
    jd_ut1: float,
    *,
    observer: LunarObserver | None = None,
    reader: SpkReader | None = None,
) -> LunarOrientation: ...
```

Contract rules:

- `observer=None` is geocentric. A `LunarObserver` is WGS-84 geodetic and produces topocentric/diurnal libration.
- Longitude is east-positive and normalized to `[-180, 180)`; latitude is north-positive.
- The two `libration_*` properties are exact aliases of the sub-observer coordinates, not separately computed fields.
- Position angles are normalized to `[0, 360)` and measured eastward/counter-clockwise from true-of-date celestial north in a north-up view.
- `bright_limb_position_angle_deg` is `None` when the projected Moon-to-Sun direction is numerically undefined near exact alignment; it is never assigned an arbitrary zero.
- `solar_colongitude_deg = (90 - sub_solar_longitude_east_deg) % 360`.
- The orientation frame is explicitly `MOON_ME_DE440_ME421`; do not return a generic `MOON_ME` label without the resolved frame identity.
- V1 reports total apparent libration. It must not label the output as optical-only or physical-only.
- An epoch outside the binary PCK descriptor coverage raises a named coverage error. There is no silent model downgrade.

## File Map

### Create

- `moira/lunar_orientation.py` — public vessels, conventions, derivations, and function.
- `moira/_lunar_apparent.py` — shared geocentric/topocentric reception light cone and sky-plane basis.
- `moira/_lunar_orientation_resources.py` — manifest loading, discovery, identity verification, and native handle cache.
- `moira/data/lunar_orientation_de440.json` — pinned resource and frame-transform admission manifest.
- `src/native/include/pck.hpp` — binary PCK descriptors, type-2 evaluator, and rotation matrix.
- `scripts/build_lunar_orientation_authority_fixtures.py` — isolated acquisition of Horizons/SVS authority fixtures.
- `tests/fixtures/lunar_orientation_horizons_calibration.json` — frozen calibration cases.
- `tests/fixtures/lunar_orientation_horizons_holdout.json` — disjoint frozen holdout cases.
- `tests/fixtures/lunar_orientation_svs_2026_holdout.json` — selected rows plus source receipt, not the entire annual dataset.
- `tests/unit/test_native_pck_reader.py` — native PCK happy-path and exact matrix tests.
- `tests/unit/test_adversarial_native_pck_reader.py` — malformed/truncated/wrong-type/boundary tests.
- `tests/unit/test_lunar_orientation.py` — public contract and geometry invariants.
- `tests/integration/test_lunar_orientation_spice_oracle.py` — pinned-kernel `spiceypy.pxform` differential oracle.
- `tests/integration/test_lunar_orientation_authority.py` — frozen Horizons and SVS checks.

### Modify

- `src/native/include/daf.hpp` — generalize raw DAF summaries without weakening the SPK projection.
- `src/native/bindings/moira_native.cpp` — bind the PCK handle/evaluator and release the GIL around file/evaluation work.
- `moira/moira_native.py` — typed/shim exposure if required by the existing import boundary.
- `moira/_kernel_paths.py` — named lunar-orientation resource discovery only if `find_kernel()` is not sufficient.
- `moira/download_kernels.py` — list/install the pinned PCK and FK into the standard kernel directory with exact byte/hash verification.
- `moira/lunar_limb.py` — consume the shared light cone and native `J2000 -> MOON_ME_DE440_ME421` rotation.
- `moira/lunar_occultation_contacts.py` — import the neutral shared light cone rather than a private helper from `lunar_limb`.
- `moira/sky/observation.py`, `moira/__init__.py`, `moira/facade.py`, `moira/_facade_astronomy.py` — public engine exposure.
- `PROVENANCE.md`, `CHANGELOG.md`, `wiki/02_standards/API_REFERENCE.md`, `wiki/03_validation/VALIDATION_ASTRONOMY.md` — contract, authority, and validation evidence.
- `moira.wiki/*` — generated only through `scripts/sync_git_wiki.py`.

## Stage 0: Freeze Authority, Conventions, And Fixtures

- [ ] Record the exact existing assets in `moira/data/lunar_orientation_de440.json`:
  - `moon_pa_de440_200625.bpc`: URL, 12,863,488 bytes, SHA-256 `60cd55aa401ea2ea97360636f567554bfe4e37bb829f901b4460a455dfaf783f`.
  - `moon_de440_250416.tf`: URL, 19,478 bytes, SHA-256 `a47c71e9c9f33796bdafb2c9d69a7ee447b6016ecad80f71cd6f3e479f9cf768`.
  - PCK frame class ID `31008`, inertial frame ID `1`, type `2`.
  - Target frame `31009` / `MOON_ME_DE440_ME421`.
  - PA-to-ME fixed rotation: axes `(3, 2, 1)`, angles `(67.8526, 78.6944, 0.2785)` arcseconds, with the exact FK direction.
- [ ] Capture geocentric and topocentric Horizons quantities 14, 15, 16, and 17 at predeclared epochs covering quarters, full/new proximity, high libration, and both PCK segments.
- [ ] Split fixture epochs before evaluating Moira: calibration establishes gates; holdout remains untouched until gates are frozen.
- [ ] Select a small, disjoint set of hourly 2026 NASA SVS rows containing `subsolar`, `subearth`, and `posangle`; retain URL, fetch timestamp, byte length, and SHA-256.
- [ ] Add fixture-governance tests rejecting overlap, missing source receipts, altered query parameters, and sign-convention ambiguity.

Gate: the convention ledger, resource identities, fixture split, and query receipts are reviewable before computational code is admitted.

## Stage 1: Generalize DAF And Add Native PCK Type 2

- [ ] Replace the SPK-shaped parsing assumption inside `daf.hpp` with a raw DAF summary representation containing exactly `ND` doubles and `NI` integers.
- [ ] Preserve the existing SPK Python descriptor shape by projecting raw summaries only after asserting `locidw == "DAF/SPK"`, `ND == 2`, and `NI == 6`.
- [ ] Add a distinct PCK projection asserting `locidw == "DAF/PCK"`, `ND == 2`, and `NI == 5`; map integers to `(frame_class_id, inertial_frame_id, data_type, start_i, end_i)`.
- [ ] Rename/extract the shared fixed-interval Chebyshev payload reader so SPK type 2 and PCK type 2 share record I/O without sharing semantic types.
- [ ] Implement `NativePckKernelHandle` with exact file identity checks, descriptor coverage lookup, segment precedence, bounded cache, and close semantics.
- [ ] Evaluate RA/DEC/W at explicit JD TDB and construct the inertial-to-PA matrix using the NAIF rotation order.
- [ ] Compose the fixed PA-to-ME rotation from the admitted manifest values; reject a manifest/kernel frame mismatch.
- [ ] Bind `open_pck_kernel()`, catalog metadata, coverage, Euler-angle diagnostics, and `rotation_matrix(jd_tdb)` with GIL release.

Tests must cover:

- synthetic little- and big-endian DAF/PCK summaries;
- `NI=5` packing (the current SPK-shaped parser misreads this and must not remain reachable);
- malformed `ND/NI`, wrong identification word, unsupported PCK type, invalid addresses, truncated directory/record, NaN metadata, and out-of-coverage epochs;
- the shared boundary between the two real kernel segments;
- rotation orthonormality, determinant `+1`, matrix/inverse round-trip, and thread-safe cache behavior;
- no behavior change in existing SPK reader and identity tests.

Gate: pinned-kernel native `J2000 -> MOON_PA_DE440` and composed `J2000 -> MOON_ME_DE440_ME421` matrices agree with `spiceypy.pxform` across calibration epochs and segment edges. Start with a `2e-12` maximum absolute matrix-element ceiling; tighten to the measured numerical floor before holdout.

## Stage 2: Resource Admission And Acquisition

- [ ] Load the packaged JSON manifest with schema, type, finite-value, URL, byte-length, digest, frame-ID, and axis-sequence validation.
- [ ] Resolve resources from the standard kernel search roots. Accept the existing lunar-limb cache only as an explicitly tested legacy discovery location during migration.
- [ ] Verify the exact PCK and FK byte identities before opening the native handle.
- [ ] Add named errors for missing resource, identity mismatch, unsupported descriptor, and coverage failure.
- [ ] Extend `moira-download-kernels --list` and acquisition so the two lunar-orientation resources can be installed deliberately; computation itself performs no network access.
- [ ] Cache handles by resolved path plus verified identity. Do not use global SPICE kernel-pool state.

Gate: public imports remain side-effect free, `[project].dependencies` remains empty, and a process without `spiceypy`, `requests`, or `laspy` can compute lunar orientation when the admitted PCK is installed.

## Stage 3: Shared Lunar Apparent Geometry

- [ ] Move `_TopocentricMoonLightCone` and `_reader_bound_moon_light_cone` out of `lunar_limb.py` into `moira/_lunar_apparent.py`; rename them without topography-specific language.
- [ ] Add the geocentric branch by using the Earth-center SSB reception state instead of a WGS-84 site offset.
- [ ] Preserve the content-identified DE441/LE441 requirement and the iterative Moon-to-observer down-leg light time.
- [ ] Add the Moon-to-Sun up-leg solve at the lunar emission/reflection epoch for the apparent subsolar direction.
- [ ] Produce one immutable internal context containing:
  - reception UT1/TT and lunar-emission TT/TDB;
  - observer and Sun directions in ICRF;
  - true-of-date north/east sky basis;
  - observer distance and translation identity.
- [ ] Keep annual/diurnal aberration policy explicit. Calibrate against Horizons before freezing it; do not copy the contact solver's physical-ray exclusion into a visual orientation contract without evidence.
- [ ] Update lunar-limb/contact consumers to use this shared context while retaining their existing airless physical-ray doctrine.

Gate: existing lunar-limb and lunar-occultation tests remain unchanged numerically, and geocentric/topocentric light-time vectors match the pinned SPICE/Horizons calibration cases within the frozen gates.

## Stage 4: Public Lunar Orientation Product

- [ ] Validate `jd_ut1`, observer latitude/longitude/elevation, and reader identity before kernel evaluation.
- [ ] Evaluate `J2000 -> MOON_ME_DE440_ME421` at the retarded lunar-emission TDB epoch.
- [ ] Rotate Moon-to-observer and Moon-to-Sun directions into ME and derive sub-observer/subsolar longitude and latitude.
- [ ] Project lunar north onto the true-of-date sky plane for `axis_position_angle_deg`.
- [ ] Project the apparent Moon-to-Sun direction for `bright_limb_position_angle_deg`; return `None` for the singular aligned case.
- [ ] Derive solar colongitude from the east-positive subsolar longitude.
- [ ] Construct immutable source provenance from the verified translation and orientation identities.
- [ ] Export through:
  - `moira.lunar_orientation`;
  - `moira.sky.observation`;
  - `moira.__init__`;
  - `Moira.lunar_orientation(dt, observer=None)` delegating through the instance reader.
- [ ] Add export-policy, facade-delegation, frozen-dataclass, repr/serialization-neutrality, and no-hidden-default tests.

Gate: all range, sign, alias, singularity, geocentric/default, and topocentric/diurnal-libration tests pass. The public product has no transport dependency and no optional-extra import requirement.

## Stage 5: External Validation And Regression Closure

- [ ] Run native-versus-SPICE matrix and final-field differentials over calibration epochs, random in-coverage epochs, both segment boundaries, and longitude/PA wrap crossings.
- [ ] Freeze tolerances from calibration only. Initial external ceilings are:
  - Horizons sub-observer/subsolar longitude and latitude: `0.001 deg`;
  - Horizons axis/subsolar position angles: `0.001 deg` away from singular alignment;
  - NASA SVS rounded hourly subpoints and axis PA: `0.01 deg`.
- [ ] Fail on systematic sign, `180 deg`, `90 deg`, frame, or time-scale offsets even if a circular residual could be hidden by a broad tolerance.
- [ ] Run the untouched Horizons and SVS holdout fixtures.
- [ ] Add invariants:
  - longitude/latitude/PA domains;
  - `libration_* == sub_observer_*` exactly;
  - colongitude identity modulo 360;
  - geocentric result is independent of Earth longitude inputs because none are accepted;
  - topocentric-minus-geocentric difference is bounded and changes with site/UT1;
  - continuous unwrapped tracks across `-180/180` and `0/360` crossings;
  - exact failure outside PCK coverage and on resource drift.
- [ ] Run existing lunar-limb, occultation, phase, kernel-reader, native GIL/threading, export, and documentation gates.

Suggested focused commands:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,lunar-graze]"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_native_pck_reader.py tests\unit\test_adversarial_native_pck_reader.py tests\unit\test_lunar_orientation.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests\integration\test_lunar_orientation_spice_oracle.py tests\integration\test_lunar_orientation_authority.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests\unit\test_spk_reader.py tests\unit\test_adversarial_native_daf_reader.py tests\unit\test_native_runtime_verification.py tests\unit\test_lunar_limb_event_profile.py tests\unit\test_lunar_occultation_contacts.py -q -p no:cacheprovider
```

Final gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not external_network" -q -p no:cacheprovider
.\.venv\Scripts\python.exe scripts\sync_git_wiki.py
.\.venv\Scripts\python.exe scripts\sync_git_wiki.py --check
```

## Suggested Commit Boundaries

1. `test(lunar-orientation): freeze authority fixtures and conventions`
2. `feat(native): add admitted binary PCK type-2 evaluation`
3. `feat(resources): admit DE440 lunar orientation assets`
4. `refactor(lunar): share reader-bound apparent geometry`
5. `feat(lunar): expose orientation and libration product`
6. `docs(lunar): publish orientation provenance and validation`

Do not commit or push from this planning task. Implementation begins only after separate authorization.

## Critical Path And Principal Risks

1. **DAF descriptor correctness:** PCK uses `NI=5`; the existing SPK-shaped summary fields are observably shifted when reading the real PCK. This must be repaired at the raw DAF layer without changing SPK behavior.
2. **Frame direction/order:** Binary PCK yields `J2000 -> MOON_PA_DE440`; the FK angles define the PA/ME relationship with an explicitly documented inverse. Matrix order must be proven against `pxform`, not inferred from labels.
3. **Time semantics:** translation uses reader-bound TT states; PCK uses TDB seconds; the orientation matrix is evaluated at retarded lunar emission, not reception UT1.
4. **Apparent versus physical ray:** lunar contacts intentionally exclude observer-motion aberration, while a visible-disc orientation product may need Horizons-compatible apparent sky-basis treatment. Stage 3 calibration must freeze this distinction explicitly.
5. **Convention drift:** longitude sign and position-angle zero/direction are API, not presentation details. Unambiguous field names and wrap-aware tests are mandatory.
6. **Resource drift:** the 12.8 MB PCK is external to the wheel. Computation must fail closed on missing or mismatched bytes and never auto-download.
7. **False decomposition:** the DE-integrated body orientation plus observer geometry gives total apparent libration; it does not independently expose optical and physical components. V1 must remain honest about that boundary.

## Completion Definition

The work is complete only when a clean base installation with the admitted lunar PCK can call `lunar_orientation_at()` without `spiceypy`, return convention-explicit geocentric and topocentric results with immutable provenance, match the pinned native/SPICE and external authority gates, preserve current lunar-contact behavior, pass the non-network suite, and leave all website/REST code untouched.
