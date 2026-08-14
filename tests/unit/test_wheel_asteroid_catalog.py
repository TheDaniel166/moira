from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from moira._wheel_asteroid_catalog import (
    CATALOG_DIR,
    CATALOG_ID,
    CATALOG_VERSION,
    TARGETS_PATH,
    load_targets,
)

LOCKED = [
    (1, "Ceres", 2000001),
    (2, "Pallas", 2000002),
    (3, "Juno", 2000003),
    (4, "Vesta", 2000004),
    (5, "Astraea", 2000005),
    (7, "Iris", 2000007),
    (10, "Hygiea", 2000010),
    (16, "Psyche", 2000016),
    (433, "Eros", 2000433),
    (1181, "Lilith", 2001181),
    (1221, "Amor", 2001221),
    (2060, "Chiron", 2002060),
    (5145, "Pholus", 2005145),
    (7066, "Nessus", 2007066),
    (8405, "Asbolus", 2008405),
    (10199, "Chariklo", 2010199),
    (10370, "Hylonome", 2010370),
    (20000, "Varuna", 2020000),
    (28978, "Ixion", 2028978),
    (50000, "Quaoar", 2050000),
    (90377, "Sedna", 2090377),
    (90482, "Orcus", 2090482),
    (136108, "Haumea", 2136108),
    (136199, "Eris", 2136199),
    (136472, "Makemake", 2136472),
]


def test_locked_roster_is_exactly_twenty_five_naif_ordered_bodies() -> None:
    rows = load_targets()
    assert CATALOG_ID == "moira-asteroids-wheel"
    assert CATALOG_VERSION == "2026.08.14.1"
    assert TARGETS_PATH == CATALOG_DIR / "targets.json"
    assert [(row["number"], row["name"], row["naif_id"]) for row in rows] == LOCKED
    assert [row["naif_id"] for row in rows] == sorted(row["naif_id"] for row in rows)
    assert "Hidalgo" not in {row["name"] for row in rows}


def _load_builder():
    path = Path(__file__).resolve().parents[2] / "scripts" / "build_wheel_asteroid_catalog.py"
    spec = importlib.util.spec_from_file_location("build_wheel_asteroid_catalog", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builder_rejects_horizons_name_mismatch(tmp_path: Path, monkeypatch) -> None:
    builder = _load_builder()

    def fake_fetch(number: int) -> dict:
        return {
            "number": number,
            "naif_id": 2_000_000 + number,
            "name": "NotCeres" if number == 1 else f"Body{number}",
            "center": 10,
            "frame": 1,
            "states": [[0.0], [0.0], [0.0], [0.0], [0.0], [0.0]],
            "epochs_jd": [2451545.0],
            "window_size": 7,
            "clamped": False,
            "start": "1600-01-01",
            "stop": "2500-01-01",
        }

    monkeypatch.setattr(builder, "_fetch_body", fake_fetch)
    with pytest.raises(RuntimeError, match="Ceres"):
        builder.build_pre_release(tmp_path)


def test_builder_refuses_to_write_when_a_body_fails(tmp_path: Path, monkeypatch) -> None:
    builder = _load_builder()

    def fake_fetch(number: int) -> dict:
        if number == 2060:
            raise RuntimeError("horizons down")
        return {
            "number": number,
            "naif_id": 2_000_000 + number,
            "name": next(
                row["name"]
                for row in __import__(
                    "moira._wheel_asteroid_catalog", fromlist=["load_targets"]
                ).load_targets()
                if row["number"] == number
            ),
            "center": 10,
            "frame": 1,
            "states": [[0.0], [0.0], [0.0], [0.0], [0.0], [0.0]],
            "epochs_jd": [2451545.0],
            "window_size": 7,
            "clamped": False,
            "start": "1600-01-01",
            "stop": "2500-01-01",
        }

    monkeypatch.setattr(builder, "_fetch_body", fake_fetch)
    with pytest.raises(RuntimeError, match="2060"):
        builder.build_pre_release(tmp_path)
    assert not (tmp_path / "asteroid_shard_000.bsp").exists()
    assert CATALOG_ID == "moira-asteroids-wheel"
