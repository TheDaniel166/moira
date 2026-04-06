"""
Audit script: check that every name listed in a module's __all__
actually exists as a binding in that module at runtime.
"""
import importlib, pathlib, sys, types

root = pathlib.Path("moira")
missing_report = []
import_errors = []

# Collect modules that have __all__
modules_with_all = []
for f in sorted(root.rglob("*.py")):
    rel = f.relative_to(root.parent)
    mod_name = str(rel).replace("\\", "/").replace("/", ".")[:-3]
    modules_with_all.append(mod_name)

for mod_name in modules_with_all:
    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        import_errors.append(f"{mod_name}: IMPORT ERROR: {e}")
        continue
    all_ = getattr(mod, "__all__", None)
    if all_ is None:
        continue
    for name in all_:
        if not hasattr(mod, name):
            missing_report.append(f"{mod_name}: '{name}' in __all__ but not defined")

print("=== IMPORT ERRORS ===")
for e in import_errors:
    print(e)

print(f"\n=== MISSING BINDINGS ({len(missing_report)}) ===")
for m in missing_report:
    print(m)

if not import_errors and not missing_report:
    print("All clean.")
