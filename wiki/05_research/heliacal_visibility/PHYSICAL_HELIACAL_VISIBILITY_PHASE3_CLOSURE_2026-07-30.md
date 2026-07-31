# Physical Heliacal Visibility Phase 3 Closure

Date: 2026-07-30

Status: Complete at the additive Python direct-module engine boundary

Baseline commit: `2141a33bebe9898e1164824c06aba28a8408adeb`

Governing roadmap:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

## Outcome

Phase 3 is closed. Moira now has an opt-in, typed physical event solver whose
reported time is either a certified visibility-margin crossing or an
inspectable domain boundary. It proves first-day or last-day ownership with an
evaluable adjacent guard day and fails closed when dependency, domain, or
crossing-completeness evidence is missing.

This closure does not change a legacy default, legacy heliacal result, facade,
serializer, REST route, OpenAPI schema, or native dispatch path. Those remain
separate later phases.

## Exact Admission

The event admission is:

| Target | Single epoch | Four physical event phases | Disposition |
|---|---:|---:|---|
| Mercury | Yes | No | `body_phase_not_admitted`; source-owned phase domain does not cover every required guard |
| Venus | Yes | No | `body_phase_not_admitted`; source-owned phase domain does not cover every required guard |
| Mars | Yes | Yes | admitted |
| Jupiter | Yes | Yes | admitted |
| Saturn | Yes | Yes | admitted |
| Sirius | Yes | Yes | admitted through exact BSC5/CALSPEC/CIE profile |
| Other fixed stars | No | No | `target_not_admitted` |
| Other bodies | No | No | separate source-and-admission project required |

The four admitted phases remain:

- `morning_first_rising`
- `morning_first_setting`
- `evening_last_rising`
- `evening_last_setting`

The lunar crescent stays on its Yallop-specific path. Legacy fixed-star event
search remains unchanged. Sirius physical assessment and event search never
call the legacy native arcus accelerator.

## Engine Boundary

`moira/_visibility_event_solver.py` owns:

- complete local-mean-solar observation-day construction;
- target and solar boundary scans;
- deterministic scalar caching;
- crossing, tangent, and near-zero receipts;
- certified possible-zero enclosure;
- opening/closing margin-root selection;
- first-day and last-day comparison;
- typed polar, circumpolar, never-rising, and no-boundary outcomes; and
- numerical sensitivity propagation separate from scientific uncertainty.

`moira/heliacal.py` owns:

- the additive public types and direct-module function;
- target/event admission;
- exact pack and certificate binding;
- planetary versus sovereign-star geometry and photometry dispatch;
- target, Sun, atmosphere, observer, horizon, ephemeris, solver, and component
  receipts; and
- compatibility isolation from every legacy path.

The pack's 0.25-degree true-altitude floor can narrow an observation window.
The result reports `target_data_pack_altitude_floor`; it does not call that
numerical domain edge a visual or measured horizon.

## Exact Data Pack

Event search accepts only:

```text
pack_id: moira-physical-heliacal-visibility
version: 1.2.0
manifest_sha256:
  cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c
generation_fingerprint:
  d2907be5084fdb9569457af3b0ac995e8888b2ba3d9317948ba7f1e89a477c0e
stellar_target_profile_sha256:
  de202599761a1a5b49d656fab1c3640d0cc73ca1319c9e5a7c6f44c0c13de22b
payload_file_count: 13
root_file_count_including_manifest: 14
```

Version 1.2 copies all eight inherited Phase 2 payload roles byte-for-byte:

- axes;
- direct extinction;
- error envelope;
- photopic luminance and relative standard error;
- scotopic luminance and relative standard error; and
- Mercury-through-Saturn target profiles.

It adds one generated Sirius profile. The runtime pack contains no CALSPEC
FITS file, BSC5 table, Hipparcos table, CIE source table, libRadtran source, or
network client.

Two separate offline builds produced 14 files each with zero byte
differences. The independent validator rederived Sirius and accepted both
builds without importing the builder or Moira.

## Sirius Source Chain

The first stellar admission binds:

- traditional name `Sirius`;
- nomenclature `alf CMa`;
- HIP 32349;
- HR 2491;
- HD 48915;
- BSC5 Johnson V `-1.46`; and
- a response profile derived from `sirius_stis_005.fits`.

The checksum-locked inputs are:

| Source | SHA-256 |
|---|---|
| STScI CALSPEC `sirius_stis_005.fits` | `1349da7b8b59ad035aefea8d7948f552b41b3897d07e5ad82ca162a53af97271` |
| VizieR BSC5 HR 2491 query | `09556d03431f70c65b75a4a555742812dd542d2e0a4ee40df4c11a876b5fcc3d` |
| BSC5 `ReadMe` | `44fd9c73e2eecad0beb47bdfa3f01c60fd43f93d6964198e31fcd48732de5b33` |
| CIE photopic response | `ee5d5d17922ae645d4af52cacf6a50bdb9385749f9d2181ca312eb2b08febac2` |
| CIE scotopic response | `6a75d3fdbcbf5e9e9a07478511933eefeda953f3e2cc14b74459e5a099ec3759` |

The derivation linearly samples positive CALSPEC data-quality rows at the
integer 380-779 nm bin starts, weights them independently by the two exact CIE
responses, normalizes each response integrand, and derives the base S/P ratio.
The generic sovereign-star `color_index` field is never consumed. Identity or
visual-magnitude drift fails closed.

Source authorities:

- [STScI CALSPEC archive](https://ssb.stsci.edu/cdbs/calspec/)
- [Bohlin 2014 CALSPEC Sirius calibration](https://arxiv.org/abs/1403.6861)
- [VizieR Bright Star Catalogue V/50](https://cdsarc.cds.unistra.fr/viz-bin/cat/V/50)
- [MAST data-use policy](https://archive.stsci.edu/publishing/data-use)

## Crossing-Completeness Certificate

The source-controlled certificate is:

```text
certificate_id:
  physical-heliacal-event-lipschitz-v1
certificate_sha256:
  eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e
exact_pack_manifest_sha256:
  cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c
```

The independent validator caught and repaired an earlier under-bound before
closure. Direct extinction is interpolated in
`log10(target_altitude + 0.25)`, so the relevant maximum derivative is
`12.59259154196714` magnitude per physical altitude degree, not the
`11.239822387695312` endpoint secant.

The independently recomputed limits are:

| Quantity | Derived or exact-pack maximum | Admitted ceiling |
|---|---:|---:|
| Solar true-altitude rate | 363 deg/day | 384 deg/day |
| Target true-altitude rate | 377 deg/day | 512 deg/day |
| Relative solar-azimuth rate | 900.6833536757019 deg/day | 1,024 deg/day |
| Refracted apparent-horizon signal | 754 deg/day | 1,024 deg/day |
| Direct-extinction interpolant contribution | 6,447.406869487176 mag/day | included below |
| Twilight coordinate contribution | 792.2886606140862 mag/day | included below |
| Full derived margin rate | 8,799.984190715348 mag/day | 16,384 mag/day |

The pack's 45-degree target-altitude ceiling excludes the horizontal
coordinate singularity at zenith. Dense sampling is not a certificate.
For each interval, the solver either:

1. excludes zero from an endpoint and the rate bound;
2. recursively encloses a witnessed crossing, tangent, or boundary contact to
   the declared tolerance; or
3. returns `crossing_completeness_not_certified`.

Adversarial tests include two crossings hidden between same-sign coarse
endpoints and a possible-zero interval with no witness. The first is found;
the second fails closed.

## Independent Event Goldens

The source-owned golden is:

```text
tests/golden/physical_visibility_phase3_events.json
sha256:
  8111d662df77b1a8b3f53258fef02a1fcf5f3c21a980e3a48df9a7c5d5838518
```

The independent validator imports neither Moira nor the event solver. It
implements the published pack interpolation, CIE MES2, Crumey threshold, and
target conditioning separately.

### Jupiter

Jupiter and solar airless topocentric geometry, Jupiter apparent magnitude,
and phase angle come from checksum-locked one-minute
[JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html) observer
tables.

```text
site: 35 N, 35 E, sea level
phase: morning_first_rising
independent event_jd_ut: 2460070.591389478
engine event_jd_ut:      2460070.591375516
absolute difference:    1.206350326538086 seconds
guard maximum margin:  -0.09540016026992415 magnitude
oracle tolerance:       60 seconds
```

### Sirius

Sirius airless topocentric geometry uses checksum-locked Hipparcos I/239
astrometry transformed by offline Astropy 7.2.0, PyERFA 2.0.1.5, and pinned
IERS data. Solar geometry comes from Horizons. BSC5/CALSPEC still own the
physical profile and V magnitude; the Hipparcos V field is not substituted.

```text
site: 30 N, 90 W, sea level
phase: morning_first_rising
independent event_jd_ut: 2461255.9502878026
engine event_jd_ut:      2461255.950317484
absolute difference:    2.564460039138794 seconds
guard maximum margin:  -0.3868969046825135 magnitude
oracle tolerance:       60 seconds
```

Both engine results report:

- `visibility_margin_zero`;
- `visibility_margin`;
- `certified_lipschitz_zero_enclosure`;
- the exact certificate SHA-256; and
- zero unresolved certificate intervals.

These one-minute external oracles validate numerical event timing. They do
not convert observer, weather, or atmospheric-model uncertainty into
probabilistic confidence.

## Verification Gates

The Phase 3 focused gate covers:

- all four phase directions;
- first/last guard ownership;
- multiple crossings;
- hidden same-sign crossing pairs;
- tangencies and near-zero intervals;
- root residuals and scan-step convergence;
- deterministic repeat execution;
- pack-floor event semantics;
- polar day/night, circumpolar, no-rise, and no-set truth;
- typed missing ephemeris, pack, profile, and domain failures;
- Mercury/Venus event non-admission before pack loading;
- Sirius catalog drift and generic-color rejection;
- Sirius isolation from legacy native dispatch;
- exact compatibility-contract identity;
- independent pack and certificate tooling import boundaries; and
- exact-pack real Jupiter and Sirius replay.

Offline validators:

```text
scripts/validate_visibility_phase3_data_pack.py
scripts/validate_visibility_phase3_event_certificate.py
scripts/validate_visibility_phase3_event_goldens.py
```

All accept explicit local paths, import no network client, and perform no
download.

The final repository replay on 2026-07-31 under the current validation
harness accepted:

```text
51 focused Phase 3 unit and governance tests
2 exact-pack engine replays: Jupiter and Sirius
3 independent offline validators: pack, certificate, and event goldens
672-case physical-visibility compatibility gate:
  671 passed, 1 pre-existing empty-enumeration skip, 0 failed
```

The exact resting state, external artifact paths, dirty-tree ownership
boundary, and restart commands are preserved in
[PHYSICAL_HELIACAL_VISIBILITY_PHASE3_RESTART_CHECKPOINT_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE3_RESTART_CHECKPOINT_2026-07-30.md).

## Closed Limits

The following are explicit limits, not unfinished Phase 3 work:

- Mercury and Venus physical event search;
- fixed stars other than Sirius;
- Moon, Uranus, Neptune, minor planets, comets, novae, and extended sources;
- optical aids;
- pack extrapolation below -9 degrees solar altitude, below 0.25 degrees
  target altitude, or outside any other exact manifest domain;
- clouds, live weather, and runtime radiative transfer;
- moonlight, site-specific airglow, and directional terrain horizons;
- observer-population probabilities and confidence scores;
- facade, serializer, REST, OpenAPI, and website adoption; and
- native acceleration of the physical model.

Reopening any limit requires a named source, explicit domain, additive
contract proposal, independent validation, and a new admission receipt.

## Next Boundary

Phase 4 remains inactive until explicitly started. It owns moonlight, airglow,
directional/local horizon realism, and related environmental components. It
must not reinterpret this Phase 3 clear-sky, no-moonlight event contract.
