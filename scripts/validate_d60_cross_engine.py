"""Reproduce conditioned D1->D60 corroboration with checksum-pinned sources.

External code is acquired only with --acquire, into an explicit directory
outside this repository. No external implementation is vendored or imported
by Moira. PyJHora's unchanged function/constant AST runs in an isolated child.
Maitreya's exact D60 branch/helpers run as C++, with its returned sign and an
instrumented intermediate longitude; this is not a full application build.

Windows requires installed MSVC. Use the project .venv and MOIRA_NO_DOWNLOAD=1.
Frozen fixtures contain numerical results and provenance, not external code.
Regeneration is explicit; never refresh fixtures to hide a disagreement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = Path(__file__).with_name("d60_cross_engine_sources.json")
TOLERANCE = 8 * math.ulp(2160.0)  # Predeclared binary64 budget, no sign tolerance.
SEED = 600017
BODIES = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
DATES = (
    "1800-01-01T12:00:00+00:00", "1900-06-15T03:45:00+00:00",
    "1950-11-23T18:30:00+00:00", "2000-01-01T12:00:00+00:00",
    "2026-10-07T00:00:00+00:00", "2050-03-21T06:15:00+00:00",
    "2100-09-22T23:59:00+00:00", "2400-12-31T12:00:00+00:00",
)

PYTHON_ORACLE = '''"""Private, unchanged pinned PyJHora D60 AST execution."""
import ast
from enum import IntEnum
import json
from pathlib import Path
import sys
from types import SimpleNamespace
out = Path(__file__).parent
tree = ast.parse((out / "pyjhora_const.py").read_text(encoding="utf-8"))
names = {"even_signs", "d60_chart_method_default"}
selected = [n for n in tree.body if
            (isinstance(n, ast.ClassDef) and n.name == "D60_CHART_METHOD") or
            (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
assert len(selected) == 3
namespace = {"IntEnum": IntEnum}
exec(compile(ast.Module(body=selected, type_ignores=[]), "pinned_pyjhora_const", "exec"), namespace)
const = SimpleNamespace(**{key: namespace[key] for key in names | {"D60_CHART_METHOD"}})
tree = ast.parse((out / "pyjhora_charts.py").read_text(encoding="utf-8"))
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "shashtyamsa_chart")
runtime = {"const": const}
exec(compile(ast.Module(body=[function], type_ignores=[]), "pinned_pyjhora_charts", "exec"), runtime)
assert "moira" not in sys.modules and "swisseph" not in sys.modules
json.dump(runtime["shashtyamsa_chart"](json.load(sys.stdin), chart_method=1), sys.stdout, allow_nan=False)
'''


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def acquire_sources(work, acquire):
    sources = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    for source in sources:
        path = work / source["file"]
        if not path.is_file():
            if not acquire:
                raise ValueError(f"Missing private source {path}; use --acquire explicitly")
            request = urllib.request.Request(source["url"], headers={"User-Agent": "Moira-validation"})
            with urllib.request.urlopen(request, timeout=30) as response:
                path.write_bytes(response.read())
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != source["sha256"]:
            raise ValueError(f"Source checksum mismatch: {path}")
    write_json(work / "source_manifest.json", sources)
    return sources


def build_maitreya(work):
    sources = {name: (work / name).read_text(encoding="utf-8") for name in
               ("maitreya_Varga.cpp", "maitreya_astrobase.cpp", "maitreya_astrobase.h", "maitreya_mathbase.cpp")}

    def function(file, signature):
        text = sources[file]
        start = text.index(signature)
        begin = text.index("{", start)
        level, end = 1, begin + 1
        while level:
            level += (text[end] == "{") - (text[end] == "}")
            end += 1
        return text[start:end]

    helpers = "\n".join([
        function("maitreya_mathbase.cpp", "double a_red("),
        function("maitreya_mathbase.cpp", "double red_deg("),
        function("maitreya_astrobase.cpp", "Rasi getRasi("),
        function("maitreya_astrobase.cpp", "double getRasiLen("),
    ])
    declaration = re.search(r"^double getRasiLen\([^\n]+;", sources["maitreya_astrobase.h"], re.M).group(0)
    branch = re.search(r"case V_SHASTIAMSA:\s*.*?break;", sources["maitreya_Varga.cpp"], re.S).group(0)
    if branch.count("ret =") != 1:
        raise ValueError("Pinned D60 branch changed")
    projection = re.search(r"rasi = getRasi\( red_deg\( ret \)\);", sources["maitreya_Varga.cpp"]).group(0)
    # Rasi's integer index is the only used type property. Source arithmetic,
    # casts, projection and helper definitions remain unchanged.
    code = ('#include <cmath>\n#include <iostream>\n#include <iomanip>\n'
            'using Rasi = int;\n' + declaration + '\n' + helpers + '\n'
            'int main() { double len; const int V_SHASTIAMSA=60;\n'
            'while(std::cin >> len) { double ret=0; Rasi rasi;\n'
            'switch(V_SHASTIAMSA) {\n' + branch + '\n}\n' + projection + '\n'
            'std::cout << rasi << " " << std::setprecision(17) << red_deg(ret) << "\\n";\n'
            '} return 0; }\n')
    (work / "maitreya_probe.cpp").write_text(code, encoding="utf-8")
    vswhere = Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")
    if not vswhere.is_file():
        raise ValueError("This validator requires installed Windows MSVC; no compiler is downloaded")
    installation = subprocess.check_output([str(vswhere), "-latest", "-products", "*", "-property", "installationPath"], text=True).strip()
    vcvars = Path(installation) / "VC/Auxiliary/Build/vcvars64.bat"
    if not vcvars.is_file():
        raise ValueError("MSVC environment script unavailable")
    batch = work / "compiler_environment.cmd"
    batch.write_text(f'@echo off\ncall "{vcvars}" >nul\nif errorlevel 1 exit /b 1\nset\n', encoding="utf-8")
    settings = subprocess.run(["cmd", "/d", "/c", str(batch)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    env = dict(os.environ)
    env.update(line.split("=", 1) for line in settings.stdout.splitlines() if "=" in line and not line.startswith("="))
    compilers = subprocess.check_output([str(vswhere), "-latest", "-products", "*", "-find", "VC/Tools/MSVC/**/bin/Hostx64/x64/cl.exe"], text=True).splitlines()
    if not compilers:
        raise ValueError("MSVC x64 compiler unavailable")
    args = [compilers[-1], "/nologo", "/std:c++17", "/EHsc", "/fp:precise", "/Od", str(work / "maitreya_probe.cpp"), "/Fe:" + str(work / "maitreya_probe.exe"), "/Fo:" + str(work / "maitreya_probe.obj")]
    build = subprocess.run(args, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (work / "maitreya_build.log").write_text(build.stdout + build.stderr, encoding="utf-8")
    if build.returncode:
        raise ValueError("Maitreya source-fragment build failed; inspect private build log")
    write_json(work / "maitreya_build.json", {"command": args, "exit_code": 0,
               "source_fragment_sha256": hashlib.sha256(code.encode()).hexdigest(),
               "executable_sha256": hashlib.sha256((work / "maitreya_probe.exe").read_bytes()).hexdigest()})


def input_corpus():
    from moira import Moira
    from moira._kernel_paths import find_planetary_kernel

    rows = []
    for segment in range(720):
        for fraction in (0.125, 0.25, 0.375):
            rows.append({"id": f"interior-{segment:03d}-{fraction}", "kind": "interior", "longitude": segment / 2 + fraction})
        start = segment / 2
        for side, longitude in [("exact", start), ("before", math.nextafter(start, -math.inf) if segment else math.nextafter(360.0, 0.0)), ("after", math.nextafter(start, math.inf))]:
            rows.append({"id": f"boundary-{segment:03d}-{side}", "kind": "boundary", "side": side, "longitude": longitude})
    rng = random.Random(SEED)
    for number in range(20000):
        rows.append({"id": f"random-{number:05d}", "kind": "random", "longitude": rng.random() * 360})
    kernel = find_planetary_kernel()
    if kernel is None or not kernel.is_file():
        raise ValueError("Installed planetary kernel required; downloads must remain disabled")
    engine = Moira(kernel_path=str(kernel))
    try:
        for date in DATES:
            chart = engine.chart(datetime.fromisoformat(date), bodies=list(BODIES), include_nodes=False)
            for frame in ("Lahiri", "Raman"):
                longitudes = engine._sidereal_longitudes_from_chart(chart, BODIES, ayanamsa_system=frame)
                for body in BODIES:
                    rows.append({"id": f"planet-{date[:10]}-{frame}-{body}", "kind": "planetary", "dt": date, "ayanamsa_system": frame, "body": body, "longitude": longitudes[body]})
    finally:
        if engine._reader_obj is not None:
            engine._reader_obj.close()
    return rows, str(kernel)


def compare(work, rows, kernel):
    from moira.varga import D60Method, shashtiamsha

    positions = []
    for row in rows:
        exact = Fraction.from_float(row["longitude"])
        sign = int(exact // 30)
        positions.append([row["id"], [sign, float(exact - sign * 30)]])
    runner = work / "oracle_pyjhora.py"
    runner.write_text(PYTHON_ORACLE, encoding="utf-8")
    py = subprocess.run([sys.executable, "-I", str(runner)], input=json.dumps(positions), capture_output=True, text=True, encoding="utf-8", check=True)
    py_rows = json.loads(py.stdout)
    if [row[0] for row in py_rows] != [row["id"] for row in rows]:
        raise ValueError("PyJHora output identity/count mismatch")
    (work / "pyjhora_outputs.json").write_text(py.stdout + "\n", encoding="utf-8")
    cpp = subprocess.run([str(work / "maitreya_probe.exe")], input="".join(format(row["longitude"], ".17g") + "\n" for row in rows), capture_output=True, text=True, encoding="utf-8", check=True)
    cpp_rows = [line.split() for line in cpp.stdout.splitlines()]
    if len(cpp_rows) != len(rows):
        raise ValueError("Maitreya output count mismatch")
    (work / "maitreya_outputs.txt").write_text(cpp.stdout, encoding="utf-8")
    stats, differences, frozen = {}, [], []
    rational_differences = []
    for row, py_row, cpp_row in zip(rows, py_rows, cpp_rows):
        point = shashtiamsha(row["longitude"], d60_method=D60Method.PVR_TEXTBOOK_LINEAR)
        exact = Fraction.from_float(row["longitude"])
        natal = int(exact // 30)
        within = exact - natal * 30
        part = int(within // Fraction(1, 2))
        sign = (natal + part) % 12
        degree = float((within - Fraction(part, 2)) * 60)
        if (point.sign_degree != degree or int(point.varga_longitude // 30) != sign or
                not (0 <= degree < 30 and sign * 30 <= point.varga_longitude < (sign + 1) * 30)):
            rational_differences.append(row["id"])
        py_sign, py_degree = py_row[1]
        cpp_sign, cpp_longitude = int(cpp_row[0]), float(cpp_row[1])
        cpp_degree = cpp_longitude - cpp_sign * 30
        stat = stats.setdefault(row["kind"], {"count": 0, "pyjhora_disagreements": 0, "maitreya_disagreements": 0, "pyjhora_max_degree_residual": 0.0, "maitreya_max_degree_residual": 0.0})
        stat["count"] += 1
        for name, other_sign, other_degree in [("pyjhora", py_sign, py_degree), ("maitreya", cpp_sign, cpp_degree)]:
            residual = abs(other_degree - degree)
            stat[name + "_max_degree_residual"] = max(stat[name + "_max_degree_residual"], residual)
            if other_sign != sign or residual > TOLERANCE or not (0 <= other_degree < 30):
                stat[name + "_disagreements"] += 1
                differences.append(row | {"engine": name, "reference_sign_index": sign, "reference_degree": degree, "other_sign_index": other_sign, "other_degree": other_degree})
        # Preserve every segment interior/boundary, the first 120 seeded random
        # inputs (not selected by residual), and every planetary input.
        if row["kind"] != "random" or int(row["id"].split("-")[1]) < 120:
            frozen.append(row | {"natal_sign_index": natal, "pyjhora_sign_index": py_sign, "pyjhora_sign_degree": py_degree, "maitreya_sign_index": cpp_sign, "maitreya_instrumented_longitude": cpp_longitude})
    write_json(work / "disagreements.json", {"rational": rational_differences, "external": differences})
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "corpus_count": len(rows), "random_seed": SEED,
               "numeric_absolute_tolerance_deg": TOLERANCE, "sign_tolerance": 0,
               "moira_rational_disagreements": len(rational_differences), "stats": stats,
               "planetary_kernel": kernel, "scope": "conditioned mapping; not independent ephemeris or full-application parity"}
    write_json(work / "comparison.json", receipt)
    if rational_differences or differences:
        raise ValueError("Comparison disagreed; private receipts retained, no fixture refreshed")
    return receipt, frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true", help="Explicitly acquire pinned public sources")
    parser.add_argument("--freeze-fixture", type=Path, help="Explicitly write reviewed numerical evidence")
    parser.add_argument("--check-fixture", type=Path, help="Reproduce and compare existing numerical evidence")
    args = parser.parse_args()
    work = args.work_dir.resolve()
    if work == ROOT or ROOT in work.parents:
        parser.error("External sources must remain outside the repository")
    if os.environ.get("MOIRA_NO_DOWNLOAD") != "1":
        parser.error("Set MOIRA_NO_DOWNLOAD=1 to prevent resource downloads")
    if args.freeze_fixture and args.check_fixture:
        parser.error("Choose freeze or check, never both")
    work.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT))
    sources = acquire_sources(work, args.acquire)
    build_maitreya(work)
    rows, kernel = input_corpus()
    write_json(work / "inputs.json", rows)
    receipt, frozen = compare(work, rows, kernel)
    fixture = {"schema_version": 1, "profile": "pvr_textbook_linear", "evidence_class": "cross_engine_corroboration",
               "pyjhora_scope": "unchanged D60 function/constants, explicit method 1; not PVR Jagannatha Hora",
               "maitreya_scope": "compiled exact D60 branch/helpers; returned sign and instrumented reduced intermediate; not a public full-position product",
               "planetary_scope": "Moira DE441 D1 inputs; independent conditioned D60 mapping only",
               "refresh_policy": "Explicit pinned-source validator; adjudicate all disagreements before any update",
               "source_manifest": sources, "numeric_absolute_tolerance_deg": TOLERANCE, "random_seed": SEED, "cases": frozen}
    if args.freeze_fixture:
        args.freeze_fixture.parent.mkdir(parents=True, exist_ok=True)
        # One case per line keeps this numerical evidence readable and small.
        header = json.dumps({key: value for key, value in fixture.items() if key != "cases"}, indent=2)
        content = header[:-2] + ',\n  "cases": [\n' + ',\n'.join('    ' + json.dumps(row, allow_nan=False) for row in frozen) + '\n  ]\n}\n'
        args.freeze_fixture.write_text(content, encoding="utf-8")
    if args.check_fixture:
        if json.loads(args.check_fixture.read_text(encoding="utf-8")) != fixture:
            raise ValueError("Frozen evidence differs; do not silently update it")
        receipt["frozen_fixture_reproduced"] = True
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
