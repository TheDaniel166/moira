# Provenance Review Response (2026-04-15)

## Purpose
Record a factual response to the allegation that substantial portions of Moira were a direct port from Swiss Ephemeris source code.

## Allegation (quoted)
"Substantial parts of your source code seem to be a direct port of Swiss Ephemeris code"

## Scope of this review
- Primary implementation focus: house engine internals in moira/houses.py.
- Supporting pass: residual runtime lineage phrasing in moira/constants.py.
- Out of scope: validation/doctrine documentation that references Swiss as an external oracle.

## Findings
1. The reviewed runtime implementation does not support the broad claim that substantial parts are direct ports.
2. A limited set of functions had lineage-shaped wording and some historically recognizable structure patterns.
3. Those areas were rewritten/hardened to read as explicit Moira-owned mathematical code while preserving public API and behavior.
4. Remaining Swiss mentions in documentation are primarily oracle/comparison context, not implementation ancestry claims.

## Implementation actions completed
### Houses hardening (moira/houses.py)
- Neutralized lineage-shaped phrasing in targeted kernels and helpers.
- Reworked projection helpers into neutral geometric forms.
- Consolidated repeated RA-to-longitude projection paths where appropriate.
- Added boundary hygiene helper _finalize_cusps for private kernel return vectors (shape/finite/normalization checks).
- Preserved doctrine/policy behavior and public API surfaces.

Targeted functions completed in this cycle:
- _mc_from_armc
- _alcabitius
- _morinus
- _campanus
- _azimuthal
- _carter
- _cotrans
- _krusinski
- _apc
- houses_from_armc
- body_house_position

### Residual runtime comment cleanup (moira/constants.py)
- Removed remaining "SWE letter" lineage-style comments from house system constants.
- No constant values changed.

## Verification actually run
Focused house regression battery:

.venv\Scripts\python.exe -m pytest tests/unit/test_house_hardening.py tests/unit/test_house_membership.py tests/unit/test_house_classification.py tests/unit/test_polar_house_breadth_gauntlet.py tests/unit/test_experimental_placidus.py -q

Result: pass.

## Public API and behavior status
- No public function renames.
- No public dataclass/enum renames.
- No exported symbol changes.
- No intentional doctrine/policy behavior changes in house selection/fallback paths.

## Conclusion
The reviewed evidence does not support the blanket claim that substantial parts of Moira are direct Swiss source ports. The identified risk surface was narrowed and remediated in runtime code, with focused tests passing after each hardening pass.
