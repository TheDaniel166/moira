from pathlib import Path

root = Path('moira')
count = 0

print("Scanning for legacy star imports...")
for f in root.rglob('*.py'):
    if f.name == 'fixed_stars_legacy.py': # Skip the legacy file itself
        continue
    
    content = f.read_text(encoding='utf-8')
    modified = False
    
    if 'from .fixed_stars' in content:
        content = content.replace('from .fixed_stars', 'from .stars')
        modified = True
    if 'import moira.fixed_stars' in content:
        content = content.replace('import moira.fixed_stars', 'import moira.stars')
        modified = True
    if 'fixed_star_at' in content:
        content = content.replace('fixed_star_at', 'star_at')
        modified = True
        
    if modified:
        f.write_text(content, encoding='utf-8')
        count += 1
        print(f"  Stabilized: {f.relative_to(root)}")

print(f"Total files stabilized: {count}")
