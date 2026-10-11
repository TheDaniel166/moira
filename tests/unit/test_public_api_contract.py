"""Adversarial self-tests for additive public API hardening."""

from __future__ import annotations

from types import ModuleType

import pytest

from tests.tools.public_api_contract import (
    compatibility_errors,
    instance_method_errors,
    public_method_names,
    surface_contract_errors,
)


def _surface(**symbols: object) -> ModuleType:
    surface = ModuleType("contract_probe")
    surface.__all__ = list(symbols)
    vars(surface).update(symbols)
    return surface


def test_explicit_additive_exports_do_not_require_baseline_updates() -> None:
    surface = _surface(existing=object(), added=object())
    assert surface_contract_errors(surface, required={"existing"}) == []
    assert compatibility_errors({"existing"}, surface.__all__, "probe") == []


def test_historical_export_removal_still_fails() -> None:
    errors = surface_contract_errors(_surface(added=object()), required={"existing"})
    assert any("removed compatibility names" in error for error in errors)


@pytest.mark.parametrize("invalid", [None, 42, [], "two words", "class", ""])
def test_invalid_export_declarations_still_fail(invalid: object) -> None:
    surface = _surface(existing=object())
    surface.__all__.append(invalid)
    assert any("invalid export name" in error for error in surface_contract_errors(surface))


@pytest.mark.parametrize("declaration", [None, "existing", {"existing"}])
def test_unordered_or_nonsequence_declaration_fails(declaration: object) -> None:
    surface = _surface(existing=object())
    surface.__all__ = declaration
    assert surface_contract_errors(surface)


def test_duplicate_export_still_fails() -> None:
    surface = _surface(existing=object())
    surface.__all__.append("existing")
    assert any("duplicate exports" in error for error in surface_contract_errors(surface))


def test_unbound_new_export_still_fails() -> None:
    surface = _surface(existing=object())
    surface.__all__.append("added")
    assert any("unbound export: added" in error for error in surface_contract_errors(surface))


def test_private_helper_export_still_fails() -> None:
    errors = surface_contract_errors(_surface(_helper=object()))
    assert any("private export" in error for error in errors)


def test_existing_metadata_exports_remain_admitted() -> None:
    assert surface_contract_errors(_surface(__version__="1", __author__="author")) == []


def test_imported_module_leak_still_fails() -> None:
    errors = surface_contract_errors(_surface(helper=ModuleType("helper")))
    assert any("exports a module" in error for error in errors)


def test_upstream_identity_is_checked_for_additions_too() -> None:
    existing, added = object(), object()
    canonical = _surface(existing=existing, added=added)
    surface = _surface(existing=existing, added=added)
    assert surface_contract_errors(surface, upstream=canonical) == []
    surface.added = object()
    errors = surface_contract_errors(surface, upstream=canonical)
    assert any("differs from" in error for error in errors)


def test_export_missing_from_canonical_layer_still_fails() -> None:
    surface = _surface(added=object())
    errors = surface_contract_errors(surface, upstream=_surface())
    assert any("not declared by" in error for error in errors)


class _Engine:
    def existing(self) -> None:
        pass


class _ExtendedEngine(_Engine):
    def added(self) -> None:
        pass

    @staticmethod
    def static_added() -> None:
        pass

    @classmethod
    def class_added(cls) -> None:
        pass


def test_additive_inherited_static_and_class_methods_are_discovered() -> None:
    assert public_method_names(_ExtendedEngine) == {
        "existing", "added", "static_added", "class_added",
    }
    assert instance_method_errors(_ExtendedEngine(), required={"existing"}) == []


def test_removed_or_nonmethod_historical_member_still_fails() -> None:
    class Broken(_Engine):
        existing = None

    errors = instance_method_errors(Broken(), required={"existing"})
    assert any("removed compatibility names" in error for error in errors)


def test_instance_shadow_of_new_method_still_fails() -> None:
    engine = _ExtendedEngine()
    engine.added = None
    errors = instance_method_errors(engine, required={"existing"})
    assert any("non-callable method: added" in error for error in errors)
