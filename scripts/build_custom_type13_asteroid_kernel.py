"""
Build and verify a standalone type-13 asteroid kernel from JPL Horizons.

Default target:
    4179 Toutatis

The script writes:
    tests/artifacts/kernels/toutatis_type13_test.bsp
    tests/artifacts/kernels/toutatis_type13_test.metadata.json

The payload is fetched from the official JPL Horizons API and written through
Moira's own DAF/type-13 writer, then verified by reopening the resulting BSP
through SmallBodyKernel and checking node-epoch round-trip integrity.

Important unit law:
    Horizons VECTORS with ``OUT_UNITS=KM-S`` yields positions in km and
    velocities in km/s. Moira's type-13 Hermite path is seconds-based, so the
    written velocity samples must remain in km/s.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from moira._spk_body_kernel import SmallBodyKernel
from moira.daf_writer import write_spk_type13

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
OUTPUT_DIR = ROOT / "tests" / "artifacts" / "kernels"
OUTPUT_BSP = OUTPUT_DIR / "toutatis_type13_test.bsp"
OUTPUT_META = OUTPUT_DIR / "toutatis_type13_test.metadata.json"

TARGET = {
    "name": "Toutatis",
    "naif_id": 2004179,
    "command": "4179;",
    "center": 10,
    "frame": 1,
}


def _fetch_vectors(
    command: str,
    start: str,
    stop: str,
    step_days: int,
) -> tuple[list[float], list[list[float]], str]:
    params = {
        "format": "text",
        "COMMAND": command,
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER": "500@10",
        "REF_PLANE": "FRAME",
        "START_TIME": start,
        "STOP_TIME": stop,
        "STEP_SIZE": f"{step_days}d",
        "OUT_UNITS": "KM-S",
        "VEC_TABLE": "2",
        "VEC_LABELS": "YES",
        "CSV_FORMAT": "YES",
        "TIME_DIGITS": "FRACSEC",
    }
    url = f"{HORIZONS_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
    return (*_parse_vectors(raw), url)


def _parse_vectors(raw: str) -> tuple[list[float], list[list[float]]]:
    lines = raw.splitlines()
    soe = eoe = -1
    for i, line in enumerate(lines):
        if line.strip() == "$$SOE":
            soe = i
        elif line.strip() == "$$EOE":
            eoe = i
            break
    if soe < 0 or eoe < 0:
        raise RuntimeError("Horizons response missing $$SOE/$$EOE markers")

    data_lines = lines[soe + 1:eoe]
    epochs_jd: list[float] = []
    states: list[list[float]] = [[] for _ in range(6)]

    for line in data_lines:
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 8:
            continue
        try:
            jd = float(parts[0])
            x = float(parts[2]); y = float(parts[3]); z = float(parts[4])
            vx = float(parts[5]); vy = float(parts[6]); vz = float(parts[7])
        except ValueError:
            continue
        epochs_jd.append(jd)
        states[0].append(x)
        states[1].append(y)
        states[2].append(z)
        states[3].append(vx)
        states[4].append(vy)
        states[5].append(vz)

    if not epochs_jd:
        raise RuntimeError("No state vectors parsed from Horizons response")
    return epochs_jd, states


def _verify_round_trip(path: Path, naif_id: int, epochs_jd: list[float], states: list[list[float]]) -> dict[str, float]:
    kernel = SmallBodyKernel(path)
    try:
        max_node_error_km = 0.0
        for i, jd in enumerate(epochs_jd):
            got = kernel.position(naif_id, jd)
            want = (states[0][i], states[1][i], states[2][i])
            err = max(abs(a - b) for a, b in zip(got, want))
            max_node_error_km = max(max_node_error_km, err)

        midpoint_jd = 0.5 * (epochs_jd[len(epochs_jd) // 2 - 1] + epochs_jd[len(epochs_jd) // 2])
        midpoint = kernel.position(naif_id, midpoint_jd)
        midpoint_norm = math.sqrt(sum(coord * coord for coord in midpoint))
        return {
            "max_node_error_km": max_node_error_km,
            "midpoint_jd": midpoint_jd,
            "midpoint_radius_km": midpoint_norm,
        }
    finally:
        kernel.close()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    epochs_jd, states_km_s, url = _fetch_vectors(
        TARGET["command"],
        start="2020-Jan-01",
        stop="2030-Jan-01",
        step_days=30,
    )
    write_spk_type13(
        OUTPUT_BSP,
        bodies=[
            {
                "naif_id": TARGET["naif_id"],
                "name": TARGET["name"],
                "center": TARGET["center"],
                "frame": TARGET["frame"],
                "states": states_km_s,
                "epochs_jd": epochs_jd,
                "window_size": 5,
            }
        ],
        locifn="MOIRA CUSTOM ASTEROID TEST",
    )

    verification = _verify_round_trip(OUTPUT_BSP, TARGET["naif_id"], epochs_jd, states_km_s)
    payload = {
        "target": TARGET,
        "source": {
            "authority": "JPL Horizons",
            "url": url,
            "center": "500@10",
            "ref_plane": "FRAME",
            "units": {
                "position": "km",
                "velocity_source": "km/s",
                "velocity_written": "km/s",
            },
        },
        "coverage": {
            "start_jd": epochs_jd[0],
            "end_jd": epochs_jd[-1],
            "epoch_count": len(epochs_jd),
            "step_days": 30,
            "window_size": 5,
        },
        "output_bsp": str(OUTPUT_BSP.relative_to(ROOT)),
        "verification": verification,
    }
    OUTPUT_META.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
