import pathlib, re

root = pathlib.Path("moira")
report = []

for f in sorted(root.rglob("*.py")):
    src = f.read_text(encoding="utf-8-sig", errors="replace")
    if "__all__" not in src:
        continue
    items = re.findall(r'__all__\s*=\s*\[([^\]]*)\]', src, re.DOTALL)
    for block in items:
        names = re.findall(r'"([^"]+)"|\'([^\']+)\'', block)
        flat = [a or b for a, b in names]
        dups = [n for n in set(flat) if flat.count(n) > 1]
        if dups:
            report.append(f"{f.relative_to(root)}: duplicates = {sorted(dups)}")

if report:
    for r in report:
        print(r)
else:
    print("No duplicates found in any __all__")
