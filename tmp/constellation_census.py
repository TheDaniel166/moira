import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from moira.data.star_registry import STAR_REGISTRY
import pkgutil
import moira.constellations

def get_star_names(module):
    for attr in dir(module):
        if attr.endswith("_STAR_NAMES") and not attr.startswith("FIXED_"):
            return getattr(module, attr)
    return None

misses = []
covered_count = 0

print(f"{'CONSTELLATION':<25} | {'MISSING STAR'}")
print("-" * 50)

# Iterate over all modules in moira.constellations
for loader, mod_name, is_pkg in pkgutil.walk_packages(moira.constellations.__path__, moira.constellations.__name__ + "."):
    try:
        # Import the module
        module = __import__(mod_name, fromlist=['dummy'])
        names_dict = get_star_names(module)
        if names_dict:
            for name in names_dict.values():
                if name not in STAR_REGISTRY:
                    short_name = mod_name.split('.')[-1]
                    print(f"{short_name:<25} | {name}")
                    misses.append((short_name, name))
                else:
                    covered_count += 1
    except Exception as e:
        # print(f"Error loading {mod_name}: {e}")
        continue

print("-" * 50)
print(f"Census Complete.")
print(f"Total Covered: {covered_count}")
print(f"Total Misses:  {len(misses)}")
