#!/usr/bin/env python3
"""Build Stage 1 time, gravity, and frame authority candidates.

This tool accepts only the reviewed source artifacts named by the Stage 1
design. It verifies their exact bytes before parsing or compiling anything and
writes candidates to an operator-selected directory outside ``tests/fixtures``.
The tracked fixtures are accepted later through an ordinary reviewed diff.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
from typing import Any
import zipfile


GENERATOR_VERSION = "moira-orbital-authority-builder-v1"
J2000 = 2_451_545.0
SECONDS_PER_DAY = 86_400.0

SOURCE_CONTRACTS = {
    "gm": {
        "filename": "gm_Horizons.pck",
        "url": "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/gm_Horizons.pck",
        "bytes": 15_428,
        "sha256": "169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c",
        "owner": "JPL Solar System Dynamics",
    },
    "lsk": {
        "filename": "naif0012.tls",
        "url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
        "bytes": 5_257,
        "sha256": "678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b",
        "owner": "NASA/JPL NAIF",
    },
    "sofa": {
        "filename": "sofa_c-20231011.zip",
        "url": "https://www.iausofa.org/2023_1011_C/sofa_c-20231011.zip",
        "bytes": 3_686_708,
        "sha256": "375729d8c0a254fd27c55484de5c8b83cccef351e1ef19d9cf7f26f5485e5538",
        "owner": "IAU SOFA Board",
    },
}

_GM_IDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399)
_TIME_CASES = (2_433_282.5, 2_451_544.5, 2_451_545.0, 2_461_298.5, 2_470_171.5)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_source(path: Path, key: str, retrieved_utc: str) -> dict[str, Any]:
    contract = SOURCE_CONTRACTS[key]
    actual_bytes = path.stat().st_size
    actual_sha256 = _sha256(path)
    if path.name != contract["filename"]:
        raise SystemExit(
            f"{key} filename differs: {path.name!r} != {contract['filename']!r}"
        )
    if actual_bytes != contract["bytes"] or actual_sha256 != contract["sha256"]:
        raise SystemExit(
            f"{path.name} is not the reviewed source artifact: "
            f"bytes={actual_bytes}, sha256={actual_sha256}"
        )
    return {
        "owner": contract["owner"],
        "source_url": contract["url"],
        "retrieved_utc": retrieved_utc,
        "byte_count": actual_bytes,
        "source_sha256": actual_sha256,
    }


def _fortran_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def _parse_scalar_assignment(text: str, key: str) -> float:
    match = re.search(
        rf"(?m)^\s*{re.escape(key)}\s*=\s*(?:\(\s*)?"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DdEe][+-]?\d+)?)",
        text,
    )
    if match is None:
        raise SystemExit(f"could not parse {key} from reviewed source")
    return _fortran_float(match.group(1))


def _parse_lsk(text: str) -> dict[str, float | list[float]]:
    mean_anomaly = re.search(
        r"DELTET/M\s*=\s*\(\s*([^\s)]+)\s+([^\s)]+)", text
    )
    if mean_anomaly is None:
        raise SystemExit("could not parse DELTET/M from reviewed LSK")
    return {
        "delta_t_a_seconds": _parse_scalar_assignment(text, "DELTET/DELTA_T_A"),
        "k_seconds": _parse_scalar_assignment(text, "DELTET/K"),
        "eb": _parse_scalar_assignment(text, "DELTET/EB"),
        "m": [
            _fortran_float(mean_anomaly.group(1)),
            _fortran_float(mean_anomaly.group(2)),
        ],
    }


def _parse_gm(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for naif_id in _GM_IDS:
        matches = re.findall(
            rf"(?m)^\s*BODY{naif_id}_GM\s*=\s*\(\s*([^\s)]+)", text
        )
        if not matches:
            raise SystemExit(f"could not parse BODY{naif_id}_GM")
        # The PCK documents historical blocks before the active assignments.
        # SPICE's later assignment wins; freeze that same rule explicitly.
        values[str(naif_id)] = _fortran_float(matches[-1])
    return values


def _tdb_minus_tt_at_tdb(epoch_tdb: float, lsk: dict[str, Any]) -> float:
    seconds_from_j2000 = math.fsum((epoch_tdb, -J2000)) * SECONDS_PER_DAY
    m0, m1 = lsk["m"]
    mean_anomaly = math.remainder(m0 + m1 * seconds_from_j2000, math.tau)
    eccentric_anomaly = mean_anomaly + lsk["eb"] * math.sin(mean_anomaly)
    return lsk["k_seconds"] * math.sin(eccentric_anomaly)


def _time_case(jd_tt: float, lsk: dict[str, Any]) -> dict[str, float | int]:
    epoch_tdb = jd_tt
    previous: float | None = None
    for iteration in range(1, 9):
        offset = _tdb_minus_tt_at_tdb(epoch_tdb, lsk)
        epoch_tdb = math.fsum((jd_tt, offset / SECONDS_PER_DAY))
        if previous is not None and abs(offset - previous) <= 1.0e-15:
            return {
                "jd_tt": jd_tt,
                "jd_tdb": epoch_tdb,
                "tdb_minus_tt_seconds": offset,
                "iterations": iteration,
            }
        previous = offset
    raise SystemExit(f"TT/TDB authority iteration did not converge for {jd_tt}")


def _sofa_harness_source() -> str:
    return r'''
#include <math.h>
#include <stdio.h>
#include "sofa.h"
#include "sofam.h"

static void emit(const char *frame, const char *routine, double epoch_tt,
                 double r[3][3]) {
    int i, j;
    printf("%s|%s|%.17g", frame, routine, epoch_tt);
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) printf("|%.17g", r[i][j]);
    }
    printf("\n");
}

int main(void) {
    const double modern[] = {2415020.0, 2451545.0, 2461298.5, 2488070.0};
    const double long_epoch[] = {-10000.0, 0.0, 5000.0, 12000.0};
    int i;
    double r[3][3], dpsi, deps, epsa, epoch;

    for (i = 0; i < 4; i++) {
        epoch = modern[i];
        iauEcm06(DJ00, epoch - DJ00, r);
        emit("MEAN_ECLIPTIC_OF_DATE", "ECM06", epoch, r);
    }
    for (i = 0; i < 4; i++) {
        epoch = DJ00 + (long_epoch[i] - 2000.0) * 365.25;
        iauLtecm(long_epoch[i], r);
        emit("MEAN_ECLIPTIC_OF_DATE", "LTECM", epoch, r);
    }
    for (i = 0; i < 4; i++) {
        epoch = modern[i];
        iauPnm06a(DJ00, epoch - DJ00, r);
        iauNut06a(DJ00, epoch - DJ00, &dpsi, &deps);
        epsa = iauObl06(DJ00, epoch - DJ00);
        iauRx(epsa + deps, r);
        emit("TRUE_ECLIPTIC_OF_DATE", "OBL06_NUT06A_PNM06A_RX", epoch, r);
    }
    return 0;
}
'''


def _compile_sofa_cases(sofa_zip: Path) -> list[dict[str, Any]]:
    try:
        from setuptools._distutils import ccompiler
        from setuptools._distutils.sysconfig import customize_compiler
    except ImportError as exc:  # pragma: no cover - release environment failure
        raise SystemExit("setuptools is required to compile the SOFA C oracle") from exc

    with tempfile.TemporaryDirectory(prefix="moira-sofa-oracle-") as raw_temp:
        temp = Path(raw_temp)
        with zipfile.ZipFile(sofa_zip) as archive:
            archive.extractall(temp / "source")
        headers = list((temp / "source").rglob("sofa.h"))
        if len(headers) != 1:
            raise SystemExit(f"expected one sofa.h in archive, found {len(headers)}")
        source_dir = headers[0].parent
        sofa_sources = sorted(
            path
            for path in source_dir.glob("*.c")
            if not path.name.startswith("t_sofa_c")
        )
        if not sofa_sources:
            raise SystemExit("reviewed SOFA archive contains no C sources")
        harness = temp / "sofa_orbital_frames.c"
        harness.write_text(_sofa_harness_source(), encoding="utf-8")

        compiler = ccompiler.new_compiler()
        customize_compiler(compiler)
        build = temp / "build"
        build.mkdir()
        harness_objects = compiler.compile(
            [str(harness)],
            output_dir=str(build),
            include_dirs=[str(source_dir)],
        )
        sofa_objects = compiler.compile(
            [str(path) for path in sofa_sources],
            output_dir=str(build),
            include_dirs=[str(source_dir)],
        )
        library_names: list[str] = []
        # Windows process creation has a short command-line ceiling. Archive
        # the official translation units in bounded batches rather than
        # handing hundreds of object paths to one lib/link invocation.
        for batch_index, offset in enumerate(range(0, len(sofa_objects), 32)):
            library_name = f"sofa_{batch_index}"
            compiler.create_static_lib(
                sofa_objects[offset : offset + 32],
                library_name,
                output_dir=str(build),
            )
            library_names.append(library_name)
        executable = str(build / "sofa_orbital_frames")
        libraries = library_names
        if compiler.compiler_type != "msvc":
            libraries.append("m")
        compiler.link_executable(
            harness_objects,
            executable,
            libraries=libraries,
            library_dirs=[str(build)],
        )
        executable_path = Path(executable)
        if compiler.compiler_type == "msvc":
            executable_path = executable_path.with_suffix(".exe")

        import subprocess

        completed = subprocess.run(
            [str(executable_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        cases: list[dict[str, Any]] = []
        for line in completed.stdout.splitlines():
            parts = line.split("|")
            if len(parts) != 12:
                raise SystemExit(f"unexpected SOFA harness row: {line!r}")
            values = [float(value) for value in parts[3:]]
            cases.append(
                {
                    "frame": parts[0],
                    "routine": parts[1],
                    "epoch_tt": float(parts[2]),
                    "matrix": [values[0:3], values[3:6], values[6:9]],
                }
            )
        if len(cases) != 12:
            raise SystemExit(f"expected 12 SOFA frame cases, found {len(cases)}")
        return cases


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gm-pck", type=Path, required=True)
    parser.add_argument("--lsk", type=Path, required=True)
    parser.add_argument("--sofa-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    repository_root = Path(__file__).resolve().parents[1]
    output_dir = args.output_dir.resolve()
    tracked_fixture_dir = (repository_root / "tests" / "fixtures").resolve()
    if output_dir == tracked_fixture_dir or tracked_fixture_dir in output_dir.parents:
        raise SystemExit("candidate output must not be inside tests/fixtures")
    output_dir.mkdir(parents=True, exist_ok=True)
    retrieved_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    sources = {
        "horizons_gm": _verified_source(args.gm_pck.resolve(), "gm", retrieved_utc),
        "naif_lsk": _verified_source(args.lsk.resolve(), "lsk", retrieved_utc),
        "iau_sofa": _verified_source(args.sofa_zip.resolve(), "sofa", retrieved_utc),
    }
    lsk = _parse_lsk(args.lsk.read_text(encoding="ascii"))
    gm = _parse_gm(args.gm_pck.read_text(encoding="ascii"))
    time_payload = {
        "schema_version": "moira.orbital-time-authority.v1",
        "generator_version": GENERATOR_VERSION,
        "fixture_role": "time_and_gravity_authority",
        "sources": {
            "naif_lsk": sources["naif_lsk"],
            "horizons_gm": sources["horizons_gm"],
        },
        "time_model": {
            **lsk,
            "equation": "TDB-TT = K*sin(M + EB*sin(M)); M evaluated at TDB",
            "fixed_point_max_iterations": 8,
            "fixed_point_residual_seconds": 1.0e-15,
        },
        "time_cases": [_time_case(jd_tt, lsk) for jd_tt in _TIME_CASES],
        "gravity_model": {
            "units": "km^3/s^2",
            "assignment_rule": "last textual PCK assignment wins",
            "values_by_naif_id": gm,
        },
    }
    frame_payload = {
        "schema_version": "moira.orbital-frame-authority.v1",
        "generator_version": GENERATOR_VERSION,
        "fixture_role": "official_sofa_c_frame_matrices",
        "source": sources["iau_sofa"],
        "compiler_oracle": "official IAU SOFA C 2023-10-11",
        "cases": _compile_sofa_cases(args.sofa_zip.resolve()),
    }

    _write_json(output_dir / "orbital_time_naif0012_reference.json", time_payload)
    _write_json(output_dir / "orbital_frames_sofa_20231011_reference.json", frame_payload)
    print(f"wrote authority candidates to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
