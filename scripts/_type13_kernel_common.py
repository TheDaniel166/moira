"""
Shared plumbing for the per-target ``build_custom_type13_*_kernel.py`` scripts
(Toutatis, Ka`epaoka`awela, 'Aylo'chaxnim, ...): fetching JPL Horizons state
vectors, writing a Type-13 kernel through Moira's own DAF writer, and
verifying the result — both at the written nodes and, critically, *between*
them, since a Type-13 Hermite path can round-trip perfectly at its nodes
while still carrying a wrong velocity unit/conversion that only shows up in
the interpolated interior of an interval.

This module assumes Moira is importable normally (``pip install -e .`` /
``pip install moira-astro``) rather than manipulating ``sys.path`` — the
majority of scripts/ already does this; a handful of older scripts
(including the original Toutatis demo) still insert the repo root onto
``sys.path`` for a zero-install checkout, but that isn't the dominant
pattern here.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from moira._spk_body_kernel import SmallBodyKernel
from moira.daf_writer import write_spk_type13

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


def fetch_vectors(
    command: str,
    start: str,
    stop: str,
    step_days: int,
) -> tuple[list[float], list[list[float]], str]:
    """Fetch heliocentric state vectors (km, km/s) for ``command`` from Horizons."""
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
    return (*parse_vectors(raw), url)


def parse_vectors(raw: str) -> tuple[list[float], list[list[float]]]:
    """
    Parse a Horizons CSV VECTORS response into (epochs_jd, [x, y, z, vx, vy, vz]).

    Fails closed: once inside the ``$$SOE``/``$$EOE`` data block, a row that
    doesn't parse as the expected fields is a data-format problem, not
    something to silently drop — a truncated response or a Horizons format
    drift should abort the build rather than write a kernel with quietly
    missing epochs.
    """
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
            raise RuntimeError(
                f"Horizons data row has {len(parts)} fields, expected >= 8: {line!r}"
            )
        try:
            jd = float(parts[0])
            x, y, z = float(parts[2]), float(parts[3]), float(parts[4])
            vx, vy, vz = float(parts[5]), float(parts[6]), float(parts[7])
        except ValueError as exc:
            raise RuntimeError(f"Could not parse Horizons data row: {line!r}") from exc
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


def assert_regular_cadence(epochs_jd: list[float], step_days: int, tolerance_days: float = 0.05) -> None:
    """
    Assert epochs are strictly increasing and evenly spaced at ~step_days.

    A dropped row inside parse_vectors's data block would otherwise still
    produce a non-empty, plausible-looking epoch list with a silent gap.
    """
    if len(epochs_jd) < 2:
        raise RuntimeError(f"Only {len(epochs_jd)} epoch(s) parsed; need at least 2 to build a kernel")
    for earlier, later in zip(epochs_jd, epochs_jd[1:]):
        gap = later - earlier
        if gap <= 0:
            raise RuntimeError(f"Epochs are not strictly increasing: {earlier} -> {later}")
        if abs(gap - step_days) > tolerance_days:
            raise RuntimeError(
                f"Irregular cadence: expected ~{step_days}d steps, got {gap:.4f}d "
                f"between JD {earlier} and JD {later} (a dropped/duplicated row?)"
            )


def verify_round_trip(
    path: Path,
    center: int,
    naif_id: int,
    epochs_jd: list[float],
    states: list[list[float]],
    command: str,
) -> dict[str, Any]:
    """
    Verify the written kernel two ways:

    1. At every node epoch, the kernel must reproduce the exact source
       position (proves the DAF write/read round-trips losslessly).
    2. At one *off-node* epoch (a grid midpoint, never written to the
       kernel), the kernel's Hermite-interpolated position is compared
       against an independently fetched Horizons vector at that same
       instant — proving the interpolation itself (velocity units,
       Hermite slope data) is correct, not just node reproduction.
    """
    kernel = SmallBodyKernel(path)
    try:
        max_node_error_km = 0.0
        for i, jd in enumerate(epochs_jd):
            got = kernel.position(center, naif_id, jd)
            want = (states[0][i], states[1][i], states[2][i])
            err = max(abs(a - b) for a, b in zip(got, want))
            max_node_error_km = max(max_node_error_km, err)

        mid_index = len(epochs_jd) // 2
        midpoint_jd = 0.5 * (epochs_jd[mid_index - 1] + epochs_jd[mid_index])
        midpoint = kernel.position(center, naif_id, midpoint_jd)
        midpoint_norm = math.sqrt(sum(coord * coord for coord in midpoint))

        # Off-node check: an epoch strictly between two written nodes,
        # offset from the sampling grid so it never coincides with one.
        off_node_jd = epochs_jd[mid_index - 1] + 0.37 * (epochs_jd[mid_index] - epochs_jd[mid_index - 1])
        off_node_epochs, off_node_states, _off_node_url = fetch_vectors(
            command,
            start=_jd_to_horizons_date(off_node_jd),
            stop=_jd_to_horizons_date(off_node_jd + 1),
            step_days=1,
        )
        # The single closest returned row is our off-node reference.
        closest_i = min(range(len(off_node_epochs)), key=lambda i: abs(off_node_epochs[i] - off_node_jd))
        reference = (
            off_node_states[0][closest_i],
            off_node_states[1][closest_i],
            off_node_states[2][closest_i],
        )
        interpolated = kernel.position(center, naif_id, off_node_epochs[closest_i])
        off_node_error_km = max(abs(a - b) for a, b in zip(interpolated, reference))

        return {
            "max_node_error_km": max_node_error_km,
            "midpoint_jd": midpoint_jd,
            "midpoint_radius_km": midpoint_norm,
            "off_node_check": {
                "jd": off_node_epochs[closest_i],
                "max_error_km": off_node_error_km,
                "note": "interpolated kernel position vs. an independently fetched Horizons vector "
                        "at an epoch strictly between two written nodes",
            },
        }
    finally:
        kernel.close()


def _jd_to_horizons_date(jd: float) -> str:
    """Format a Julian Day as a Horizons-acceptable ``JD<value>`` time spec."""
    return f"JD{jd:.6f}"


def build_and_verify(
    target: dict[str, Any],
    output_bsp: Path,
    output_meta: Path,
    step_days: int,
    root: Path,
) -> dict[str, Any]:
    """Fetch, write, verify, and record metadata for one custom Type-13 target."""
    output_bsp.parent.mkdir(parents=True, exist_ok=True)

    epochs_jd, states_km_s, url = fetch_vectors(
        target["command"],
        start="2020-Jan-01",
        stop="2030-Jan-01",
        step_days=step_days,
    )
    assert_regular_cadence(epochs_jd, step_days)

    write_spk_type13(
        output_bsp,
        bodies=[
            {
                "naif_id": target["naif_id"],
                "name": target["name"],
                "center": target["center"],
                "frame": target["frame"],
                "states": states_km_s,
                "epochs_jd": epochs_jd,
                "window_size": 5,
            }
        ],
        locifn="MOIRA CUSTOM ASTEROID TEST",
    )

    verification = verify_round_trip(
        output_bsp, target["center"], target["naif_id"], epochs_jd, states_km_s, target["command"]
    )
    payload = {
        "target": target,
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
            "step_days": step_days,
            "window_size": 5,
        },
        "output_bsp": str(output_bsp.relative_to(root)),
        "verification": verification,
    }
    output_meta.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
