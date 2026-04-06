"""
Audit: find potential division-by-zero locations in moira source.
Reports any line containing '/ ' where the denominator could be zero
based on variable name heuristics (sin, cos, dist, r, sep, delta, etc.)
"""
import pathlib, re

root = pathlib.Path("moira")

# Patterns that suggest a dangerous denominator
risky_denom = re.compile(
    r'/\s*(sin_?\w*|cos_?\w*|dist\w*|sep\w*|delta\w*|diff\w*|'
    r'r\b|d\b|norm\w*|mag\w*|speed\w*|dt\b|period\w*|denom\w*)'
    r'(?!\s*=)'  # not an assignment
)

findings = []
for f in sorted(root.rglob("*.py")):
    if "test" in str(f):
        continue
    src = f.read_text(encoding="utf-8-sig", errors="replace")
    lines = src.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if risky_denom.search(line):
            findings.append(f"{f.relative_to(root)}:{i}  {stripped[:100]}")

print(f"=== POTENTIAL DIVISION-BY-ZERO CANDIDATES ({len(findings)}) ===")
for r in findings[:80]:
    print(r)
if len(findings) > 80:
    print(f"... and {len(findings)-80} more")
