from __future__ import annotations

from moira.download_kernels import _REGISTRY, list_kernels
from moira._wheel_asteroid_catalog import CATALOG_ID, CATALOG_VERSION


def test_registry_does_not_offer_centaurs_or_minor_bodies() -> None:
    names = {entry["filename"] for entry in _REGISTRY}
    assert "centaurs.bsp" not in names
    assert "minor_bodies.bsp" not in names


def test_jpl_small_body_entries_do_not_claim_chiron(capsys) -> None:
    asteroids = next(entry for entry in _REGISTRY if entry["filename"] == "asteroids.bsp")
    sb441 = next(entry for entry in _REGISTRY if entry["filename"] == "sb441-n373s.bsp")
    for entry in (asteroids, sb441):
        blob = f"{entry['description']} {entry.get('filename', '')}".lower()
        assert "do not install chiron" in blob or "does not install chiron" in blob
        assert "not a substitute" in blob


def test_list_kernels_reports_wheel_catalog_and_omits_ghost_bundled(capsys) -> None:
    list_kernels()
    text = capsys.readouterr().out
    assert CATALOG_ID in text
    assert CATALOG_VERSION in text
    assert "OK (wheel)" in text
    assert "centaurs.bsp" not in text
    assert "minor_bodies.bsp" not in text
