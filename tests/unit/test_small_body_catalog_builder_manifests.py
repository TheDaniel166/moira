import json
from pathlib import Path

from scripts import build_comet_catalog
from scripts import build_unified_asteroid_catalog


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_asteroid_builder_declares_moira_artifact_provenance(tmp_path: Path) -> None:
    kernel_name = "asteroid_shard_000.bsp"
    (tmp_path / kernel_name).write_bytes(b"kernel")
    record = {"number": 1, "naif_id": 2_000_001, "name": "Ceres"}
    _write_json(
        tmp_path / "asteroid_shard_000.metadata.json",
        {
            "shard": 0,
            "kernel": kernel_name,
            "window": list(build_unified_asteroid_catalog.WINDOW),
            "step_days": build_unified_asteroid_catalog.STEP_DAYS,
            "window_size": build_unified_asteroid_catalog.WINDOW_SIZE,
            "records": [record],
            "failures": [],
        },
    )

    build_unified_asteroid_catalog._write_manifest(tmp_path, records=[record])

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_schema"] == "moira.small-body-catalog/v1"
    assert manifest["catalog_id"] == "moira-asteroids"
    assert manifest["provenance"] == {
        "artifact_author": "Moira",
        "artifact_format": "DAF/SPK Type 13",
        "trajectory_source": "JPL Horizons VECTORS",
        "horizons_api": build_unified_asteroid_catalog.HORIZONS_URL,
        "center": "Sun (500@10)",
        "reference_plane": "FRAME",
        "units": "km and km/s",
        "timescale": "JDTDB",
    }


def test_asteroid_builder_declares_horizons_range_clamps(tmp_path: Path) -> None:
    record = {
        "number": 101955,
        "naif_id": 2_101_955,
        "name": "Bennu",
        "clamped": True,
        "start": "1901-01-01",
        "stop": "2134-01-01",
    }

    build_unified_asteroid_catalog._write_manifest(tmp_path, records=[record])

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["coverage_exceptions"] == [
        {
            "naif_id": 2_101_955,
            "name": "Bennu",
            "start_date": "1901-01-01",
            "end_date": "2134-01-01",
            "policy": "jpl_horizons_ephemeris_availability",
            "authority": "JPL Horizons API",
            "note": (
                "conservative full-year bounds parsed from the Horizons "
                "ephemeris-availability response"
            ),
        }
    ]


def test_comet_builder_declares_moira_artifact_provenance(tmp_path: Path) -> None:
    kernel_name = "comet_shard_000.bsp"
    (tmp_path / kernel_name).write_bytes(b"kernel")
    _write_json(
        tmp_path / "comet_shard_000.metadata.json",
        {
            "shard": 0,
            "kernel": kernel_name,
            "records": [{"number": 1, "naif_id": 1_000_001, "name": "Halley"}],
            "failures": [],
        },
    )

    build_comet_catalog._write_manifest(tmp_path)

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_schema"] == "moira.small-body-catalog/v1"
    assert manifest["catalog_id"] == "moira-comets"
    assert manifest["provenance"] == build_comet_catalog._catalog_provenance()
