#!/usr/bin/env python
"""
scripts/build_comet_kernel.py

Fetch JPL Horizons heliocentric state vectors for the five curated periodic
comets and write a type 13 SPK kernel at the resolver path returned by
moira._kernel_paths.find_kernel("comets.bsp") unless --output is provided.

Curated comets
--------------
    1P/Halley               NAIF 1000001
    2P/Encke                NAIF 1000002
    9P/Tempel 1             NAIF 1000009
    67P/Churyumov-Gerasimenko NAIF 1000067
    109P/Swift-Tuttle       NAIF 1000109

Horizons query parameters
--------------------------
    EPHEM_TYPE  = VECTORS
    CENTER      = 500@10    (heliocentric; Sun-centered)
    REF_PLANE   = FRAME     (ICRF/J2000)
    OUT_UNITS   = KM-S
    VEC_TABLE   = 2         (state vectors: x y z vx vy vz)
    TIME_DIGITS = FRACSEC
    CSV_FORMAT  = YES

Coverage: 1800-Jan-01 to 2200-Jan-01, step 30 days.
Swift-Tuttle has a short Horizons solution window; coverage may be narrower.

Usage
-----
    cd <repo root>
    py -3 scripts/build_comet_kernel.py [--output PATH] [--step DAYS]

    --output PATH   Override output path (default: find_kernel("comets.bsp"))
    --step DAYS     Sampling step in days (default: 30)
    --start JD      Start JD (default: 2378497.5 = 1800-Jan-01)
    --end JD        End JD   (default: 2524611.5 = 2200-Jan-01)
    --dry-run       Print Horizons URLs and exit without writing anything
"""

from __future__ import annotations

import sys
import time
import argparse
import urllib.request
import urllib.parse
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.daf_writer import write_spk_type13
from moira._kernel_paths import find_kernel

# ---------------------------------------------------------------------------
# Comet registry
# ---------------------------------------------------------------------------

# Horizons periodic comet designations.
# Horizons small-body API requests for periodic comets need an explicit
# designation search plus directives to select one non-fragment apparition,
# e.g. COMMAND='DES=1P;NOFRAG;CAP'.
COMET_REGISTRY: list[dict] = [
    {"name": "Halley",                "designation": "1P",   "naif_id": 1000001},
    {"name": "Encke",                 "designation": "2P",   "naif_id": 1000002},
    {"name": "Tempel1",               "designation": "9P",   "naif_id": 1000009},
    {"name": "Churyumov-Gerasimenko", "designation": "67P",  "naif_id": 1000067},
    {"name": "Swift-Tuttle",          "designation": "109P", "naif_id": 1000109},
]

_HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Default time coverage
_DEFAULT_START_JD = 2378497.5   # 1800-Jan-01 TDB
_DEFAULT_END_JD   = 2524611.5   # 2200-Jan-01 TDB
_DEFAULT_STEP     = 30          # days

_SLEEP_BETWEEN = 1.5            # seconds between Horizons requests


# ---------------------------------------------------------------------------
# Horizons fetch
# ---------------------------------------------------------------------------

def _jd_to_cal(jd: float) -> str:
    """Convert JD to Horizons calendar string 'YYYY-MMM-DD'."""
    # Meeus, Chapter 7
    jd2 = jd + 0.5
    z = int(jd2)
    f = jd2 - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
    return f"{year}-{months[month-1]}-{day:02d}"


def _horizons_command(designation: str) -> str:
    """Return the Horizons small-body search for a periodic comet."""
    return f"'DES={designation};NOFRAG;CAP'"


def _fetch_vectors(
    designation: str,
    start_jd: float,
    end_jd: float,
    step_days: int,
) -> tuple[list[float], list[list[float]]]:
    """
    Fetch heliocentric ICRF state vectors from JPL Horizons.

    Returns
    -------
    (epochs_jd, states)
    epochs_jd : list of N JD floats (TDB)
    states    : (6, N) list — rows: x, y, z, vx, vy, vz  (km / km·s⁻¹)
    """
    start_str = _jd_to_cal(start_jd)
    end_str   = _jd_to_cal(end_jd)
    command = _horizons_command(designation)

    params = {
        "format":       "text",
        "COMMAND":      command,
        "OBJ_DATA":     "NO",
        "MAKE_EPHEM":   "YES",
        "EPHEM_TYPE":   "VECTORS",
        "CENTER":       "500@10",        # Sun-centered ICRF
        "REF_PLANE":    "FRAME",
        "START_TIME":   start_str,
        "STOP_TIME":    end_str,
        "STEP_SIZE":    f"{step_days}d",
        "OUT_UNITS":    "KM-S",
        "VEC_TABLE":    "2",
        "VEC_LABELS":   "YES",
        "CSV_FORMAT":   "YES",
        "TIME_DIGITS":  "FRACSEC",
    }

    url = f"{_HORIZONS_URL}?{urllib.parse.urlencode(params)}"
    print(f"  Fetching: {url[:120]}...")

    with urllib.request.urlopen(url, timeout=120) as resp:
        raw = resp.read().decode("utf-8")

    return _parse_horizons_vectors(raw)


def _parse_horizons_vectors(
    raw: str,
) -> tuple[list[float], list[list[float]]]:
    """
    Parse the $$SOE / $$EOE block from a Horizons VECTORS CSV response.

    Returns (epochs_jd, states) where states is (6, N).
    """
    lines = raw.splitlines()

    # Locate $$SOE and $$EOE markers
    soe = eoe = -1
    for i, line in enumerate(lines):
        if line.strip() == "$$SOE":
            soe = i
        elif line.strip() == "$$EOE":
            eoe = i
            break

    if soe < 0 or eoe < 0:
        raise ValueError(
            f"Could not find $$SOE/$$EOE markers in Horizons response.\n"
            f"Response head:\n{raw[:2000]}"
        )

    data_lines = lines[soe + 1 : eoe]

    epochs_jd: list[float] = []
    states: list[list[float]] = [[] for _ in range(6)]

    i = 0
    while i < len(data_lines):
        line = data_lines[i].strip()
        if not line:
            i += 1
            continue

        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            i += 1
            continue

        try:
            jd = float(parts[0])
        except ValueError:
            i += 1
            continue

        # Current Horizons API output is one CSV row per epoch:
        # JDTDB, Calendar, X, Y, Z, VX, VY, VZ,
        if len(parts) >= 8:
            try:
                x = float(parts[2]);  y = float(parts[3]);  z = float(parts[4])
                vx = float(parts[5]); vy = float(parts[6]); vz = float(parts[7])
            except ValueError:
                i += 1
                continue

            epochs_jd.append(jd)
            states[0].append(x)
            states[1].append(y)
            states[2].append(z)
            states[3].append(vx)
            states[4].append(vy)
            states[5].append(vz)
            i += 1
            continue

        # Older Horizons CSV output grouped one epoch across multiple rows:
        # Line 1: JDTDB, Cal, ...
        # Line 2: X, Y, Z,
        # Line 3: VX, VY, VZ,
        # Line 4: LT, RG, RR,  (ignored)
        if i + 2 >= len(data_lines):
            break

        parts2 = [p.strip() for p in data_lines[i + 1].split(",")]
        parts3 = [p.strip() for p in data_lines[i + 2].split(",")]

        try:
            x = float(parts2[0]);  y = float(parts2[1]);  z = float(parts2[2])
            vx = float(parts3[0]); vy = float(parts3[1]); vz = float(parts3[2])
        except (ValueError, IndexError):
            i += 1
            continue

        epochs_jd.append(jd)
        states[0].append(x)
        states[1].append(y)
        states[2].append(z)
        states[3].append(vx)
        states[4].append(vy)
        states[5].append(vz)

        i += 4

    if not epochs_jd:
        raise ValueError(
            "No epochs parsed from Horizons response.\n"
            f"Response head:\n{raw[:2000]}"
        )

    print(f"    Parsed {len(epochs_jd)} state vectors.")
    return epochs_jd, states


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_comet_kernel(
    output: Path,
    start_jd: float,
    end_jd: float,
    step_days: int,
    dry_run: bool = False,
) -> None:
    print(f"Building comet kernel -> {output}")
    print(f"Coverage: JD {start_jd:.1f} – {end_jd:.1f}  "
          f"({_jd_to_cal(start_jd)} to {_jd_to_cal(end_jd)}), "
          f"step {step_days} d")
    print()

    bodies: list[dict] = []

    for comet in COMET_REGISTRY:
        name         = comet["name"]
        designation  = comet["designation"]
        naif_id      = comet["naif_id"]

        print(f"[{name}]  NAIF {naif_id}  Horizons {_horizons_command(designation)}")

        if dry_run:
            params = {
                "COMMAND":    _horizons_command(designation),
                "EPHEM_TYPE": "VECTORS",
                "CENTER":     "500@10",
                "START_TIME": _jd_to_cal(start_jd),
                "STOP_TIME":  _jd_to_cal(end_jd),
                "STEP_SIZE":  f"{step_days}d",
            }
            url = f"{_HORIZONS_URL}?{urllib.parse.urlencode(params)}"
            print(f"  DRY-RUN URL: {url}")
            print()
            continue

        try:
            epochs_jd, states = _fetch_vectors(
                designation, start_jd, end_jd, step_days
            )
        except Exception as exc:
            print(f"  WARNING: fetch failed for {name}: {exc}")
            print(f"  Skipping {name}.")
            print()
            time.sleep(_SLEEP_BETWEEN)
            continue

        bodies.append({
            "naif_id":     naif_id,
            "name":        name,
            "center":      10,      # Sun
            "frame":       1,       # ICRF/J2000
            "states":      states,
            "epochs_jd":   epochs_jd,
            "window_size": 7,
        })

        print()
        time.sleep(_SLEEP_BETWEEN)

    if dry_run:
        print("Dry run complete. No kernel written.")
        return

    if not bodies:
        print("ERROR: No bodies fetched. Kernel not written.")
        sys.exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    write_spk_type13(output, bodies, locifn="MOIRA COMET KERNEL")
    print(f"Kernel written: {output}  ({output.stat().st_size:,} bytes)")
    print(f"Bodies written: {[b['name'] for b in bodies]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Moira comet SPK kernel from JPL Horizons."
    )
    parser.add_argument(
        "--output", type=Path,
        default=None,
        help="Output .bsp path (default: resolver path for comets.bsp)",
    )
    parser.add_argument(
        "--step", type=int, default=_DEFAULT_STEP,
        help=f"Sampling step in days (default: {_DEFAULT_STEP})",
    )
    parser.add_argument(
        "--start", type=float, default=_DEFAULT_START_JD,
        help=f"Start JD TDB (default: {_DEFAULT_START_JD} = 1800-Jan-01)",
    )
    parser.add_argument(
        "--end", type=float, default=_DEFAULT_END_JD,
        help=f"End JD TDB (default: {_DEFAULT_END_JD} = 2200-Jan-01)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print Horizons query URLs and exit without fetching or writing.",
    )
    args = parser.parse_args()

    if args.output is None:
        # Keep write default aligned with runtime kernel lookup policy.
        output = find_kernel("comets.bsp")
    else:
        output = args.output

    build_comet_kernel(
        output=output,
        start_jd=args.start,
        end_jd=args.end,
        step_days=args.step,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
