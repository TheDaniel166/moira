from __future__ import annotations

from datetime import datetime, timezone

import moira
import moira.facade as facade


_PUBLIC_NAMES = [
    "GalacticAngles",
    "GalacticHouseCusps",
    "GalacticHousePlacement",
    "GalacticHouseBoundaryProfile",
    "calculate_galactic_houses",
    "assign_galactic_house",
    "body_galactic_house_position",
    "describe_galactic_boundary",
]


def test_galactic_house_public_names_resolve_from_facade() -> None:
    for name in _PUBLIC_NAMES:
        assert hasattr(facade, name), f"moira.facade.{name} not found"
        assert name in facade.__all__, f"{name} missing from moira.facade.__all__"


def test_galactic_house_public_names_resolve_from_package_root() -> None:
    for name in _PUBLIC_NAMES:
        assert hasattr(moira, name), f"moira.{name} not found"
        assert name in moira.__all__, f"{name} missing from moira.__all__"


def test_moira_galactic_houses_matches_module_entry_point() -> None:
    api = facade.Moira()
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    via_method = api.galactic_houses(dt, 51.5, 0.0)
    via_function = facade.calculate_galactic_houses(
        facade.jd_from_datetime(dt),
        51.5,
        0.0,
    )

    assert via_method == via_function
