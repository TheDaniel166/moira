# Killer Validation Index

Purpose
-------
This page is the compact index for Moira's adversarial validation layer.

It does not replace the detailed result tables.
It tells you which proof covers which failure mode, where the measured outputs live,
and which suites to run when someone sends a new "killer test."

Validation layers
-----------------

| Layer | What it proves | Primary artifacts |
| --- | --- | --- |
| Segment continuity | No public jump at real DE441 split boundaries | `tests/unit/test_de441_segment_boundaries.py`, `wiki/03_release/KILLER_TEST_RESULTS.md` |
| Delta-T robustness | Smooth, symmetric response to `ΔT` perturbations across coverage | `tests/unit/test_ephemeris_stress_proofs.py`, `wiki/03_release/DELTA_T_500_YEAR_CHECKPOINTS.md` |
| Coverage-edge truth | Finite results inside coverage and explicit failure outside it | `tests/unit/test_ephemeris_stress_proofs.py` |
| Conjunction solver rigor | Near-zero residual roots and time-reversal sanity at conjunctions | `tests/unit/test_ephemeris_stress_proofs.py` |
| Fixed-case routing coherence | Direct, chained, and routed topocentric paths agree at one TT-pinned epoch | `tests/unit/test_topocentric_multi_path_consistency.py`, `tests/integration/test_topocentric_multi_path_horizons_anchor.py` |
| Breadth gauntlet | Cross-epoch, cross-observer, cross-body route, round-trip, smoothness, and external-anchor stability | `tests/unit/test_ephemeris_breadth_gauntlet.py`, `tests/integration/test_ephemeris_breadth_horizons_gauntlet.py` |
| Polar high-latitude oracle | Supported polar-capable house systems match the cached Swiss oracle above critical latitude | `tests/integration/test_houses_polar_external_reference.py`, `wiki/03_validation/POLAR_HOUSE_EXTERNAL_REFERENCE.md` |
| Polar house gauntlet | Dynamic critical-latitude doctrine, strict-policy honesty, and fallback placement parity | `tests/unit/test_polar_house_breadth_gauntlet.py` |
| Polar chart public-path gauntlet | Chart vessel, house fallback, body placement, angularity, and lots remain coherent on the public API path | `tests/unit/test_polar_chart_public_gauntlet.py` |
| Public doctrine surface audit | Public doctrine and policy vessels remain reachable, frozen, default-constructible, and correctly classified | `tests/unit/test_public_doctrine_surfaces.py`, `wiki/03_release/KILLER_TEST_RESULTS.md` |

How to read the stack
---------------------
- The stress suite attacks local numerical pathologies: boundaries, `ΔT`, root-finding, and coverage edges.
- The breadth suite attacks routing drift: different observers, epochs, bodies, coordinate conversions, and compact external anchors.
- The polar high-latitude oracle attacks supported-system truth against Swiss at the actual polar cap.
- The polar-house suite attacks fallback doctrine: whether high-latitude house policy stays explicit and downstream-consistent.
- The polar chart suite attacks public-path coherence: whether fallback truth survives all the way up to chart assembly, placement, angularity, and lots.
- The doctrine audit attacks API drift at the policy layer: whether exposed doctrine vessels still exist, stay frozen, and preserve stable default construction semantics.

Detailed reports
----------------
- `wiki/03_release/KILLER_TEST_RESULTS.md`
- `wiki/03_release/DELTA_T_500_YEAR_CHECKPOINTS.md`
- `wiki/03_validation/POLAR_HOUSE_EXTERNAL_REFERENCE.md`

Recommended run order
---------------------
1. `python -m pytest tests/unit/test_de441_segment_boundaries.py -q`
2. `python -m pytest tests/unit/test_ephemeris_stress_proofs.py -q`
3. `python -m pytest tests/unit/test_topocentric_multi_path_consistency.py -q`
4. `python -m pytest tests/unit/test_ephemeris_breadth_gauntlet.py -q`
5. `python -m pytest tests/unit/test_polar_house_breadth_gauntlet.py -q`
6. `python -m pytest tests/unit/test_polar_chart_public_gauntlet.py -q`
7. `python -m pytest tests/unit/test_public_doctrine_surfaces.py -q`
8. `python -m pytest tests/integration/test_topocentric_multi_path_horizons_anchor.py -q`
9. `python -m pytest tests/integration/test_ephemeris_breadth_horizons_gauntlet.py -q`
10. `python -m pytest tests/integration/test_houses_polar_external_reference.py -q`

Decision rule
-------------
- If a new challenge is about astronomical continuity, time scale behavior, or root precision, start in the stress suite.
- If it is about observer routing, coordinate transforms, or external anchors, start in the breadth suite.
- If it is about supported house systems at the polar cap, start in the polar external oracle.
- If it is about fallback doctrine for unsupported semi-arc systems, start in the polar-house suite.
- If it is about whether that fallback doctrine survives chart assembly or lot computation, start in the polar chart suite.
- If it is about whether a policy or doctrine surface is still publicly exposed and structurally stable, start in the doctrine audit.
- If it survives all of those layers, it is probably testing a genuinely new semantic surface rather than an already-covered edge.
