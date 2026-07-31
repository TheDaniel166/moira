# Physical Heliacal Visibility Phase 3 Checkpoint

Date: 2026-07-30

Status: Archived implementation checkpoint; superseded by Phase 3 closure

Governing roadmap:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

Baseline commit: `2141a33bebe9898e1164824c06aba28a8408adeb`

> Historical checkpoint only. The open gates and present-tense implementation
> statements below describe the earlier planetary checkpoint, not current
> engine truth. They were resolved by
> [PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CLOSURE_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CLOSURE_2026-07-30.md).

## Purpose

This checkpoint records the implemented Python physical visibility-event
solver without claiming the Phase 3 exit gate. It preserves the Phase 0
four-phase doctrine, consumes the Phase 2 single-epoch visibility margin, and
does not alter legacy event policy, lunar crescent search, facade, REST, or
native dispatch.

## Implemented Engine Boundary

The numerical core in `moira/_visibility_event_solver.py` now provides:

- a deterministic bounded scalar scan with typed evaluations;
- explicit non-evaluable gaps rather than negative or invisible defaults;
- refinement of every witnessed sign-changing bracket;
- distinct crossing, tangent, and near-zero receipts;
- solar-side, target-horizon, and data-pack-domain window intersection;
- separate polar-day, polar-night, circumpolar, never-rising, and
  never-setting geometry states;
- one-day qualification; and
- first-morning and last-evening ownership with an evaluable guard day.

The additive direct-module contract in `moira/heliacal.py` now provides:

- `PhysicalVisibilityPhase` with the four Phase 0 values;
- `PhysicalVisibilitySearchPolicy`;
- typed observation-window, solver, sensitivity, horizon, and ephemeris
  receipts;
- deterministic propagation of the Phase 2 data-pack numerical margin
  envelope through first/last event ownership;
- `PhysicalVisibilityEventResult`; and
- `physical_visibility_event(...)`.

The event function currently admits only Mercury, Venus, Mars, Jupiter, and
Saturn because those are the only targets carried by the immutable Phase 2
version 1.1 target-profile contract. A fixed-star request returns
`target_not_admitted` before pack loading or legacy/native dispatch.

No root export, `moira.sky.visibility` re-export, facade method, serializer,
REST model, route, or OpenAPI change is made at this checkpoint. Those remain
Phase 5 work.

## Four-Phase Behavior

| Physical phase | Window connection | Owned margin transition | Across-day proof |
|---|---|---|---|
| `morning_first_rising` | apparent target rise before apparent sunrise | not visible to visible | preceding morning does not qualify |
| `morning_first_setting` | apparent target set before apparent sunrise | visible to not visible | preceding morning does not qualify |
| `evening_last_rising` | apparent target rise after apparent sunset | not visible to visible | following evening does not qualify |
| `evening_last_setting` | apparent target set after apparent sunset | visible to not visible | following evening does not qualify |

If the target horizon itself opens or closes the visible interval, the primary
time is typed as `apparent_target_horizon`. Otherwise it is the refined
`visibility_margin_zero`. A horizon result does not fabricate a zero margin
residual. A margin result exposes its bracket, iterations, residual, and root
tolerances.

## Domain and Failure Containment

The effective version 1.1 manifest domain, not the wider Phase 0 outer
envelope, controls every search window. The presently admitted pack narrows
solar-center altitude to `[-9, 0]` degrees and target true altitude to
`[0.25, 45]` degrees.

The solver first finds the physical apparent target rise or set over the
complete morning or evening side. It then intersects that geometry with the
solar and target manifest domains. This distinction prevents a pack-domain
boundary from being mislabeled as a missing physical rise or set.

If the target is already nominally visible when a manifest-domain boundary
clips away the physical horizon transition, the event fails closed as
`target_altitude_out_of_domain`. Missing ephemeris evidence remains
`ephemeris_dependency_missing`; it is not collapsed into invisibility.

## Receipt Boundary

The result separates:

- solver coverage and precision;
- the selected margin bracket and residual;
- event-time semantics;
- data-pack numerical sensitivity;
- atmospheric-scenario sensitivity; and
- probabilistic confidence.

No probabilistic confidence is claimed. The current checkpoint explicitly
reports:

```text
crossing_completeness_state =
    bounded_sampling_not_formally_certified

data_pack_numerical_event_interval_jd_ut =
    lower and upper event times from the Phase 2 margin envelope

atmospheric_scenario_reason =
    explicit_admitted_atmospheric_scenario_bounds_required
```

The data-pack interval is deterministic propagation of the admitted numerical
envelope. It is not a probability interval. Atmospheric scenarios remain
separate and require explicit admitted scenario bounds.

## Verification

Runtime: repository `.venv`, Python 3.14.3, offline mode, strict known-issue
policy.

Because unrelated in-progress test-harness edits currently prevent collection
in the primary working tree, the authoritative checks used a clean detached
worktree at the baseline commit with only the Phase 3 files overlaid. No
unrelated working-tree file was staged or changed by those checks.

Focused Phase 3 gate:

```text
tests/unit/test_visibility_event_solver.py
tests/unit/test_physical_visibility_event.py

35 passed
```

The focused gate covers:

- multiple crossings;
- exact and off-grid tangencies;
- near-zero non-roots;
- non-evaluable gaps;
- scan-step convergence;
- deterministic repeat execution;
- all four public phase meanings;
- target-horizon and margin-owned events;
- first-day and last-day ownership;
- root bracket and residual inspection;
- lower and upper data-pack numerical event-time propagation;
- polar day, polar night, circumpolar, no-rise, and no-set states;
- actual version 1.1 manifest-domain clipping;
- missing ephemeris containment;
- fixed-star rejection before pack/native dispatch; and
- a deterministic event-time shift when the admitted AOD input changes.

The broader visibility compatibility gate collected 657 cases across the
Phase 1 pack, Phase 2 LUT/spectral/target surfaces, legacy physical and
heliacal policies, planetary and fixed-star legacy events, validation
corpora, apparent-magnitude references, adversarial public behavior, and the
existing server visibility route:

```text
656 passed
1 skipped: pre-existing empty optional validation enumeration
0 failed
0 deselected
```

The active DE441 reader was also exercised offline for the Sun and all five
admitted planets through the same true-horizontal geometry dependency used by
the event solver.

## Exact-Pack Event Probe

The exact admitted version 1.1 pack survived in the local WSL artifact cache
and was opened read-only from the Windows engine through:

```text
\\wsl.localhost\Ubuntu\home\nilad\.cache\moira\
visibility-reference-lab\data-packs\
moira-physical-heliacal-visibility-1.1.0-v3
```

Its root manifest remained:

```text
f594fd12058cc7f5c7bc9de7f2b06652bef3c0604ef7b0a05a069e54e4026c87
```

The Phase 2 Venus single-epoch path evaluated through that pack with all eight
component receipts. The Phase 3 Jupiter morning-first-rising path then
evaluated with the default five-minute scan and quarter-second root policy:

```text
body: Jupiter
phase: morning_first_rising
latitude_deg: 35
longitude_deg: 35
observation_day_key: 2460071
comparison_observation_day_key: 2460070
comparison_day_status: does_not_qualify
event_jd_ut: 2460070.591375515796
event_time_semantics: visibility_margin_zero
boundary_source: visibility_margin
visibility_margin_residual_magnitude: 0.00000329627889073
data_pack_numerical_event_interval_jd_ut:
  [2460069.5928249373, 2460071.5901005096]
component_receipt_count: 8
```

The nominal event lies inside the existing independently implemented
repository validation window `2460050-2460110` for the 2023 post-conjunction
Jupiter morning apparition. That broad legacy window is useful corroboration,
but it is not promoted into the source-owned Phase 3 golden required for
closure.

### Real-pack domain findings

The exact pack also proved that Phase 2 single-epoch admission is not the same
as complete Phase 3 event ownership:

- a Venus morning-first-rising probe reached a qualifying day at key
  `2459012`, but the required preceding day `2459011` returned
  `target_spectral_profile_out_of_domain`;
- a Venus evening-last-setting probe reached a qualifying day whose following
  guard returned `target_altitude_out_of_domain`; and
- version 1.1 starts target true altitude at `0.25` degrees, so it cannot own
  an apparent-horizon transition whose refracted true altitude lies below that
  floor.

The solver correctly returns `phase_ownership_not_evaluable` in those cases.
It must not reinterpret an out-of-domain guard as a non-qualifying day.

The exact-policy event probe also reached a Phase 2 boundary defect:
finite-precision CIE MES2 coefficients evaluated slightly below zero just
above `0.005 cd/m2` and slightly above one just below `5 cd/m2`. The engine now
clamps the rounded formula to the declared piecewise endpoints, with focused
regressions at both adjacent floating-point values. This prevents a raw
`ValueError` from escaping during numerical event-envelope propagation without
changing the CIE equations or their official example results.

## Windows Receipt Reproducibility Repair

The broad clean-checkout gate found a pre-existing Windows-only failure in
Phase 1 byte receipts. `core.autocrlf=true` changed byte-hashed Phase 1 JSON
and Python tooling files in a new worktree because the Phase 2
`.gitattributes` repair covered only Phase 2 artifacts.

The attribute contract now pins every byte-hashed Phase 1 visibility spec,
checkpoint, builder, validator, and radiance-response validator to LF. The
two previously failing receipt checks pass with the source-controlled byte
counts and SHA-256 values.

## Open Gates Before Phase 3 Closure

### 1. Crossing-completeness admission

The scan covers the entire bounded interval at a declared maximum step and
adaptively refines witnessed structure. That is not a proof that two
same-interval crossings cannot occur between same-sign samples.

Phase 3 needs an admitted temporal derivative/curvature bound, an interval
method, or another defensible certification rule tied to the physical margin.
Until then, the result remains explicitly
`bounded_sampling_not_formally_certified`, and the roadmap statement that no
valid crossing can be skipped stays unchecked.

### 2. Event-complete planetary data domains

Version 1.1 is admitted for the five Phase 2 single-epoch target profiles, but
its effective domains do not close every Phase 3 first/last ownership proof.
Before public physical events, source-backed pack work must determine:

- how the direct-extinction surface can reach the apparent-horizon true
  altitude required by the Phase 0 boundary law;
- how Mercury and Venus spectral/color treatment can cover the conjunction
  side needed by their first/last guard days; and
- whether any body/phase pair remains intentionally unsupported after those
  source gates.

This is a data/source admission problem. Missing guards must continue to fail
closed; the solver must not manufacture continuity across the gap.

### 3. Fixed-star target admission

Version 1.1 contains no fixed-star spectral profile. A physical fixed-star
event requires a separately admitted vessel with:

- unambiguous catalog identity;
- source-identified visual photometry;
- a named spectral distribution or explicit color-system transformation;
- pack or immutable external-data identity;
- independent validation; and
- proof that the new physical path never enters the legacy native arcus
  accelerator.

No ambiguous `color_index` may be guessed into a spectral response.

### 4. Independent end-to-end event validation

The exact version 1.1 pack and DE441 now pass one evaluated Jupiter event
probe. Closure still requires source-owned planetary goldens that are
independent of the legacy engine implementation and that cover multiple
bodies, phases, latitudes, and domain boundaries. Stellar validation follows
only after the fixed-star admission above.

## Explicitly Unchanged

- Legacy `HeliacalEventKind` meanings and dates.
- Legacy native planetary and fixed-star dispatch.
- Yallop lunar crescent search.
- Existing visibility-policy defaults and response shapes.
- Root exports, facade, serializers, REST, and OpenAPI.
- Phase 4 local-realism scope.
- Phase 6 native-strengthening scope.

## Next Authorized Work

Phase 3 remains active. The recommended order is:

1. extend or explicitly narrow the source-backed planetary event domains;
2. admit and independently validate a fixed-star spectral target contract;
3. add independent planetary and stellar physical-event goldens;
4. establish and adversarially test the crossing-completeness certificate;
5. add the Phase 3 closure receipt only after all four gates pass.
