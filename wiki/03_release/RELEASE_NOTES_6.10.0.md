# Release Notes - Moira 6.10.0

**Release date:** 12 October 2026.

Moira 6.10.0 brings the completed Vedic work through the selected VED-014
Kalachakra profile into an engine release. The Python engine, public facades
and REST API expose the same named policies, bounded calculations and source
provenance. Sixteen of the 24 registered Vedic packages have reached their
selected delivery checkpoints; this release does not claim every tradition.

## Vedic calculation and transport

- Daily Panchanga uses local dates, zones and sunrise-owned days, with solved
  limb endings, repeated/skipped sunrise evidence and unavailable solar states.
  Bounded lunar-month context is included; festival catalogues remain research.
- Gochar includes the admitted seven-body/natal-Moon snapshot, reader-bound
  epoch and civil-date composition, and bounded whole-sign windows. The window
  contract retains retrograde re-entry, Vedha, optional natal BAV, boundary
  uncertainty and a complete state partition under explicit resource budgets.
- D60 exposes edition-owned deities, Santhanam signs, a modern full-position
  profile and the explicit `classical_derived_linear` degree policy. Harmonic
  defaults remain; classical derivation and modern attribution stay distinct.
- Sayanadi admits the selected BPHS Navamsa-ordinal profile with strict inputs
  and dated birth composition. Legacy conditional-effect prose retains its
  separately documented validation limits.
- Chara supports bounded cycles and three named Rangacharya recipes. Argala
  has separate BPHS, PVR and Rath assessments, with repaired result invariants
  and explicit source conflicts.
- Yoga extensions add 21 selected source entries, with independent Navamsa
  readings and bounded BPHS wealth/royal rules. Unresolved aspect-target
  readings are explicitly excluded.
- Kalachakra admits `bphs_santhanam_longitude_row_cycle_v1`: nine major-period
  occurrences, optional full-parent antardashas, exact rational source years,
  explicit 360/365.25-day projections and bounded active-period lookup. Five
  REST operations provide discovery, supplied/date-derived sequences and
  current periods. Competing continuations and disputed gati remain visible.

## Muhurta

- Personalized sampled search now uses actual natal inputs, declared clocks,
  effective ayanamsa and complete applied-policy receipts.
- Seven named window families, Panchanga Shuddhi assessments, selected dosha
  detectors and source-scoped cancellation rules preserve raw restrictions,
  evidence and boundary uncertainty.
- Lagna/Navamsa components and optional strength context are available through
  the same engine and REST policies.
- Source-selected marriage, residential housing/Vastu, ordinary land travel,
  purchase/sale/first-opening and additional named marriage traditions share
  strict request contracts and bounded evaluation/search products.
- Marriage searches reuse request-local exact computations and remove
  redundant work without changing their accuracy or validation thresholds.

## Shared repairs and catalog integration

- Polynomial ayanamsas use the IAU 2006 general precession quantity appropriate
  to the scalar calculation. Historical sidereal results can change.
- Direct-input admission, reader binding, timescale provenance, result-tree
  integrity and REST error classification have been hardened across the
  delivered Vedic surfaces. Previously accepted malformed inputs may now fail.
- Packaged small-body manifests and metadata identify external catalog release
  `2026.10.10.1`. The wheel does not contain the external SPK catalog files.
  Historical scientific receipts remain bound to their original manifests;
  they are not relabelled to certify the newer catalog bytes.
- Publication candidates and exact-tag documentation artifacts retain distinct
  provenance, and generated API/wiki checks run before release.

## Validation and limits

The [release validation receipt](../03_validation/RELEASE_VALIDATION_6.10.0.md)
records the review, selected tests, resource receipts and publication checks.
Individual source and real-kernel acceptance receipts remain linked from the
[Vedic register](../06_roadmap/VEDIC_REMAINING_WORK_REGISTER.md).
These establish the documented computational scope, not predictive efficacy.

Special Lagnas, additional Gochar corpora/modifiers, deferred Pancha Pakshi
doctrines, exceptional lunar-month rules and festival catalogues remain future
work. Natal-discovery and light-box work in the development checkout is excluded.
Website application deployment is separate from this engine/PyPI release.

See [compatibility notes](COMPATIBILITY_NOTES_6.10.0.md) before upgrading.
