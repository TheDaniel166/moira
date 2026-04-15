# Swiss-Lineage License Remediation Ledger

Purpose
- Track functions that require clean-room rewrite and provenance hardening.
- Separate wording cleanup from algorithmic remediation.
- Keep legal/computational truth explicit.

Status key
- wording-cleaned: Swiss-lineage wording removed from docstrings/comments.
- rewrite-required: implementation still needs clean-room derivation.
- done: independently re-derived and validated against non-copied authorities.

Current pass (2026-04-15)
- Completed:
	- wording-cleaned across core modules.
	- houses hardening pass completed for targeted house kernels and public helpers.
- Not completed:
	- independent-oracle parity campaign for non-house rewrite-required functions.

High-priority rewrite-required set
- moira/coordinates.py: horizontal_to_equatorial
- moira/coordinates.py: cotrans_sp
- moira/coordinates.py: atmospheric_refraction
- moira/coordinates.py: atmospheric_refraction_extended
- moira/coordinates.py: equation_of_time
- moira/eclipse.py: next_solar_eclipse_at_location (class method)
- moira/eclipse.py: next_solar_eclipse_at_location (module wrapper)
- moira/nodes.py: next_moon_node_crossing
- moira/nodes.py: nodes_and_apsides_at
- moira/phenomena.py: planet_phenomena_at
- moira/planets.py: planet_relative_to
- moira/planets.py: next_heliocentric_transit

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
