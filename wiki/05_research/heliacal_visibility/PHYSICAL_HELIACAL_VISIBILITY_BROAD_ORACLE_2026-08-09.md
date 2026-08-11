# Physical Heliacal Visibility Broad Oracle - 2026-08-09

Status: accepted local Phase 7 engine release gate; no tag, package
publication, downstream installation, deployment, or website change was
performed.

## Outcome

The original exact end-to-end event oracle contained one Jupiter morning-first
rising and one Sirius morning-first rising. That evidence remains valid, but it
was not broad enough to carry the four-target, four-phase public event surface
by itself.

The expanded gate predeclares the complete product of:

- targets: Mars, Jupiter, Saturn, and Sirius; and
- phases: morning first rising, morning first setting, evening last rising,
  and evening last setting.

The resulting 16 cells contain:

- 12 independently reconstructed event times;
- 4 explicit typed negative/domain regression cells;
- 40 checksum-bound one-minute NASA/JPL Horizons source files;
- checksum-bound Hipparcos Sirius astrometry and a pinned offline
  Astropy/ERFA/IERS transform; and
- the exact external visibility pack `1.2.0`, manifest
  `cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c`.

All 12 event-time comparisons pass the fixed 60-second limit. The largest
absolute engine/oracle difference is `5.8789461851119995` seconds. The live
public-engine replay passes all 16 cells with the declared default search
policy and content-admitted DE441.

## Independence boundary

The source acquisition step uses an exact engine result only to center a
bounded external query. It does not use that engine timestamp as oracle truth.
The offline oracle then derives the event from:

1. JPL airless target and solar geometry;
2. JPL apparent planetary photometry, or Hipparcos/Astropy Sirius geometry and
   source-owned Sirius photometry;
3. a separate implementation of the immutable visibility-pack interpolation,
   CIE MES2, Crumey threshold, extinction, and target-color equations;
4. independently reconstructed target-boundary and solar-side ownership; and
5. linear root interpolation on the fixed one-minute external grid.

The builder and Phase 7 validator import neither Moira, the production event
solver, nor a network client. They contain no direct NumPy import. The isolated
Sirius authority-validation toolchain uses the declared development-only
Astropy/ERFA stack and may load NumPy transitively; neither NumPy nor Astropy is
part of the published engine, the live engine replay, or the base runtime. The
acquisition script is the only networked step. The stored validator replay is
offline and checksum locked.

## Timed-event results

| Case | Engine/oracle difference (s) | Guard-day independent basis |
|---|---:|---|
| Mars, morning first setting, Babylon | 0.352322 | target setting occurs after sunrise on the adjacent day |
| Mars, evening last rising, Babylon | 1.195729 | target rising occurs before sunset on the adjacent day |
| Jupiter, evening last setting, Levant | 0.679578 | requested margin crossing is absent on the adjacent day |
| Jupiter, morning first rising, Levant | 0.759038 | requested margin crossing is absent on the adjacent day |
| Jupiter, morning first setting, Levant | 0.144638 | target setting occurs after sunrise on the adjacent day |
| Jupiter, evening last rising, Levant | 0.194044 | target rising occurs before sunset on the adjacent day |
| Saturn, morning first setting, Sydney | 0.232548 | target setting occurs after sunrise on the adjacent day |
| Saturn, evening last rising, Sydney | 0.425063 | target rising occurs before sunset on the adjacent day |
| Sirius, evening last setting, New Orleans | 5.878946 | requested margin crossing is absent on the adjacent day |
| Sirius, morning first rising, New Orleans | 3.780989 | requested margin crossing is absent on the adjacent day |
| Sirius, morning first setting, New Orleans | 1.019588 | target setting occurs after sunrise on the adjacent day |
| Sirius, evening last rising, New Orleans | 0.414683 | target rising occurs before sunset on the adjacent day |

The adjacent-day trace matters. A raw visibility-margin zero can exist while
the requested target boundary lies on the wrong side of sunrise or sunset.
Such a day does not own the requested phase. The broadened oracle reconstructs
that geometry rather than accepting only the selected event timestamp.

## Typed negative/domain cells

These four matrix cells are intentionally not described as independent event
times:

| Case | Public result | Reason |
|---|---|---|
| Mars, evening last setting, Greenwich | `not_found` | `no_phase_transition_in_search_window` |
| Mars, morning first rising, Greenwich | `not_found` | `no_phase_transition_in_search_window` |
| Saturn, evening last setting, Greenwich | `not_evaluable` | `target_altitude_out_of_domain` |
| Saturn, morning first rising, Greenwich | `not_found` | `no_phase_transition_in_search_window` |

They are full-window public-engine regressions that verify fail-closed status,
reason, evidence state, and absence of fabricated event fields. They must not
be counted as four additional event-time oracles.

## Source-controlled evidence

- Frozen acquisition specification:
  `scripts/visibility_reference_lab/physical_visibility_phase7_source_acquisition_spec_v1.json`
- Matrix specification:
  `scripts/visibility_reference_lab/physical_visibility_phase7_broad_oracle_matrix_v1.json`
- Networked acquisition tool:
  `scripts/acquire_visibility_phase7_oracle_sources.py`
- Engine-only window discovery tool:
  `scripts/discover_visibility_phase7_oracle_windows.py`
- Offline independent builder:
  `scripts/build_visibility_phase7_broad_oracle.py`
- Offline independent validator:
  `scripts/validate_visibility_phase7_broad_oracle.py`
- Immutable golden:
  `tests/golden/physical_visibility_phase7_broad_oracle.json`
- External-source recovery receipt:
  `tests/artifacts/release/physical_visibility_phase7_source_recovery_2026-08-11.json`
- Governance:
  `tests/unit/test_visibility_phase7_broad_oracle_governance.py`
- Live public-engine replay:
  `tests/integration/test_physical_visibility_phase7_broad_oracle.py`

The golden SHA-256 is
`29d96b8eb1187c013357039df8c224e6a41381d83bb81fd961e24057a563ede9`.
It records the exact source-file names, byte counts, SHA-256 checksums, query
identities, pack identity, toolchain receipt, independent brackets, event
roots, target/solar boundary roots, guard-day basis, captured engine results,
and residuals.

## Acquisition provenance recovery - 2026-08-11

The external sources and the admitted matrix were frozen in two deliberate
steps. The network acquisition used the 5,311-byte pre-admission specification
now preserved at
`scripts/visibility_reference_lab/physical_visibility_phase7_source_acquisition_spec_v1.json`.
Its raw LF SHA-256 is
`ba061013c6e6258475baab4442b072c82c887aabc840cc19f5b0126542eb9323`,
which is the exact digest recorded by the archived NASA/JPL source manifest.

The later admitted matrix adds the release gate and physical-policy receipt.
Its raw LF SHA-256 is
`9237a3829ec97121845a51827fd7013b71f8802fee02005e1d26c4222aec0f9a`.
The acquisition-driving fields - schema, status, selection policy, five sites,
and all 16 cases - are identical in both files. Governance tests bind the two
files and reject drift. This separation removes the former self-reference in
which the acquisition tool defaulted to the later file containing the earlier
file's digest.

The 47 external source files were also preserved in the verified 48-entry
archive `physical-visibility-phase7-source-bundle-2026-08-11.zip`, SHA-256
`ebad4060250702c2dff378c960a67de657dab9a5366856825907e93f88b4e103`.
The archive remains external; its machine-independent identity and complete
verification checks are recorded in the source-controlled recovery receipt.

## Limits of the claim

This gate validates the admitted clear-sky, naked-eye, unresolved point-source
model and its public event semantics. It does not control or predict clouds,
smoke, local light pollution, campfires, obstructions, observer physiology, or
other real-world conditions outside the explicit policy. It also does not
admit Mercury or Venus event search, additional fixed stars, telescopic
visibility, extended objects, or the quarantined Jones/Paranal experiment.
