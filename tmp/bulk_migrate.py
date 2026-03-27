from pathlib import Path

p = Path('moira/constellations')
files = list(p.glob('stars_*.py'))
print(f"Migrating {len(files)} constellation files...")

for f in files:
    content = f.read_text(encoding='utf-8')
    
    # 1. Update imports
    content = content.replace(
        'from ..fixed_stars import fixed_star_at, StarPosition, list_stars',
        'from ..stars import fixed_star_at, GaiaStarPosition, list_stars'
    )
    
    # 2. Update type hints
    content = content.replace(': StarPosition', ': GaiaStarPosition')
    
    # 3. Update docstrings
    content = content.replace(
        'Stars sourced from sefstars.txt via moira.fixed_stars.',
        'Stars sourced from the Sovereign Star Registry via Gaia DR3.'
    )
    
    f.write_text(content, encoding='utf-8')
    print(f"  Done: {f.name}")

print("Bulk Migration Complete.")
