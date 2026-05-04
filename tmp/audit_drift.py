#!/usr/bin/env python3
"""Audit drift between repo `moira/` and Web venv `moira/` site-packages copy.

Read-only. Writes artifacts to ./tmp/ relative to the repo root.
"""
from __future__ import annotations
import ast, difflib, hashlib, json, re
from pathlib import Path

REPO = Path(r"c:\Users\nilad\OneDrive\Desktop\Moira\moira")
DRIFT = Path(r"C:\Users\nilad\OneDrive\Desktop\Moira Web\.venv\Lib\site-packages\moira")
OUT = Path(r"c:\Users\nilad\OneDrive\Desktop\Moira\tmp")
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git", ".mypy_cache"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd"}
CONTRACT_RE = re.compile(r"\[MACHINE_CONTRACT v1\](.*?)\[/MACHINE_CONTRACT\]", re.DOTALL)


def walk(root):
    out = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(root).parts
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        if p.suffix in EXCLUDE_EXTS:
            continue
        out[p.relative_to(root).as_posix()] = p
    return out


def sha256(p):
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(source):
    info = {"all": None, "classes": {}, "functions": [], "contracts": []}
    if source.startswith("\ufeff"):
        source = source.lstrip("\ufeff")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return info
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                    info["all"] = [e.value for e in node.value.elts
                                   if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            info["classes"][node.name] = sorted(
                s.name for s in node.body
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and not s.name.startswith("_")
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            info["functions"].append(node.name)
    info["functions"].sort()
    for m in CONTRACT_RE.finditer(source):
        idm = re.search(r'"id"\s*:\s*"([^"]+)"', m.group(1))
        if idm:
            info["contracts"].append(idm.group(1))
    info["contracts"].sort()
    return info


def main():
    OUT.mkdir(exist_ok=True)
    print(f"Walking REPO  : {REPO}")
    a = walk(REPO)
    print(f"Walking DRIFT : {DRIFT}")
    b = walk(DRIFT)
    print(f"  REPO={len(a)} files, DRIFT={len(b)} files")

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    common = sorted(set(a) & set(b))
    modified = [r for r in common if sha256(a[r]) != sha256(b[r])]
    py_mod = [r for r in modified if r.endswith(".py")]
    bin_mod = [r for r in modified if not r.endswith(".py")]

    s = [f"# Drift Structural Report\n", f"REPO  : `{REPO}`", f"DRIFT : `{DRIFT}`", "",
         f"- Only in REPO: **{len(only_a)}**", f"- Only in DRIFT: **{len(only_b)}**",
         f"- Modified (both sides): **{len(modified)}** ({len(py_mod)} `.py`, {len(bin_mod)} binary/data)",
         f"- Identical: **{len(common) - len(modified)}**", "",
         "## Only in REPO", *[f"- `{r}`" for r in only_a],
         "", "## Only in DRIFT venv", *[f"- `{r}`" for r in only_b],
         "", "## Modified", *[f"- `{r}`" for r in modified]]
    (OUT / "drift_structural.md").write_text("\n".join(s), encoding="utf-8")

    patch = []
    bom_only = set()
    for rel in py_mod:
        try:
            raw_a = a[rel].read_text(encoding="utf-8-sig")
            raw_b = b[rel].read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            patch.append(f"# Skipped (encoding): {rel}\n"); continue
        if raw_a == raw_b:
            bom_only.add(rel)
            continue
        sa = raw_a.splitlines(keepends=True)
        sb = raw_b.splitlines(keepends=True)
        diff = list(difflib.unified_diff(sa, sb, fromfile=f"REPO/{rel}", tofile=f"DRIFT/{rel}", n=3))
        if diff:
            patch.extend(diff); patch.append("\n")
    (OUT / "drift_diff_full.patch").write_text("".join(patch), encoding="utf-8")

    sym = ["# Drift Symbol Report\n",
           "Per modified `.py`: differences in `__all__`, public classes/methods, public functions, and `[MACHINE_CONTRACT v1]` IDs.\n"]
    led = ["# Drift Ledger\n",
           "| File | ΔBytes | __all__ | Classes | Functions | Contracts | Notes |",
           "|------|--------|---------|---------|-----------|-----------|-------|"]

    for rel in py_mod:
        try:
            sa = a[rel].read_text(encoding="utf-8-sig")
            sb = b[rel].read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        ia, ib = extract(sa), extract(sb)
        all_add = sorted(set(ib["all"] or []) - set(ia["all"] or []))
        all_rem = sorted(set(ia["all"] or []) - set(ib["all"] or []))
        cls_add = sorted(set(ib["classes"]) - set(ia["classes"]))
        cls_rem = sorted(set(ia["classes"]) - set(ib["classes"]))
        cls_chg = [(c, sorted(set(ib["classes"][c]) - set(ia["classes"][c])),
                       sorted(set(ia["classes"][c]) - set(ib["classes"][c])))
                   for c in set(ia["classes"]) & set(ib["classes"])
                   if ia["classes"][c] != ib["classes"][c]]
        fn_add = sorted(set(ib["functions"]) - set(ia["functions"]))
        fn_rem = sorted(set(ia["functions"]) - set(ib["functions"]))
        con_add = sorted(set(ib["contracts"]) - set(ia["contracts"]))
        con_rem = sorted(set(ia["contracts"]) - set(ib["contracts"]))
        db = len(sb.encode("utf-8")) - len(sa.encode("utf-8"))

        sym.append(f"## `{rel}`")
        sym.append(f"- Byte delta (DRIFT − REPO): {db:+d}")
        if all_add or all_rem: sym.append(f"- `__all__` +{all_add} -{all_rem}")
        if cls_add or cls_rem: sym.append(f"- Public classes +{cls_add} -{cls_rem}")
        for c, am, rm in cls_chg: sym.append(f"- `{c}` methods +{am} -{rm}")
        if fn_add or fn_rem: sym.append(f"- Public functions +{fn_add} -{fn_rem}")
        if con_add or con_rem: sym.append(f"- MACHINE_CONTRACT ids +{con_add} -{con_rem}")
        any_surface = bool(all_add or all_rem or cls_add or cls_rem or cls_chg or fn_add or fn_rem or con_add or con_rem)
        if not any_surface:
            sym.append("- No public-surface changes (body-only).")
        sym.append("")

        fmt = lambda add, rem: f"+{len(add)}/-{len(rem)}" if (add or rem) else "—"
        cls_d = fmt(cls_add, cls_rem) + (f", ~{len(cls_chg)}" if cls_chg else "")
        if rel in bom_only:
            notes = "BOM-only (UTF-8 BOM prefix added in DRIFT; content identical)"
        elif not any_surface:
            notes = "body-only"
        else:
            notes = ""
        led.append(f"| `{rel}` | {db:+d} | {fmt(all_add, all_rem)} | {cls_d} | {fmt(fn_add, fn_rem)} | {fmt(con_add, con_rem)} | {notes} |")

    sym.append("\n## Files only in REPO\n" + "\n".join(f"- `{r}`" for r in only_a))
    sym.append("\n## Files only in DRIFT venv\n" + "\n".join(f"- `{r}`" for r in only_b))
    for r in only_a: led.append(f"| `{r}` | (REPO only) | — | — | — | — | absent in DRIFT |")
    for r in only_b: led.append(f"| `{r}` | (DRIFT only) | — | — | — | — | absent in REPO |")
    for r in bin_mod: led.append(f"| `{r}` | (binary) | — | — | — | — | binary/data modified |")

    (OUT / "drift_symbols.md").write_text("\n".join(sym), encoding="utf-8")
    (OUT / "drift_ledger.md").write_text("\n".join(led), encoding="utf-8")
    summary = {"repo": str(REPO), "drift": str(DRIFT), "counts": {
        "only_in_repo": len(only_a), "only_in_drift": len(only_b),
        "modified": len(modified), "modified_py": len(py_mod),
        "modified_binary": len(bin_mod), "identical": len(common) - len(modified),
        "bom_only_diff": len(bom_only),
        "modified_real": len(py_mod) - len(bom_only)},
        "bom_only_files": sorted(bom_only)}
    (OUT / "drift_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Done.", json.dumps(summary["counts"]))


if __name__ == "__main__":
    main()
