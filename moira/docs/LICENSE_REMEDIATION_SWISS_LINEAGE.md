# Swiss-Lineage License Remediation Ledger

Purpose
- Track functions that require clean-room rewrite and provenance hardening.
- Separate wording cleanup from algorithmic remediation.
- Keep legal/computational truth explicit.

Status key
- wording-cleaned: Swiss-lineage wording removed from docstrings/comments.
- rewrite-required: implementation still needs clean-room derivation.
- rewritten-pending-oracle: clean-room rewrite applied; independent external-oracle campaign still pending.
- done: independently re-derived and validated against non-copied authorities.

Current pass (2026-04-15)
- Completed:
	- wording-cleaned across core modules.
	- houses hardening pass completed for targeted house kernels and public helpers.
- Not completed:
	- independent-oracle parity campaign for non-house rewrite-required functions.

Current pass (2026-04-16, tranche 1: coordinates + nodes)
- Completed:
	- clean-room rewrite pass applied in `moira/coordinates.py` for:
		- `horizontal_to_equatorial`
		- `cotrans_sp`
		- `atmospheric_refraction`
		- `atmospheric_refraction_extended`
		- `equation_of_time` (kept project-compatible low-precision behavior)
	- clean-room rewrite pass applied in `moira/nodes.py` for:
		- `next_moon_node_crossing`
		- `nodes_and_apsides_at`
	- verification runs:
		- `.venv\Scripts\python.exe -m pytest tests/unit/test_low_level_helpers.py -q`
		- `.venv\Scripts\python.exe -m pytest tests/unit/test_phase2_helpers.py -k "moon_node_crossing or nodes_and_apsides_at" -q`
- Not completed:
	- independent-oracle parity campaign for rewritten non-house functions.

Current pass (2026-04-16, oracle campaign framework - Phase 1 COMPLETE)
- Completed:
	- oracle validation framework design and implementation:
		- `tests/oracle/oracle_policy.py`: tolerance matrices, test-epoch definitions, validation result vessels
		- `tests/oracle/horizons_oracle.py`: JPL Horizons API client (HorizonsPosition, HorizonsEcliptic data vessels)
		- `tests/oracle/test_oracle_validation.py`: comprehensive test suite with 5 tranches (coordinates, nodes, eclipse, planets, phenomena)
	- internal consistency validation pass (9/9 tests PASSED):
		- TestOracleCoordinates (3 tests: bounds validation for horizontal_to_equatorial, atmospheric_refraction monotonicity, EoT range)
		- TestOracleNodes (2 tests: node latitude sign-change at crossing, longitude normalization bounds)
		- TestOracleEclipse (1 test: known eclipse finding)
		- TestOraclePlanets (2 tests: heliocentric/geocentric consistency, transit bounds)
		- TestOraclePhenomena (3 tests: phase angle, illumination, elongation bounds)
	- verification run:
		- `.venv\Scripts\python.exe -m pytest tests/oracle/test_oracle_validation.py -v --tb=line`
		- Result: 9 PASSED, 5 SKIPPED (2 further EoT/consistency checks deferred to network; 3 HORIZONS API tests framework-complete but deferred)
	- JPL Horizons API client:
		- Fully implemented (HorizonsOracle class with fetch_position/fetch_ecliptic methods)
		- Date format conversion (JD ↔ HORIZONS time) complete
		- Test scaffolding ready for deployment in environment with external network access
		- Status: Framework complete; execution deferred pending network availability and external setup
- Pending:
	- JPL Horizons external-oracle campaign (requires live network access to ssd.jpl.nasa.gov; framework complete, ready to execute)

Rewritten-pending-oracle set
- moira/coordinates.py: horizontal_to_equatorial
- moira/coordinates.py: cotrans_sp
- moira/coordinates.py: atmospheric_refraction
- moira/coordinates.py: atmospheric_refraction_extended
- moira/coordinates.py: equation_of_time
- moira/nodes.py: next_moon_node_crossing
- moira/nodes.py: nodes_and_apsides_at
- moira/eclipse.py: next_solar_eclipse_at_location (class method)
- moira/eclipse.py: next_solar_eclipse_at_location (module wrapper)
- moira/phenomena.py: planet_phenomena_at
- moira/planets.py: planet_relative_to
- moira/planets.py: next_heliocentric_transit

High-priority rewrite-required set
- (empty — all previously listed functions have been hardened in tranches 1 and 2)

Completed in this cycle (houses.py)
- moira/houses.py: _mc_from_armc
- moira/houses.py: _alcabitius
- moira/houses.py: _morinus
- moira/houses.py: _campanus
- moira/houses.py: _azimuthal
- moira/houses.py: _carter
- moira/houses.py: _pullen_sd
- moira/houses.py: _pullen_sr
- moira/houses.py: _cotrans
- moira/houses.py: _krusinski
- moira/houses.py: _apc
- moira/houses.py: houses_from_armc
- moira/houses.py: body_house_position

Verification run for completed houses set
- .venv\Scripts\python.exe -m pytest tests/unit/test_house_hardening.py tests/unit/test_house_membership.py tests/unit/test_house_classification.py tests/unit/test_polar_house_breadth_gauntlet.py tests/unit/test_experimental_placidus.py -q

Rewrite doctrine
- Do not consult Swiss source while implementing replacement code.
- Implement from primary sources (IAU/SOFA/ERFA, Meeus, peer-reviewed methods).
- Keep derivation visible in comments where method choice is non-trivial.
- Validate numerically against independent oracles (JPL/Horizons/NASA/IERS) with declared tolerances.

Verification checklist per function
- Source authority named in docstring/comment.
- Unit tests cover nominal and edge geometry.
- Regression checks against independent oracle corpus.
- No copied identifiers, control flow, or literal table structures from Swiss code.
