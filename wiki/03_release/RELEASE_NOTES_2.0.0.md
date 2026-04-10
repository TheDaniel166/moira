# Release Notes — Moira 2.0.0

Date: 2026-04-10

---

## Summary

Moira 2.0.0 is a release-integrity milestone.

No new astrological features are introduced.
What this release does is harden the behavioral contract of the engine:
time semantics are now strict, house policy is now explicit, public result
vessels are now formally frozen, and several subsystems that previously
accepted ambiguous inputs now raise rather than silently proceeding on
invalid assumptions.

These changes collectively produce a more honest and verifiable engine.
Callers that depended on undefined behavior will need to adapt.
The compatibility guide below states exactly what must change.

---

## Breaking Changes

Four changes require caller adaptation.
Full migration guidance is in `COMPATIBILITY_NOTES_2.0.0.md`.

### 1. Naïve `datetime` objects now raise

`jd_from_datetime()` previously accepted timezone-unaware `datetime` objects
and silently treated them as UTC.

This is now an error.

```python
# raises ValueError in 2.0.0
jd_from_datetime(datetime(2000, 1, 1, 12, 0, 0))

# correct
from datetime import timezone
jd_from_datetime(datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
```

Callers that pass naïve datetimes anywhere in the engine must add explicit
`tzinfo`. This is the most pervasive caller-visible change in this release.

### 2. `classify_house_system()` now raises on unknown codes

Previously this function returned undefined or silent fallback behavior for
unrecognized house system codes. It now raises `ValueError`.

```python
# raises ValueError in 2.0.0
classify_house_system("XX")
```

Callers must pass only valid `HouseSystem` constants.

### 3. Strict house policy now raises on unknown codes

When using `HousePolicy.strict()` or passing `unknown_system=UnknownSystemPolicy.RAISE`,
unknown house system codes that previously fell back silently to Placidus now
raise `ValueError`.

The **default** `HousePolicy` retains silent fallback. This change only affects
callers who explicitly request strict behavior or who construct `HousePolicy`
with `UnknownSystemPolicy.RAISE`.

### 4. `decan_at()` no longer accepts a `reader` parameter

The optional `reader` argument has been removed from `decan_at()`. The function
is now self-contained and computes from RAMC, true obliquity, and latitude
directly.

```python
# raises TypeError in 2.0.0
decan_at(jd, lat, lon, reader=my_reader)

# correct
decan_at(jd, lat, lon)
```

---

## Hardening (no caller breakage)

The following changes strengthen guarantees without requiring caller adaptation.

### House policy objects made explicit

House calculations now carry full truth-preservation metadata:

- `HouseCusps.system` — the system that was requested
- `HouseCusps.effective_system` — the system that actually ran
- `HouseCusps.fallback` — `True` if a fallback occurred
- `HouseCusps.fallback_reason` — why the fallback occurred

Callers who relied on silent fallback will still get results. They now also get
explicit metadata explaining what happened.

### 50 public policy dataclasses are now formally frozen

All public policy dataclasses are `frozen=True, slots=True` and are enforced as
such at test-gate time. These are hashable, immutable, and safe to use as dict
keys or in sets.

### Hermetic decan night geometry now validated at construction

`DecanHoursNight` now validates its inputs in `__post_init__`. Invalid night
boundaries (non-finite JDs, inverted sunset/sunrise ordering, wrong number of
hours) raise `ValueError` at construction time rather than producing silently
corrupt results downstream.

### Heliacal stellar rising corrected

The redundant elongation magnitude guard (`abs(se) < 12.0°`) has been removed
from the rising solver. This eliminated a systematic +1-day offset for stars
with small arcus visionis values (e.g., Regulus at approximately 11°). The
altitude check at the visibility-arc twilight threshold remains the sole rising
criterion, which is the correct formulation.

### Operational hardening artifacts in place

- CI gate: `.github/workflows/release-hardening.yml`
- Doc-consistency checker: `scripts/check_doc_consistency.py`
- Protected-zone regression discipline: `wiki/03_release/PROTECTED_ZONE_REGRESSION_DISCIPLINE.md`

---

## Validation

The following test suites were verified green in the project `.venv` on 2026-04-10:

- `tests/unit/test_public_api_drift.py` — public API surface stability
- `tests/unit/test_public_doctrine_surfaces.py` — frozen policy dataclass enforcement
- `tests/unit/test_dasha.py` — dasha system correctness
- `tests/unit/test_timelords.py` — timelord engine correctness
- `tests/unit/test_cycles.py` — cycle and return solver correctness
- `tests/unit/test_electional.py` — electional engine correctness
- `tests/unit/test_hermetic_decans.py` — hermetic decan hardening
- `tests/unit/test_house_hardening.py` — house engine consistency
- `tests/unit/test_de441_segment_boundaries.py` — DE441 continuity proofs
- `tests/unit/test_ephemeris_stress_proofs.py` — Delta-T robustness

Full killer-test results are in `wiki/03_release/KILLER_TEST_RESULTS.md`.
Doc-consistency check passes clean.

---

## Compatibility

See `COMPATIBILITY_NOTES_2.0.0.md` for a concise migration guide.

---

## Prior version

`1.2.1` — production-capable engine state prior to release-integrity hardening.
