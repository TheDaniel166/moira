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


def test_registry_pins_lunar_orientation_resource_identities() -> None:
    entries = {entry["filename"]: entry for entry in _REGISTRY}
    pck = entries["moon_pa_de440_200625.bpc"]
    frame = entries["moon_de440_250416.tf"]

    assert pck["byte_length"] == 12_863_488
    assert pck["sha256"] == "60cd55aa401ea2ea97360636f567554bfe4e37bb829f901b4460a455dfaf783f"
    assert frame["byte_length"] == 19_478
    assert frame["sha256"] == "a47c71e9c9f33796bdafb2c9d69a7ee447b6016ecad80f71cd6f3e479f9cf768"


def test_lunar_orientation_selector_contains_only_the_pinned_pair() -> None:
    from moira.download_kernels import _LUNAR_ORIENTATION_FILENAMES

    assert _LUNAR_ORIENTATION_FILENAMES == {
        "moon_pa_de440_200625.bpc",
        "moon_de440_250416.tf",
    }


def test_list_kernels_reports_wheel_catalog_and_omits_ghost_bundled(capsys) -> None:
    list_kernels()
    text = capsys.readouterr().out
    assert CATALOG_ID in text
    assert CATALOG_VERSION in text
    assert "OK (wheel)" in text
    assert "centaurs.bsp" not in text
    assert "minor_bodies.bsp" not in text
