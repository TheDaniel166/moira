"""Additive API guards: live declarations, immutable compatibility floors.

These checks never generate or update a baseline from the running package.
An explicitly declared addition is allowed; missing historical names and
malformed, unbound, private, or inconsistent exports are not.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
import inspect
import keyword
from types import ModuleType


_METADATA_EXPORTS = frozenset({"__author__", "__version__"})


def compatibility_errors(
    required: Iterable[str], current: Iterable[str], label: str,
) -> list[str]:
    """Preserve the historical floor without rejecting additive declarations."""
    missing = sorted(set(required) - set(current))
    return [f"{label} removed compatibility names: {missing}"] if missing else []


def surface_contract_errors(
    surface: ModuleType,
    *,
    required: Iterable[str] = (),
    upstream: ModuleType | None = None,
) -> list[str]:
    """Validate current exports independently of any copied expected-name list."""
    declaration = getattr(surface, "__all__", None)
    label = surface.__name__
    if not isinstance(declaration, (list, tuple)):
        return [f"{label}.__all__ must be an ordered list or tuple of names"]

    errors: list[str] = []
    names: list[str] = []
    for name in declaration:
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
        ):
            errors.append(f"{label} declares an invalid export name: {name!r}")
        else:
            names.append(name)
            if name.startswith("_") and name not in _METADATA_EXPORTS:
                errors.append(f"{label} declares a private export: {name}")

    duplicates = sorted(
        name for name, count in Counter(names).items() if count > 1
    )
    if duplicates:
        errors.append(f"{label} declares duplicate exports: {duplicates}")
    errors.extend(compatibility_errors(required, names, label))

    for name in sorted(set(names)):
        if not hasattr(surface, name):
            errors.append(f"{label} declares an unbound export: {name}")
            continue
        value = getattr(surface, name)
        if isinstance(value, ModuleType):
            errors.append(f"{label} exports a module instead of a public symbol: {name}")
        if upstream is not None:
            if name not in upstream.__all__ or not hasattr(upstream, name):
                errors.append(f"{label}.{name} is not declared by {upstream.__name__}")
            elif value is not getattr(upstream, name):
                errors.append(f"{label}.{name} differs from {upstream.__name__}.{name}")
    return errors


def public_method_names(engine_type: type) -> frozenset[str]:
    """Discover public methods, including inherited, static, and class methods."""
    return frozenset(
        name for name, member in inspect.getmembers(engine_type)
        if not name.startswith("_")
        and (inspect.isfunction(member) or inspect.ismethod(member))
    )


def instance_method_errors(
    engine: object, *, required: Iterable[str] = (),
) -> list[str]:
    """Check every current method, not only methods in a historical inventory."""
    names = public_method_names(type(engine))
    errors = compatibility_errors(required, names, type(engine).__name__)
    for name in sorted(names):
        if not callable(getattr(engine, name, None)):
            errors.append(f"{type(engine).__name__} instance has a non-callable method: {name}")
    return errors
