# Scripts Folder Cleanup Notice (2026-05-30)

We performed a major cleanup pass on the scripts/ directory.

## What Changed
- Many one-shot, historical, debug, and phase-specific scripts (diagnostics, old migration benchmarks, ad-hoc checks, etc.) have been moved into scripts/archive/.
- The two star substrate builders (build_tier2_substrate.py and build_sovereign_substrate.py) have been moved into scripts/data_ingestion/ (they are the legitimate tools for refreshing Tier 2 / Vedic star data).

## Why You Still See All the Old Files
Per our collaboration rules (see SYNC_POLICY.md), we only add new folders/files to your main working copy. We never automatically delete code files from your main folder. The originals remain exactly where they were so nothing is lost on your side.

You now have two new top-level folders next to the old files:
- archive/ — contains the moved one-shot/historical material (organized into subfolders)
- data_ingestion/ — contains the active data builder scripts

## Recommended Next Steps
1. Refresh/reload in VS Code or File Explorer (OneDrive can lag on new folders).
2. Look inside archive/ — everything there is safe to delete locally if you want to clean up.
3. data_ingestion/ has its own README.

Docs have been updated to point to the new archive locations.

If you need anything restored or moved differently, tell me.