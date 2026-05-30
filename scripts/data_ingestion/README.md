# Data Ingestion Scripts

This folder contains one-time or occasional refresh scripts used to build/populate data substrates for Moira (especially Tier 2 / Vedic star data).

## Scripts

- `build_tier2_substrate.py`: 
  General naked-eye / BSC5 + SIMBAD sweep. Queries Vizier for stars <= Mag 5, resolves via SIMBAD for proper motions, parallax, magnitudes, spectra. Appends "Tier 2" naked-eye luminaries to the registry (skipping those already in Tier 1).
  Used to extend the star data scaffolding for Tier 2 features.

- `build_sovereign_substrate.py`:
  Focused minting of IAU-sanctioned proper-name stars from the modern-iau-star-names-clean.csv. Prioritizes HIP, designations, Bayer IDs, and special aliases for the "sovereign" 88 IAU constellations' named stars.
  Emphasizes provenance and lore for culturally significant stars.

These were primarily run during the initial Tier 2 substrate work (around the time of the Vedic/Tier 2 efforts). Re-run only when you need to refresh or significantly extend the `moira/data/star_*` files.

Shared outputs:
- moira/data/star_registry.csv (core data)
- moira/data/star_lore.json (nature, spectrum, variable info, culture_map placeholders)
- moira/data/star_provenance.json (sources, matching status, resolution notes)

**Note:** These scripts use lazy numpy handling (via astropy masked arrays) and are not part of the core runtime. They depend on astroquery + astropy for live queries.

See the main MOIRA_NATIVE_MIGRATION_TRACKER.md and related docs for historical context on when these were executed.
