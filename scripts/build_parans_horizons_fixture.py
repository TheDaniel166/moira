from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.tools.horizons import observer_event_times


FIXTURE_PATH = ROOT / "tests" / "fixtures" / "parans_horizons_reference.json"

_CIRCLE_NAME = {
    "Rise": "Rising",
    "Set": "Setting",
    "Transit": "Culminating",
    "AntiTransit": "AntiCulminating",
}

_CASES = [
    {
        "id": "sun-moon-new-york-tight",
        "location": {"label": "New York City, USA", "latitude_deg": 40.7128, "longitude_deg": -74.006, "elevation_km": 0.0},
        "jd_start": 2460394.5,
        "orb_minutes": 4.0,
        "bodies": [
            {"body": "Sun", "command": "10"},
            {"body": "Moon", "command": "301"},
        ],
        "notes": "Tight anti-culmination / transit paran derived from Horizons event times.",
    },
    {
        "id": "moon-venus-new-york-mixed",
        "location": {"label": "New York City, USA", "latitude_deg": 40.7128, "longitude_deg": -74.006, "elevation_km": 0.0},
        "jd_start": 2460392.5,
        "orb_minutes": 6.0,
        "bodies": [
            {"body": "Moon", "command": "301"},
            {"body": "Venus", "command": "299"},
        ],
        "notes": "Mixed horizon paran with a modest orb.",
    },
    {
        "id": "sun-venus-tromso-none",
        "location": {"label": "Tromso, Norway", "latitude_deg": 69.6492, "longitude_deg": 18.9553, "elevation_km": 0.0},
        "jd_start": 2460482.5,
        "orb_minutes": 4.0,
        "bodies": [
            {"body": "Sun", "command": "10"},
            {"body": "Venus", "command": "299"},
        ],
        "notes": "High-latitude no-paran case within the configured orb.",
    },
]


def _derive_expected_parans(case: dict) -> list[dict]:
    lat = case["location"]["latitude_deg"]
    lon = case["location"]["longitude_deg"]
    elev = case["location"]["elevation_km"]
    jd_start = case["jd_start"]
    orb_minutes = case["orb_minutes"]
    orb_jd = orb_minutes / (24.0 * 60.0)

    by_body: dict[str, dict[str, float | None]] = {}
    for body_info in case["bodies"]:
        by_body[body_info["body"]] = observer_event_times(
            body_info["command"],
            jd_start,
            lat,
            lon,
            altitude_deg=-0.5667,
            elevation_km=elev,
        )

    expected: list[dict] = []
    body_list = [body_info["body"] for body_info in case["bodies"]]
    for i, body1 in enumerate(body_list):
        for body2 in body_list[i + 1:]:
            for event1, jd1 in by_body[body1].items():
                for event2, jd2 in by_body[body2].items():
                    if jd1 is None or jd2 is None:
                        continue
                    delta = abs(jd1 - jd2)
                    if delta <= orb_jd:
                        expected.append(
                            {
                                "body1": body1,
                                "body2": body2,
                                "circle1": _CIRCLE_NAME[event1],
                                "circle2": _CIRCLE_NAME[event2],
                                "jd1_ut": jd1,
                                "jd2_ut": jd2,
                                "jd_mid_ut": (jd1 + jd2) / 2.0,
                                "orb_minutes": delta * 24.0 * 60.0,
                            }
                        )
    expected.sort(key=lambda row: row["orb_minutes"])
    return expected


def main() -> int:
    payload = {
        "_comment": "Offline Horizons-derived paran reference cases. Expected paran matches are derived from external Horizons event times, not Moira's own paran matcher.",
        "_source": "Primary oracle: JPL Horizons observer tables via tests/tools/horizons.py. No network is required at test time.",
        "_default_threshold_seconds": 5.0,
        "cases": [],
    }

    for case in _CASES:
        payload["cases"].append(
            {
                "id": case["id"],
                "location": case["location"],
                "window": {
                    "jd_start": case["jd_start"],
                    "duration_hours": 24.0,
                    "semantics": "next 24h from jd_start",
                },
                "altitude_deg": -0.5667,
                "orb_minutes": case["orb_minutes"],
                "threshold_seconds": 5.0,
                "bodies": case["bodies"],
                "expected_parans": _derive_expected_parans(case),
                "notes": case["notes"],
            }
        )

    FIXTURE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {FIXTURE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
