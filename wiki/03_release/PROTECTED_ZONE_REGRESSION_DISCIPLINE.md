# Protected-Zone Regression Discipline

Status: active release-hardening policy

Purpose
-------
This page records the minimum regression discipline required whenever a change
touches a protected zone on the production path.

Protected zones
---------------
For release discipline, the following remain protected:

- astronomical core computation
- time systems and `delta_t` semantics
- precession, nutation, aberration, refraction, and coordinate transforms
- ephemeris or kernel binding logic
- house-policy propagation and fallback truth
- validation baselines, accuracy thresholds, and oracle comparison logic
- canonical public result vessels and root exports

Required practice
-----------------
When a change touches a protected zone:

1. Name the protected zone in the change summary before editing.
2. Run at least one targeted suite that directly exercises the touched zone.
3. Run any public-surface guard needed to prove that the change did not drift
   exported semantics.
4. If the change affects release-facing docs, run the doc-consistency checker.
5. Do not claim parity, precision retention, or unchanged semantics unless the
   relevant targeted checks actually ran.

Minimum targeted suites
-----------------------
Use the smallest relevant suite first.

| Protected concern | Minimum targeted proof |
| --- | --- |
| Root public exports and layered surfaces | `tests/unit/test_public_api_drift.py` |
| Public doctrine and policy vessels | `tests/unit/test_public_doctrine_surfaces.py` |
| Vimshottari structural and invariant truth | `tests/unit/test_dasha.py` |
| Firdaria and Zodiacal Releasing structural truth | `tests/unit/test_timelords.py` |
| Planetary cycles and return-series semantics | `tests/unit/test_cycles.py` |
| Adversarial astronomical routing and polar doctrine | `wiki/03_validation/KILLER_VALIDATION_INDEX.md` run list |

Operational gate
----------------
The repository CI release-hardening lane enforces the following floor on every
push to `main` and every pull request:

- release-facing doc consistency
- public API drift guard
- public doctrine surface audit
- `dasha.py` hardening suite
- `timelords.py` hardening suite
- `cycles.py` hardening suite

Anything broader remains a release-manager decision, not an excuse to skip the
minimum targeted proof above.
