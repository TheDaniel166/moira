from __future__ import annotations

import argparse
import json
import random
import statistics
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from moira._kernel_paths import find_kernel, find_planetary_kernel
from moira._spk_body_kernel import SmallBodyKernel
from moira.asteroids import ASTEROID_NAIF, asteroid_at
from moira.constants import Body
from moira.julian import julian_day
from moira.planets import planet_at
from moira.spk_reader import KernelPool, SpkReader

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
OUTPUT_DIR = ROOT / "tests" / "artifacts" / "oracle"
RANDOM_SEED = 20260509

PLANET_COMMANDS: list[tuple[str, str]] = [
    (Body.SUN, "10"),
    (Body.MOON, "301"),
    (Body.MERCURY, "199"),
    (Body.VENUS, "299"),
    (Body.MARS, "499"),
    (Body.JUPITER, "599"),
    (Body.SATURN, "699"),
    (Body.URANUS, "799"),
    (Body.NEPTUNE, "899"),
    (Body.PLUTO, "999"),
]

SMALL_BODY_KERNELS = (
    "sb441-n373s.bsp",
    "centaurs.bsp",
    "minor_bodies.bsp",
    "asteroids.bsp",
)


def _angle_diff_arcsec(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0 - 180.0) * 3600.0


def _observer_ecliptic(command: str, target_date: date) -> tuple[float, float]:
    start_dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=timezone.utc)
    stop_dt = start_dt + timedelta(days=1)
    fmt = "%Y-%b-%d %H:%M"
    params = {
        "format": "text",
        "COMMAND": command,
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",
        "START_TIME": f"'{start_dt.strftime(fmt)}'",
        "STOP_TIME": f"'{stop_dt.strftime(fmt)}'",
        "STEP_SIZE": "'1 d'",
        "QUANTITIES": "'31'",
        "ANG_FORMAT": "DEG",
    }
    url = HORIZONS_URL + "?" + urllib.parse.urlencode(params)
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
        parts = s.split()
        if len(parts) >= 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                pass

    preview = "\n".join(text.splitlines()[:40])
    raise RuntimeError(
        f"Could not parse Horizons observer response for {command}.\n"
        f"--- raw response (first 40 lines) ---\n{preview}"
    )


def _observer_ecliptic_with_fallbacks(commands: list[str], target_date: date) -> tuple[str, float, float]:
    errors: list[str] = []
    for command in commands:
        try:
            lon, lat = _observer_ecliptic(command, target_date)
            return command, lon, lat
        except Exception as exc:
            errors.append(f"{command}: {exc}")
    raise RuntimeError("All Horizons command candidates failed:\n" + "\n".join(errors))


def _planet_rows(jd_ut: float, target_date: date, reader: SpkReader) -> list[dict]:
    rows: list[dict] = []
    for body, command in PLANET_COMMANDS:
        result = planet_at(body, jd_ut, reader=reader)
        _, ref_lon, ref_lat = _observer_ecliptic_with_fallbacks([command], target_date)
        rows.append({
            "body": body,
            "command": command,
            "moira": {
                "longitude_deg": result.longitude,
                "latitude_deg": result.latitude,
                "distance_au": result.distance,
                "speed_lon_deg_per_day": result.speed,
            },
            "horizons": {
                "longitude_deg": ref_lon,
                "latitude_deg": ref_lat,
            },
            "delta": {
                "longitude_arcsec": _angle_diff_arcsec(result.longitude, ref_lon),
                "latitude_arcsec": (result.latitude - ref_lat) * 3600.0,
            },
        })
    return rows


def _build_small_body_pool(planetary_path: Path, manifest_path: Path | None = None) -> tuple[KernelPool, list]:
    readers = [SpkReader(planetary_path)]
    if manifest_path is not None:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for shard in payload.get("shards", []):
            path = ROOT / shard["path"]
            if path.exists():
                readers.append(SmallBodyKernel(path))
    else:
        for filename in SMALL_BODY_KERNELS:
            path = find_kernel(filename)
            if path.exists():
                readers.append(SmallBodyKernel(path))
    return KernelPool(readers), readers


def _available_asteroid_names(readers: list) -> list[str]:
    available_ids: set[int] = set()
    for reader in readers[1:]:
        if isinstance(reader, SmallBodyKernel):
            available_ids.update(reader.list_naif_ids())
    return sorted(name for name, naif_id in ASTEROID_NAIF.items() if naif_id in available_ids)


def _asteroid_command_candidates(name: str) -> list[str]:
    number = ASTEROID_NAIF[name] - 2_000_000
    return [f"'{number};'", f"'{number}'"]


def _asteroid_rows(pool: KernelPool, sample_names: list[str], jd_ut: float, target_date: date) -> list[dict]:
    rows: list[dict] = []
    for name in sample_names:
        result = asteroid_at(name, jd_ut, reader=pool)
        command, ref_lon, ref_lat = _observer_ecliptic_with_fallbacks(
            _asteroid_command_candidates(name),
            target_date,
        )
        rows.append({
            "body": name,
            "command": command,
            "moira": {
                "longitude_deg": result.longitude,
                "latitude_deg": result.latitude,
                "distance_km": result.distance,
                "speed_lon_deg_per_day": result.speed,
            },
            "horizons": {
                "longitude_deg": ref_lon,
                "latitude_deg": ref_lat,
            },
            "delta": {
                "longitude_arcsec": _angle_diff_arcsec(result.longitude, ref_lon),
                "latitude_arcsec": (result.latitude - ref_lat) * 3600.0,
            },
        })
    return rows


def _summary(rows: list[dict]) -> dict:
    lon_abs = [abs(row["delta"]["longitude_arcsec"]) for row in rows]
    lat_abs = [abs(row["delta"]["latitude_arcsec"]) for row in rows]
    worst_lon = max(rows, key=lambda row: abs(row["delta"]["longitude_arcsec"]))
    worst_lat = max(rows, key=lambda row: abs(row["delta"]["latitude_arcsec"]))
    return {
        "count": len(rows),
        "median_abs_longitude_arcsec": statistics.median(lon_abs) if lon_abs else 0.0,
        "median_abs_latitude_arcsec": statistics.median(lat_abs) if lat_abs else 0.0,
        "max_abs_longitude_arcsec": max(lon_abs) if lon_abs else 0.0,
        "max_abs_latitude_arcsec": max(lat_abs) if lat_abs else 0.0,
        "worst_longitude_body": worst_lon["body"] if rows else None,
        "worst_latitude_body": worst_lat["body"] if rows else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a public-surface JPL Horizons oracle audit.")
    parser.add_argument("--date", default=str(date.today()), help="UTC calendar date in YYYY-MM-DD form.")
    parser.add_argument("--asteroid-count", type=int, default=20, help="Number of random available asteroids to sample.")
    parser.add_argument("--body", action="append", default=[], help="Repeatable asteroid name to audit explicitly.")
    parser.add_argument("--small-body-manifest", type=Path, default=None, help="Optional manifest.json from sovereign type-13 shards.")
    parser.add_argument("--output-tag", default="", help="Optional suffix tag for the output artifact filename.")
    args = parser.parse_args()
    if args.small_body_manifest is not None and not args.small_body_manifest.is_absolute():
        args.small_body_manifest = ROOT / args.small_body_manifest

    target_date = date.fromisoformat(args.date)
    jd_ut = julian_day(target_date.year, target_date.month, target_date.day, 0.0)

    planetary_path = find_planetary_kernel()
    if planetary_path is None:
        raise RuntimeError("No planetary kernel is installed.")

    planetary_reader = SpkReader(planetary_path)
    try:
        planet_rows = _planet_rows(jd_ut, target_date, planetary_reader)
    finally:
        planetary_reader.close()

    pool, readers = _build_small_body_pool(planetary_path, args.small_body_manifest)
    try:
        available_names = _available_asteroid_names(readers)
        if args.body:
            sample_names = list(dict.fromkeys(args.body))
            missing = [name for name in sample_names if name not in available_names]
            if missing:
                raise RuntimeError(f"Requested bodies are not available in the selected small-body readers: {missing!r}")
        else:
            if len(available_names) < args.asteroid_count:
                raise RuntimeError(
                    f"Only {len(available_names)} available asteroid bodies found, "
                    f"need {args.asteroid_count}."
                )
            rng = random.Random(RANDOM_SEED)
            sample_names = sorted(rng.sample(available_names, args.asteroid_count))
        asteroid_rows = _asteroid_rows(pool, sample_names, jd_ut, target_date)
    finally:
        for reader in reversed(readers):
            reader.close()

    payload = {
        "date_utc": f"{target_date.isoformat()} 00:00:00",
        "jd_ut": jd_ut,
        "oracle": {
            "authority": "JPL Horizons",
            "product": "OBSERVER geocentric apparent ecliptic, QUANTITIES=31, CENTER=500@399",
        },
        "sampling": {
            "asteroid_seed": RANDOM_SEED,
            "asteroid_count": args.asteroid_count,
        },
        "planets": {
            "rows": planet_rows,
            "summary": _summary(planet_rows),
        },
        "asteroids": {
            "available_count": len(available_names),
            "sampled_bodies": sample_names,
            "rows": asteroid_rows,
            "summary": _summary(asteroid_rows),
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.output_tag}" if args.output_tag else ""
    output_path = OUTPUT_DIR / f"absolute_oracle_check_{target_date.isoformat()}{suffix}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path.relative_to(ROOT)), **payload["planets"]["summary"], **{
        "asteroid_median_abs_longitude_arcsec": payload["asteroids"]["summary"]["median_abs_longitude_arcsec"],
        "asteroid_max_abs_longitude_arcsec": payload["asteroids"]["summary"]["max_abs_longitude_arcsec"],
    }}, indent=2))


if __name__ == "__main__":
    main()
