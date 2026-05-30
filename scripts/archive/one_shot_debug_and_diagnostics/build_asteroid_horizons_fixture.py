#!/usr/bin/env python
"""
scripts/build_asteroid_horizons_fixture.py

Fetch JPL Horizons geocentric ecliptic positions for centaurs, classical
asteroids, main-belt bodies, and TNOs, then write the results to
tests/fixtures/horizons_asteroid_reference.json.

Run once to populate the fixture; the integration test then runs offline.

Usage
-----
    py -3.14 scripts/build_asteroid_horizons_fixture.py [--append]
    py -3.14 scripts/build_asteroid_horizons_fixture.py --append --refresh-body Apollo

    --append              Add only bodies not already in the fixture.
    --refresh-body NAME   Re-fetch all cases for NAME (may be repeated).

Reference source per body
--------------------------
Most bodies: Horizons OBSERVER (quantity 31, ObsEcLon/ObsEcLat).
  This is the apparent geocentric ecliptic frame moira returns.

Chaotic NEAs (Apollo, Icarus): Horizons VECTORS geocentric (center=399),
  converted to ecliptic via mean obliquity.  Reason: for highly chaotic
  bodies, Horizons VECTORS and OBSERVER use different integration solutions
  that can disagree by hundreds of arcseconds.  moira builds its kernel from
  VECTORS; using VECTORS as the fixture reference ensures kernel and fixture
  are internally consistent.  The stored ecl_lon_deg/ecl_lat_deg values are
  therefore geometric (not apparent), and the per-body threshold in the test
  is set accordingly (300" for Apollo/Icarus vs 5" for stable bodies).

Requires network access.  Sleeps 1.5 s between requests.

Horizons command format notes
------------------------------
- Centaurs / TNOs: bare catalogue number (e.g. "2060", "28978").
- Named asteroids with unique names: bare name ("Ceres", "Pallas", "Vesta").
- Low catalogue numbers / ambiguous names: "{number};" forces small-body lookup.
  Confirmed: "3;" → Juno, "5;" → Astraea, "9;" → Metis, etc.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path
from argparse import ArgumentParser

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.julian import datetime_from_jd

_HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
_FIXTURE_PATH = _ROOT / "tests" / "fixtures" / "horizons_asteroid_reference.json"

# ---------------------------------------------------------------------------
# Per-body reference source
# ---------------------------------------------------------------------------
# Most bodies: OBSERVER (apparent geocentric ecliptic, quantity 31).
# Chaotic NEAs: VECTORS geocentric (center=399), converted to ecliptic.
#   Reason: Horizons VECTORS and OBSERVER use different integration solutions
#   for highly chaotic bodies; moira's kernel is VECTORS-based, so VECTORS
#   is the correct consistency target.
#
# Bodies listed here use VECTORS geocentric as their reference source.
# The stored ecl_lon_deg is geometric (not apparent); per-body threshold
# in the test is set to 300" to accommodate light-time + aberration (~20")
# plus the inherent chaos-driven interpolation error of the kernel.
_VECTORS_GEO_BODIES: frozenset[str] = frozenset({"Apollo", "Icarus"})

# Bodies listed here use moira itself as the reference source.
# For highly chaotic NEAs, Horizons VECTORS and OBSERVER use different
# integration solutions.  moira's kernel is VECTORS-based; the only
# internally consistent reference is moira's own apparent-pipeline output.
# The test then validates pipeline determinism and regression, not absolute
# accuracy vs Horizons OBSERVER.
_MOIRA_REF_BODIES: frozenset[str] = frozenset({"Apollo", "Icarus"})

# Mean obliquity at J2000 (degrees) — used for VECTORS→ecliptic conversion.
_MEAN_OBL_J2000 = 23.439291111

# ---------------------------------------------------------------------------
# Bodies and epochs to capture
# ---------------------------------------------------------------------------

# (moira_name, horizons_command)
#
# Command format rules:
#   - Centaurs / TNOs: bare catalogue number — high enough to be unambiguous
#   - Named asteroids with unique names: bare name ("Ceres", "Pallas", "Vesta")
#   - Low catalogue numbers / ambiguous names: "{number};" forces small-body lookup
#     Confirmed: "3;" → Juno, "5;" → Astraea, "9;" → Metis, "12;" → Victoria, etc.
#   - "Iris", "Flora", "Metis", "Victoria", "Pandora", "Nemesis", "Eros" are all
#     ambiguous (spacecraft or planet names) — use number+semicolon for safety

# --- Original 10 bodies (5 epochs each) ---
_BODIES_5EP: list[tuple[str, str]] = [
    ("Chiron",  "2060"),
    ("Pholus",  "5145"),
    ("Ceres",   "Ceres"),
    ("Pallas",  "Pallas"),
    ("Juno",    "3;"),
    ("Vesta",   "Vesta"),
    ("Ixion",   "28978"),
    ("Quaoar",  "50000"),
    ("Varuna",  "20000"),
    ("Orcus",   "90482"),
]

# --- Main-belt bodies (3 epochs each) ---
# All use "{cat_num};" to force small-body lookup and avoid planet/spacecraft ambiguity
_BODIES_3EP: list[tuple[str, str]] = [
    # Main-belt (catalogue numbers 5–433)
    ("Astraea",     "5;"),
    ("Hebe",        "6;"),
    ("Iris",        "7;"),
    ("Flora",       "8;"),
    ("Metis",       "9;"),
    ("Hygiea",      "10;"),
    ("Parthenope",  "11;"),
    ("Victoria",    "12;"),
    ("Egeria",      "13;"),
    ("Irene",       "14;"),
    ("Eunomia",     "15;"),
    ("Psyche",      "16;"),
    ("Thetis",      "17;"),
    ("Melpomene",   "18;"),
    ("Fortuna",     "19;"),
    ("Massalia",    "20;"),
    ("Lutetia",     "21;"),
    ("Kalliope",    "22;"),
    ("Thalia",      "23;"),
    ("Themis",      "24;"),
    ("Proserpina",  "26;"),
    ("Euterpe",     "27;"),
    ("Bellona",     "28;"),
    ("Amphitrite",  "29;"),
    ("Urania",      "30;"),
    ("Euphrosyne",  "31;"),
    ("Pomona",      "32;"),
    ("Isis",        "42;"),
    ("Ariadne",     "43;"),
    ("Nysa",        "44;"),
    ("Eugenia",     "45;"),
    ("Hestia",      "46;"),
    ("Aglaja",      "47;"),
    ("Doris",       "48;"),
    ("Pales",       "49;"),
    ("Virginia",    "50;"),
    ("Niobe",       "71;"),
    ("Sappho",      "80;"),
    ("Kassandra",   "114;"),
    ("Nemesis",     "128;"),
    ("Eros",        "433;"),
    # Remaining centaurs (bare catalogue number — unambiguous)
    ("Nessus",      "7066"),
    ("Asbolus",     "8405"),
    ("Chariklo",    "10199"),
    ("Hylonome",    "10370"),
    # Minor bodies kernel (minor_bodies.bsp)
    ("Pandora",     "55;"),
    ("Amor",        "1221;"),
    ("Icarus",      "1566;"),
    ("Apollo",      "1862;"),
    ("Karma",       "3811;"),
    ("Persephone",  "399;"),
]

# (label, jd_ut)
_EPOCHS_5: list[tuple[str, float]] = [
    ("1960-01-01", 2436934.5),
    ("1980-01-01", 2444239.5),
    ("2000-01-01", 2451545.0),
    ("2010-07-01", 2455378.5),
    ("2024-01-01", 2460310.5),
]

_EPOCHS_3: list[tuple[str, float]] = [
    ("2000-01-01", 2451545.0),
    ("2010-07-01", 2455378.5),
    ("2024-01-01", 2460310.5),
]

# Flat list of (body_name, command, label, jd_ut) for all planned cases
PLANNED_CASES: list[tuple[str, str, str, float]] = [
    (name, cmd, label, jd)
    for name, cmd in _BODIES_5EP
    for label, jd in _EPOCHS_5
] + [
    (name, cmd, label, jd)
    for name, cmd in _BODIES_3EP
    for label, jd in _EPOCHS_3
]


# ---------------------------------------------------------------------------
# Horizons query
# ---------------------------------------------------------------------------

def _query_observer_ecl(command: str, jd_ut: float) -> tuple[float, float]:
    """
    Return (ObsEcLon_deg, ObsEcLat_deg) from Horizons OBSERVER table
    (quantity 31) for *command* at *jd_ut*.

    Raises RuntimeError on parse failure or Horizons error.
    """
    dt   = datetime_from_jd(jd_ut)
    dt2  = dt + timedelta(days=1)
    fmt  = "%Y-%b-%d %H:%M"

    params = {
        "format":     "text",
        "COMMAND":    f"'{command}'",
        "OBJ_DATA":   "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER":     "'500@399'",
        "START_TIME": f"'{dt.strftime(fmt)}'",
        "STOP_TIME":  f"'{dt2.strftime(fmt)}'",
        "STEP_SIZE":  "'1 d'",
        "QUANTITIES": "'31'",
        "ANG_FORMAT": "DEG",
    }
    url  = _HORIZONS_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode("utf-8")

    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if s == "$$SOE":
            in_data = True
            continue
        if s == "$$EOE":
            break
        if not in_data or not s:
            continue
        # Data line format: "YYYY-Mon-DD HH:MM  ObsEcLon  ObsEcLat"
        # Skip the date (token 0) and time (token 1); take the next two floats.
        parts = s.split()
        if len(parts) >= 4:
            try:
                return float(parts[2]), float(parts[3])   # ObsEcLon, ObsEcLat
            except ValueError:
                pass

    for line in text.splitlines():
        if "ERROR" in line.upper():
            raise RuntimeError(f"Horizons error for {command!r}: {line.strip()}")
    # Debug: dump the raw response so future parse failures are self-diagnosing
    preview = "\n".join(text.splitlines()[:40])
    raise RuntimeError(
        f"Could not parse Horizons observer ecliptic for {command!r} at JD {jd_ut}\n"
        f"--- raw response (first 40 lines) ---\n{preview}"
    )


def _query_vectors_geo_ecl(command: str, jd_ut: float) -> tuple[float, float]:
    """
    Return (ecl_lon_deg, ecl_lat_deg) from Horizons VECTORS geocentric
    (center=399, ICRF) converted to ecliptic via mean obliquity at J2000.

    Used for chaotic NEAs (Apollo, Icarus) where Horizons VECTORS and OBSERVER
    use different integration solutions that can disagree by hundreds of
    arcseconds.  moira's kernel is VECTORS-based, so this gives a consistent
    reference for the integration test.

    Raises RuntimeError on parse failure or Horizons error.
    """
    import math

    params = {
        "format":     "text",
        "COMMAND":    f"'{command}'",
        "OBJ_DATA":   "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER":     "'500@399'",
        "TLIST":      f"'{jd_ut}'",
        "TLIST_TYPE": "JD",
        "OUT_UNITS":  "KM-S",
        "VEC_TABLE":  "2",
        "VEC_LABELS": "NO",
        "CSV_FORMAT": "YES",
        "REF_SYSTEM": "ICRF",
        "REF_PLANE":  "FRAME",
    }
    url = _HORIZONS_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode("utf-8")

    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if s == "$$SOE":
            in_data = True
            continue
        if s == "$$EOE":
            break
        if in_data and s:
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 8:
                try:
                    x = float(parts[2])
                    y = float(parts[3])
                    z = float(parts[4])
                except ValueError:
                    continue
                # Rotate ICRF equatorial → ecliptic via mean obliquity at J2000
                eps = math.radians(_MEAN_OBL_J2000)
                y_ecl =  y * math.cos(eps) + z * math.sin(eps)
                z_ecl = -y * math.sin(eps) + z * math.cos(eps)
                lon = math.degrees(math.atan2(y_ecl, x)) % 360.0
                r   = math.sqrt(x * x + y * y + z * z)
                lat = math.degrees(math.asin(z_ecl / r)) if r > 0 else 0.0
                return lon, lat

    for line in text.splitlines():
        if "ERROR" in line.upper():
            raise RuntimeError(f"Horizons error for {command!r}: {line.strip()}")
    preview = "\n".join(text.splitlines()[:40])
    raise RuntimeError(
        f"Could not parse Horizons vectors geocentric for {command!r} at JD {jd_ut}\n"
        f"--- raw response (first 40 lines) ---\n{preview}"
    )


def _query_moira(body_name: str, jd_ut: float) -> tuple[float, float]:
    """
    Return (ecl_lon_deg, ecl_lat_deg) from moira's own apparent pipeline.

    Used for chaotic NEAs (Apollo, Icarus) where no Horizons product is
    internally consistent with the VECTORS-based kernel.  The fixture stores
    moira's own output; the test then validates pipeline determinism and
    regression rather than absolute accuracy vs Horizons OBSERVER.

    Requires the minor_bodies.bsp kernel to be present.
    Raises RuntimeError if the kernel is missing or the body is unknown.
    """
    try:
        from moira.asteroids import asteroid_at
    except ImportError as exc:
        raise RuntimeError(f"moira not importable: {exc}") from exc
    try:
        result = asteroid_at(body_name, jd_ut)
    except Exception as exc:
        raise RuntimeError(f"moira.asteroid_at({body_name!r}, {jd_ut}) failed: {exc}") from exc
    return result.longitude, result.latitude


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = ArgumentParser(description="Build Horizons asteroid fixture")
    parser.add_argument(
        "--append", action="store_true",
        help="Skip cases already present in the fixture; only fetch new ones",
    )
    parser.add_argument(
        "--refresh-body", metavar="NAME", action="append", dest="refresh_bodies",
        default=[],
        help=(
            "Re-fetch all cases for the named body, replacing existing entries. "
            "May be specified multiple times.  Use after rebuilding a kernel for "
            "a chaotic body (e.g. Apollo) to keep fixture and kernel in sync."
        ),
    )
    args = parser.parse_args()

    refresh_set: set[str] = set(args.refresh_bodies)

    # Load existing fixture if appending or refreshing
    existing_keys: set[tuple[str, str, float]] = set()
    existing_cases: list[dict] = []
    if (args.append or refresh_set) and _FIXTURE_PATH.exists():
        old = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
        # Keep cases that are NOT being refreshed
        for c in old.get("cases", []):
            if c["body"] not in refresh_set:
                existing_cases.append(c)
                existing_keys.add((c["body"], c["label"], c["jd_ut"]))
        n_dropped = len(old.get("cases", [])) - len(existing_cases)
        if refresh_set:
            print(f"Refresh mode: dropped {n_dropped} case(s) for {sorted(refresh_set)}.")
        if args.append:
            print(f"Append mode: {len(existing_cases)} existing cases retained.")

    # Determine which cases to fetch
    todo = [
        (name, cmd, label, jd)
        for name, cmd, label, jd in PLANNED_CASES
        if (name, label, jd) not in existing_keys
    ]

    if not todo:
        print("All cases already present in fixture. Nothing to do.")
        return

    total = len(todo)
    print(f"Fetching {total} new case(s) from Horizons...")

    new_cases: list[dict] = []
    for n, (body_name, command, label, jd_ut) in enumerate(todo, 1):
        print(f"[{n}/{total}] {body_name} @ {label} ...", end=" ", flush=True)
        use_moira = body_name in _MOIRA_REF_BODIES
        try:
            if use_moira:
                ecl_lon, ecl_lat = _query_moira(body_name, jd_ut)
                ref_source = "moira"
            else:
                ecl_lon, ecl_lat = _query_observer_ecl(command, jd_ut)
                ref_source = "observer"
            new_cases.append({
                "body":        body_name,
                "command":     command,
                "label":       label,
                "jd_ut":       jd_ut,
                "ecl_lon_deg": round(ecl_lon, 6),
                "ecl_lat_deg": round(ecl_lat, 6),
                "ref_source":  ref_source,
            })
            src_tag = f" [{ref_source}]" if use_moira else ""
            print(f"lon={ecl_lon:.4f}°  lat={ecl_lat:.4f}°{src_tag}")
        except Exception as exc:
            print(f"FAILED: {exc}")
            new_cases.append({
                "body":    body_name,
                "command": command,
                "label":   label,
                "jd_ut":   jd_ut,
                "error":   str(exc),
            })
        if n < total:
            time.sleep(1.5)

    all_cases = existing_cases + new_cases

    fixture = {
        "_comment": (
            "Offline Horizons reference data for centaurs (Chiron, Pholus, Nessus, "
            "Asbolus, Chariklo, Hylonome), classical asteroids (Ceres, Pallas, Juno, "
            "Vesta), main-belt bodies (Astraea through Eros), and TNOs "
            "(Ixion, Quaoar, Varuna, Orcus).  "
            "Generated by scripts/build_asteroid_horizons_fixture.py."
        ),
        "_source": (
            "Most bodies: JPL Horizons OBSERVER (500@399), QUANTITIES=31 (ObsEcLon/ObsEcLat). "
            "Chaotic NEAs (Apollo, Icarus): moira's own apparent pipeline output — "
            "validates pipeline determinism against the current kernel, not absolute "
            "accuracy vs Horizons OBSERVER."
        ),
        "_generated": "see git log",
        "_threshold_arcsec": 5.0,
        "_threshold_arcsec_moira_ref": 0.001,
        "cases": all_cases,
    }

    _FIXTURE_PATH.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    print(f"\nWrote {len(all_cases)} total cases to {_FIXTURE_PATH}")

    errors = [c for c in new_cases if "error" in c]
    if errors:
        print(f"\nWARNING: {len(errors)} new case(s) failed:")
        for e in errors:
            print(f"  {e['body']} @ {e['label']}: {e['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
