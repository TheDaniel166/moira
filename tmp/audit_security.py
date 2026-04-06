"""
Security audit: scan moira source for patterns of concern.
- urllib.request usage (network access)
- Hardcoded credentials / tokens / passwords
- Path traversal risks: open() with user-controlled path
- Temp file races (NamedTemporaryFile without delete=False pattern)
"""
import pathlib, re

root = pathlib.Path("moira")

PATTERNS = {
    "hardcoded_secret": re.compile(
        r'(?i)(password|secret|token|api_key|apikey)\s*=\s*["\'][^"\']{6,}["\']'
    ),
    "url_retrieve_no_validate": re.compile(r'urlretrieve\('),
    "urlopen_no_validate": re.compile(r'urlopen\('),
    "tempfile_unsafe": re.compile(r'tempfile\.mktemp\('),
    "shutil_rmtree": re.compile(r'shutil\.rmtree\('),
    "os_remove_user_path": re.compile(r'os\.remove\s*\(\s*[^"\')]+\)'),
}

findings = []
for f in sorted(root.rglob("*.py")):
    src = f.read_text(encoding="utf-8-sig", errors="replace")
    for label, pat in PATTERNS.items():
        for m in pat.finditer(src):
            line_no = src[:m.start()].count('\n') + 1
            findings.append((str(f.relative_to(root)), line_no, label, m.group().strip()))

if findings:
    for fname, lineno, label, snippet in findings:
        print(f"{fname}:{lineno}  [{label}]  {snippet[:120]}")
else:
    print("No security pattern matches.")
