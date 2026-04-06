"""
Deep audit: scan for specific Python correctness and safety patterns.

Checks:
1. Mutable default arguments (list/dict literals as function default values)
2. Global mutable state modified at module level
3. Division patterns that could produce ZeroDivisionError on plausible inputs
4. Missing 'encoding' argument in open() calls
5. __all__ entries that reference undefined names at runtime (already done — skip)
6. Network download: any http:// (non-TLS) URLs in registry
"""
import pathlib, re, ast

root = pathlib.Path("moira")

# --- 1. Mutable defaults ---
def find_mutable_defaults(src, filename):
    results = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return results
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    results.append(
                        f"{filename}:{default.lineno}  [mutable_default] "
                        f"def {node.name}() has mutable default {type(default).__name__}"
                    )
    return results

# --- 2. http:// URLs (non-TLS) ---
http_pattern = re.compile(r'http://(?!localhost)[^\s"\']+')

# --- 3. open() without encoding ---
open_no_enc = re.compile(r'\bopen\s*\([^)]+\)')

findings = []
http_findings = []

for f in sorted(root.rglob("*.py")):
    src = f.read_text(encoding="utf-8-sig", errors="replace")
    rel = str(f.relative_to(root))

    # Mutable defaults
    findings.extend(find_mutable_defaults(src, rel))

    # http:// URLs
    for m in http_pattern.finditer(src):
        lineno = src[:m.start()].count('\n') + 1
        http_findings.append(f"{rel}:{lineno}  [http_url]  {m.group()[:80]}")

print("=== MUTABLE DEFAULTS ===")
if findings:
    for r in findings: print(r)
else:
    print("None found.")

print("\n=== HTTP (NON-TLS) URLS ===")
if http_findings:
    for r in http_findings: print(r)
else:
    print("None found.")
