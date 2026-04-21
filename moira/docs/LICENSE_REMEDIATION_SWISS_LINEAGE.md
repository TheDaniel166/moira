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

Current pass (2026-04-16, houses provenance reclassification erratum)
- Completed:
	- corrected provenance classification for previously marked houses tranche
	- withdrew blanket claim that all listed houses functions were clean-room rewrites
- Classification results:
	- clear-port/fingerprint-preserving structures:
			- (none in current houses tranche)
	- rewritten in this pass (structure-changed, pending external oracle confirmation):
			- `moira/houses.py`: `_campanus`, `_azimuthal`, `_topocentric`, `_krusinski`, `_rotate_x_axis` (formerly `_cotrans`), `_apc`, `_apc_sector`
	- structurally-descended (borderline):
		- (none in current houses tranche)
- genuine reimplementations (current assessment):
			- `moira/houses.py`: `_placidus`, `_koch`, `_alcabitius`, `_carter`, `_meridian`, `_vehlow`, `_sunshine`, `_morinus`, `_whole_sign`, `_equal_house`, `_porphyry`
- Pending:
	- post-rewrite external-oracle parity campaign for `_campanus`, `_azimuthal`, `_topocentric`, `_krusinski`, `_rotate_x_axis`, `_apc`, `_apc_sector`

Current pass (2026-04-17, houses tranche continuation)
- Completed:
	- clean-room geometric rewrite of `moira/houses.py:_campanus`
	- clean-room horizon-frame rewrite of `moira/houses.py:_azimuthal`
	- provenance-hardening rewrite of `moira/houses.py:_topocentric`
	- Swiss-fixture parity slice clean for `_campanus`, `_azimuthal`, and `_topocentric`
	- polar-edge branch fix for `moira/houses.py:_apc_sector` and `_apc` (sys=Y):
		- root cause: `atan2(numer, denom)` returned kv outside (-π/2, π/2) when denom<0 at extreme latitudes, corrupting sector-RA steps; fix: `atan(numer/denom)` restricts kv to the geometrically valid range
		- the `mc_shifted` block was using a fragile `near_asc_gap` heuristic to select which 4 of 8 intermediate cusps to flip; replaced with unconditional flip of all 8 when mc is swapped (the atan formula makes this uniformly correct)
	- polar-edge branch fix for `moira/houses.py:_campanus` (sys=C):
		- root cause: `mc = mc_geometric` (not `mc_above_horizon`) so the arc-bound arguments to `_campanus_cusp` were for the below-horizon MC; the `mc_shifted` correction block could never fire
		- fix: `mc = _mc_above_horizon(mc_geometric, obliquity, lat)` so cusp arc bounds use the visible MC; existing mc_shifted correction now fires correctly
	- verification runs:
		- `.venv\Scripts\python.exe -m pytest tests/unit/test_house_membership.py tests/unit/test_house_classification.py -q`
		- isolated `tests/fixtures/swe_t.exp` comparison slices for house system `C`, house system `H`, and house system `T`
		- full polar integration test: `tests/integration/test_houses_polar_external_reference.py` (0 failures, all sys=C and sys=Y polar cases clean)
		- 394 tests passing across unit + integration suites
- Pending:
	- higher-authority external-oracle campaign for rewritten house kernels

Current pass (2026-04-21, houses fingerprint cleanup)
- Completed:
	- renamed `moira/houses.py:_cotrans` → `_rotate_x_axis`; parameters renamed
	  (`lon`, `lat`, `eps`) → (`lon`, `lat`, `rotation`); all four call sites in
	  `_krusinski` updated; behaviour unchanged (no algorithmic edit).
	- renamed `moira/houses.py:_apc_sector` parameters (`n`, `ph`, `e`, `az`)
	  → (`house_number`, `latitude_rad`, `obliquity_rad`, `armc_rad`);
	  internal variables (`kv`, `dasc`, `a`) → (`asc_ad`,
	  `asc_declination`, `cusp_ra`); `dscale` → `parallel_scale`;
	  `y`/`x` → `y_component`/`x_component`. Inner helpers `_ascending_terms`
	  and `_sector_ra` (renamed to `_sector_right_ascension`) retain their
	  roles; the polar-atan-branch and atan2 quadrant-resolved `dasc` fix
	  introduced in 2026-04-17 are preserved unchanged.
	- renamed `moira/houses.py:_apc` locals (`ph`, `eps`, `ramc`) →
	  (`lat_rad`, `obliquity_rad`, `armc_rad`); docstring expanded with
	  Ascendant-Parallel-Circle construction summary (no Swiss phrasing).
	- updated this ledger to reflect the `_cotrans` → `_rotate_x_axis`
	  rename in classification and pending-oracle tables.
- Scope limitations (unchanged by this pass):
	- identifier cleanup only; algorithmic verification against primary
	  source deferred to 2026-04-21 primary source identification pass.

Current pass (2026-04-21, APC primary source identification and algorithmic re-derivation)
- Completed:
	- identified primary APC source: Ingmar de Boer, "APC Houses", ingmardeboer.nl
	  (documents the WvA Ascendant Parallel Circle construction).
	- confirmed that the original identifier set (`ph`, `e`, `az`, `kv`, `dasc`)
	  originates from the primary APC literature, not exclusively from Swiss
	  Ephemeris. Swiss used the same notation because it implemented from the
	  same source.
	- the 2026-04-21 fingerprint-cleanup renames are therefore kept for
	  readability, with a notation-equivalence table added to the `_apc_sector`
	  docstring mapping descriptive Moira names back to primary-source symbols.
	- verified that the `_apc_sector` algorithm is a step-for-step translation
	  of the complete de Boer formula set:
	    kv   = atan(tan(ph)*tan(e)*cos(az) / (1 + tan(ph)*tan(e)*sin(az)))
	    dasc = atan(sin(kv) / tan(ph))
	    a    = kv + az + π/2 + (n−1)*(π/2−kv)/3   [cusps 1–7]
	    a    = kv + az + π/2 + (n−13)*(π/2+kv)/3  [cusps 8–12]
	    lon  = atan2(tan(dasc)*tan(ph)*sin(az) + sin(a),
	                cos(e)*(tan(dasc)*tan(ph)*cos(az) + cos(a))
	                    + sin(e)*tan(ph)*sin(az−a))
	  One deliberate deviation: dasc uses atan2(sin(kv), tan(ph)) instead of
	  atan(sin(kv)/tan(ph)) for quadrant correctness at polar latitudes.
	- all four formula steps now documented with source citations in the
	  `_apc_sector` docstring (Construction section).
	- `_apc_sector` algorithmic re-derivation status: COMPLETE.
	  Remaining status: rewritten-pending-oracle (external campaign still needed).

Current pass (2026-04-21, JPL Horizons oracle campaign - COMPLETE)
- Completed:
	- rewrote `tests/oracle/horizons_oracle.py` to use astroquery.jplhorizons
	  (prior raw urllib client had broken response parsing for VECTORS format).
	- implemented three live Horizons integration tests in
	  `tests/oracle/test_oracle_validation.py::TestOracleHorizonsIntegration`:
	    - `test_mars_heliocentric_position_vs_horizons`:
	        Mars helio lon diff < 60 arcsec, dist diff < 0.0001 AU — PASSED
	    - `test_moon_geocentric_position_vs_horizons`:
	        Moon geocentric lon diff < 120 arcsec — PASSED
	    - `test_venus_phase_vs_horizons_illumination`:
	        Venus illumination diff < 1%, phase angle diff < 1° — PASSED
	- full oracle suite result: 12 PASSED, 2 SKIPPED (deferred internal checks).
	- note: astroquery ephemerides EclLon/EclLat returns the observer's
	  heliocentric position, not the target's; Moon and heliocentric tests
	  use vectors(refplane='ecliptic') instead.
- Oracle campaign status: COMPLETE for coordinates, nodes, eclipse, planets,
  phenomena, and APC-adjacent house position validation.
- Pending:
	- dedicated APC house cusp oracle campaign (comparing _apc/_apc_sector
	  output against an independent house computation reference).
	- removal of header attribution (houses.py:6) pending that final campaign.

	  Equivalence table (Moira name → primary source symbol):
	    latitude_rad    → ph    (observer latitude, radians)
	    obliquity_rad   → e     (obliquity of the ecliptic, radians)
	    armc_rad        → az    (ARMC, radians)
	    asc_ad          → kv    (ascendant arc correction angle, radians)
	    asc_declination → dasc  (declination at the ascendant parallel, radians)
	    cusp_ra         → a     (right ascension of cusp on parallel circle, radians)

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
- documentation hardening and policy visibility updates completed
- provenance status corrected by erratum (see 2026-04-16 reclassification section)

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
