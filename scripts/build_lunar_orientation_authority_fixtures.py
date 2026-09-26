"""Acquire the frozen Horizons and NASA SVS lunar-orientation fixtures.

This is a maintainer tool, not a runtime dependency. It performs network I/O
only when invoked explicitly and writes only to ``--output-dir``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"
SVS_URL = "https://svs.gsfc.nasa.gov/vis/a000000/a005500/a005587/mooninfo_2026.json"
USER_AGENT = "Moira-Lunar-Orientation-Fixture-Builder/1.0"

CALIBRATION_CASES = (
    ("2026-09-26T00:00:00Z", None),
    (
        "2026-09-26T00:00:00Z",
        {"latitude_deg": 40.7128, "longitude_deg": -74.006, "elevation_m": 10.0},
    ),
)
HOLDOUT_CASES = tuple(
    (stamp, None)
    for stamp in (
        "2026-01-01T00:00:00Z",
        "2026-03-25T00:00:00Z",
        "2026-12-31T00:00:00Z",
    )
)
SVS_HOLDOUT_TIMES = {
    "01 Jan 2026 00:00 UT",
    "26 Sep 2026 00:00 UT",
    "31 Dec 2026 23:00 UT",
}


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _horizons_url(stamp: str, observer: dict[str, float] | None) -> str:
    start = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    stop = start + timedelta(minutes=2)
    params = {
        "format": "text",
        "COMMAND": "'301'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'500@399'" if observer is None else "'coord@399'",
        "START_TIME": f"'{start:%Y-%m-%d %H:%M}'",
        "STOP_TIME": f"'{stop:%Y-%m-%d %H:%M}'",
        "STEP_SIZE": "'1 m'",
        "QUANTITIES": "'14,15,16,17'",
    }
    if observer is not None:
        params["COORD_TYPE"] = "'GEODETIC'"
        params["SITE_COORD"] = (
            f"'{observer['longitude_deg']},{observer['latitude_deg']},"
            f"{observer['elevation_m'] / 1000.0}'"
        )
    return f"{HORIZONS_API}?{urllib.parse.urlencode(params)}"


def _signed_longitude(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _horizons_case(stamp: str, observer: dict[str, float] | None) -> dict[str, object]:
    url = _horizons_url(stamp, observer)
    payload = _fetch(url)
    text = payload.decode("utf-8")
    try:
        data_line = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip().splitlines()[0]
    except IndexError as exc:
        raise RuntimeError("Horizons response has no ephemeris data block") from exc
    numbers = [float(token) for token in data_line.split() if _is_float(token)]
    if len(numbers) < 8:
        raise RuntimeError(f"Horizons response row is not understood: {data_line!r}")
    values = numbers[-8:]
    return {
        "utc": stamp,
        "observer": observer,
        "sub_observer_longitude_east_deg": _signed_longitude(values[0]),
        "sub_observer_latitude_deg": values[1],
        "sub_solar_longitude_east_deg": _signed_longitude(values[2]),
        "sub_solar_latitude_deg": values[3],
        "bright_limb_position_angle_deg": values[4],
        "axis_position_angle_deg": values[6],
        "query_url": url,
        "response_byte_length": len(payload),
        "response_sha256": hashlib.sha256(payload).hexdigest(),
    }


def _horizons_fixture(cases: tuple[tuple[str, dict[str, float] | None], ...]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "authority": "JPL Horizons API",
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "Moon (301)",
        "target_frame": "MOON_ME_DE440_ME421",
        "longitude_convention": "east-positive",
        "position_angle_convention": "counter-clockwise from true-of-date north",
        "quantities": [14, 15, 16, 17],
        "cases": [_horizons_case(stamp, observer) for stamp, observer in cases],
    }


def _svs_fixture() -> dict[str, object]:
    payload = _fetch(SVS_URL)
    rows = json.loads(payload)
    selected = {row["time"]: row for row in rows if row["time"] in SVS_HOLDOUT_TIMES}
    if set(selected) != SVS_HOLDOUT_TIMES:
        raise RuntimeError("NASA SVS response is missing a selected holdout row")
    cases = []
    ordered_times = sorted(
        SVS_HOLDOUT_TIMES,
        key=lambda value: datetime.strptime(value, "%d %b %Y %H:%M UT"),
    )
    for source_time in ordered_times:
        row = selected[source_time]
        dt = datetime.strptime(source_time, "%d %b %Y %H:%M UT").replace(
            tzinfo=timezone.utc
        )
        cases.append(
            {
                "utc": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sub_observer_longitude_east_deg": row["subearth"]["lon"],
                "sub_observer_latitude_deg": row["subearth"]["lat"],
                "sub_solar_longitude_east_deg": row["subsolar"]["lon"],
                "sub_solar_latitude_deg": row["subsolar"]["lat"],
                "axis_position_angle_j2000_deg": row["posangle"],
            }
        )
    return {
        "schema_version": 1,
        "authority": "NASA Scientific Visualization Studio Moon Phase and Libration 2026",
        "source_url": SVS_URL,
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_byte_length": len(payload),
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "longitude_convention": "east-positive",
        "position_angle_convention": "counter-clockwise from J2000 celestial north",
        "cases": cases,
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write(
        args.output_dir / "lunar_orientation_horizons_calibration.json",
        _horizons_fixture(CALIBRATION_CASES),
    )
    _write(
        args.output_dir / "lunar_orientation_horizons_holdout.json",
        _horizons_fixture(HOLDOUT_CASES),
    )
    _write(
        args.output_dir / "lunar_orientation_svs_2026_holdout.json",
        _svs_fixture(),
    )


if __name__ == "__main__":
    main()
