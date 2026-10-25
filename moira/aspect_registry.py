"""Canonical longitude-aspect names and explicit, immutable spelling aliases.

Standard geometry remains owned by moira.constants; optional exact-fraction
sets are owned by moira.optional_aspects. Resolution ignores case, ASCII
spaces, hyphens, and underscores; it never infers an angle from a name or
adds a second definition. Unknown names raise ValueError. Quindecile always
means 24 degrees; the explicitly qualified 165-degree convention resolves
to Tao. Naming sources and exclusions are collated in
wiki/02_standards/ASPECT_BACKEND_STANDARD.md.
"""

from types import MappingProxyType
from typing import Mapping

from .constants import Aspect, AspectDefinition
from .optional_aspects import OPTIONAL_ASPECT_SETS, _optional_definitions

__all__ = ["ASPECT_ALIASES", "ASPECT_DEFINITIONS", "resolve_aspect"]

ASPECT_DEFINITIONS: tuple[AspectDefinition, ...] = (
    tuple(Aspect.ALL) + _optional_definitions(tuple(OPTIONAL_ASPECT_SETS))
)


_ALIASES = {
    "Inconjunct": "Quincunx",
    "Octile": "Semisquare",
    "Sesquisquare": "Sesquiquadrate",
    "Trioctile": "Sesquiquadrate",
    "Semiquintile": "Decile",
    "Tridecile": "Tredecile",
    "Sesquiquintile": "Tredecile",
    "Nonile": "Novile",
    "Binonile": "Binovile",
    "Quadranovile": "Quadnovile",
    "Quatronovile": "Quadnovile",
    "Duodecile": "Semisextile",
    "Semioctile": "Hexadecile",
    "Sexdecile": "Hexadecile",
    "Quartisquare": "Hexadecile",
    "Semidecile": "Vigintile",
    "Semiduodecile": "Untion",
    "Quartisextile": "Untion",
    "Quartosextile": "Untion",
    "Quattuorvigintile": "Untion",
    "Trientquintile": "Quindecile",
    "Quindecile (24°)": "Quindecile",
    "Quindecile (165°)": "Tao",
    "Quindecile (Tyl)": "Tao",
    "Contraquindecile": "Tao",
    "Undecaquartisextile": "Tao",
    "QuatroUndecile": "Quadriundecile",
    "Quadundecile": "Quadriundecile",
    "Quadraundecile": "Quadriundecile",
    "QuintUndecile": "Quinqueundecile",
    "Quinundecile": "Quinqueundecile",
    "Quintaundecile": "Quinqueundecile",
    "Quadriquindecile": "Quadraquindecile",
    "Sepquindecile": "Septaquindecile",
    "Septquindecile": "Septaquindecile",
    "Triquartisquare": "Sesquioctile",
    "Quintaquartisquare": "Quinsemioctile",
    "Septaquartisquare": "Septsemioctile",
    "Sepsemioctile": "Septsemioctile",
    "Quintaseminovile": "Quinseminovile",
    "Septaseminovile": "Septseminovile",
    "Septavigintile": "Septvigintile",
    "Novigintile": "Nonavigintile",
    "Tresemiseptile": "Trisemiseptile",
    "Sesquiseptile": "Trisemiseptile",
    "Quintasemiseptile": "Quinsemiseptile",
}
_PUBLISHED_OPTIONAL_ALIASES = {
    13: ("Tredecile", "Bitredecile", "Tritredecile", "Quadratredecile", "Quintatredecile", "Sextatredecile"),
    32: ("Quartisemisquare", "Triquartisemisquare", "Quintaquartisemisquare", "Septaquartisemisquare",
         "Nonaquartisemisquare", "Undecaquartisemisquare", "Tredecaquartisemisquare", "Quindecaquartisemisquare"),
    36: ("Sextisextile", "Quintasextisextile", "Septasextisextile", "Undecasextisextile",
         "Tredecasextisextile", "Septendecasextisextile"),
}
for _set, _members in OPTIONAL_ASPECT_SETS.items():
    for _index, _member in enumerate(_members):
        _name = _member.definition.name
        _ALIASES[f"{_member.numerator}/{_member.denominator}"] = _name
        if _member.denominator in _PUBLISHED_OPTIONAL_ALIASES:
            _published = _PUBLISHED_OPTIONAL_ALIASES[_member.denominator][_index]
            # The existing unqualified Tredecile remains the 108-degree aspect.
            _alias = f"{_published} (13th harmonic)" if _member.denominator == 13 else _published
            _ALIASES[_alias] = _name
_ALIASES.update({"Semivigintile": "H40 1/40", "Quadragintile": "H40 1/40",
                 "Trigintasextile": "H36 1/36"})
ASPECT_ALIASES: Mapping[str, str] = MappingProxyType(_ALIASES)


def _name_key(name: str) -> str:
    return name.casefold().replace(" ", "").replace("-", "").replace("_", "")


_DEFINITIONS = {definition.name: definition for definition in ASPECT_DEFINITIONS}
_NAMES = {_name_key(name): name for name in _DEFINITIONS}
for _alias, _canonical in ASPECT_ALIASES.items():
    _key = _name_key(_alias)
    if _canonical not in _DEFINITIONS or _NAMES.get(_key, _canonical) != _canonical:
        raise ValueError(f"conflicting longitude aspect alias {_alias!r}")
    _NAMES[_key] = _canonical


def resolve_aspect(name: str) -> AspectDefinition:
    """Resolve a canonical name or declared alias to its unique definition.

    Whitespace outside a name is rejected; only the documented internal
    separator and case normalization is applied. Numeric angles, guessed
    abbreviations, and declination names are not admitted by this registry.
    """
    if not isinstance(name, str) or not name or name != name.strip():
        raise ValueError("aspect must name one canonical longitude aspect or declared alias")
    canonical = _NAMES.get(_name_key(name))
    if canonical is None:
        raise ValueError(f"unknown canonical longitude aspect {name!r}")
    return _DEFINITIONS[canonical]
