from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

from moira.stars import star_at, star_name_resolves


CONSTELLATIONS_DIR = Path(__file__).resolve().parents[2] / "moira" / "constellations"
J2000 = 2451545.0


def _constellation_modules() -> list[object]:
    modules = []
    for modinfo in pkgutil.iter_modules([str(CONSTELLATIONS_DIR)]):
        if modinfo.name == "__init__":
            continue
        modules.append(importlib.import_module(f"moira.constellations.{modinfo.name}"))
    return modules


@pytest.mark.unit
@pytest.mark.parametrize("module", _constellation_modules(), ids=lambda module: module.__name__.split(".")[-1])
def test_constellation_star_mappings_resolve_sovereign_names(module: object) -> None:
    mapping = next(
        value
        for key, value in vars(module).items()
        if key.endswith("_STAR_NAMES") and isinstance(value, dict)
    )
    for advertised_name in mapping.values():
        assert star_name_resolves(advertised_name), (
            f"{module.__name__} advertises {advertised_name!r}, but the sovereign star engine "
            "does not resolve it."
        )
        star = star_at(advertised_name, J2000)
        assert star.name


@pytest.mark.unit
@pytest.mark.parametrize("module", _constellation_modules(), ids=lambda module: module.__name__.split(".")[-1])
def test_constellation_available_helpers_match_resolver_truth(module: object) -> None:
    mapping = next(
        value
        for key, value in vars(module).items()
        if key.endswith("_STAR_NAMES") and isinstance(value, dict)
    )
    available_fn = next(
        value
        for key, value in vars(module).items()
        if key.startswith("available_") and callable(value)
    )
    expected = [name for name in mapping.values() if star_name_resolves(name)]
    assert available_fn() == expected
