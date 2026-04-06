"""
Moira codebase statistics.
"""
import pathlib, ast, collections

root = pathlib.Path(".")
moira_root = root / "moira"
tests_root = root / "tests"
scripts_root = root / "scripts"

def file_stats(path: pathlib.Path):
    lines = code = comments = blank = 0
    try:
        src = path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return 0, 0, 0, 0
    for line in src.splitlines():
        lines += 1
        stripped = line.strip()
        if not stripped:
            blank += 1
        elif stripped.startswith("#"):
            comments += 1
        else:
            code += 1
    return lines, code, comments, blank

def count_symbols(path: pathlib.Path):
    """Count classes, functions, async functions defined in a file."""
    try:
        src = path.read_text(encoding="utf-8-sig", errors="replace")
        tree = ast.parse(src)
    except Exception:
        return 0, 0
    classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    funcs = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    return classes, funcs

def scan_dir(d: pathlib.Path, label: str):
    files = sorted(d.rglob("*.py")) if d.exists() else []
    total_lines = total_code = total_comments = total_blank = 0
    total_classes = total_funcs = 0
    sizes = []
    for f in files:
        l, c, cm, b = file_stats(f)
        cl, fn = count_symbols(f)
        total_lines += l
        total_code += c
        total_comments += cm
        total_blank += b
        total_classes += cl
        total_funcs += fn
        sizes.append((f.relative_to(d), l, c))
    return {
        "label": label,
        "files": len(files),
        "total_lines": total_lines,
        "code_lines": total_code,
        "comment_lines": total_comments,
        "blank_lines": total_blank,
        "classes": total_classes,
        "functions": total_funcs,
        "top10": sorted(sizes, key=lambda x: x[2], reverse=True)[:10],
        "all_files": sizes,
    }

moira = scan_dir(moira_root, "moira/")
tests = scan_dir(tests_root, "tests/")
scripts = scan_dir(scripts_root, "scripts/")

print("=" * 70)
print("MOIRA CODEBASE STATISTICS")
print("=" * 70)

for s in [moira, tests, scripts]:
    print(f"\n── {s['label']} ──────────────────────────────")
    print(f"  Python files     : {s['files']:>6,}")
    print(f"  Total lines      : {s['total_lines']:>6,}")
    print(f"  Code lines       : {s['code_lines']:>6,}")
    print(f"  Comment lines    : {s['comment_lines']:>6,}")
    print(f"  Blank lines      : {s['blank_lines']:>6,}")
    print(f"  Classes          : {s['classes']:>6,}")
    print(f"  Functions/methods: {s['functions']:>6,}")
    if s['top10']:
        print(f"\n  Top 10 by code lines:")
        for fname, lines, code in s['top10']:
            print(f"    {str(fname):<45} {code:>5} code / {lines:>5} total")

# Grand total
total_files = moira['files'] + tests['files'] + scripts['files']
total_lines = moira['total_lines'] + tests['total_lines'] + scripts['total_lines']
total_code  = moira['code_lines'] + tests['code_lines'] + scripts['code_lines']
total_cls   = moira['classes'] + tests['classes'] + scripts['classes']
total_fn    = moira['functions'] + tests['functions'] + scripts['functions']

print(f"\n{'=' * 70}")
print("TOTALS (moira + tests + scripts)")
print(f"{'=' * 70}")
print(f"  Python files     : {total_files:>6,}")
print(f"  Total lines      : {total_lines:>6,}")
print(f"  Code lines       : {total_code:>6,}")
print(f"  Classes          : {total_cls:>6,}")
print(f"  Functions/methods: {total_fn:>6,}")

# __all__ coverage
with_all = [f for f in sorted(moira_root.rglob("*.py"))
            if "__all__" in f.read_text(encoding="utf-8-sig", errors="replace")]
print(f"\n  moira/ __all__ coverage: {len(with_all)}/{moira['files']} modules")

# constellations breakdown
const_root = moira_root / "constellations"
const_files = list(const_root.rglob("*.py")) if const_root.exists() else []
print(f"  constellation data files: {len(const_files)}")

# Size distribution
buckets = collections.Counter()
for _, lines, code in moira['all_files']:
    if code < 50:      buckets['tiny  (<50)'] += 1
    elif code < 200:   buckets['small (50–199)'] += 1
    elif code < 500:   buckets['medium(200–499)'] += 1
    elif code < 1000:  buckets['large (500–999)'] += 1
    else:              buckets['xlarge(1000+)'] += 1

print(f"\n  moira/ file size distribution (by code lines):")
for label in ['tiny  (<50)', 'small (50–199)', 'medium(200–499)', 'large (500–999)', 'xlarge(1000+)']:
    print(f"    {label}: {buckets[label]:>3}")
