"""Exact geometric templates for longitude aspect patterns.

Owns immutable rational-turn layouts and harmonic template generation.
Delegates aspect identities and orbs to the canonical aspect registry. Detection
and result construction remain in ``moira.patterns``. Harmonic layouts are
geometric constructions, with no assigned psychological meaning. No I/O or
optional runtime dependencies are used.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, combinations_with_replacement
from math import lcm
from types import MappingProxyType
from typing import Mapping

from .aspect_registry import ASPECT_DEFINITIONS, resolve_aspect
from .optional_aspects import OPTIONAL_ASPECT_FRACTIONS, OPTIONAL_ASPECT_SETS

__all__ = [
    "GeometricPatternTemplate", "PatternGeometryTruth", "HARMONIC_PATTERN_PRESETS",
    "harmonic_pattern_templates", "triangle_template",
    "MATHEMATICAL_PATTERN_TEMPLATES",
]


def _exact_turn(value: object) -> Fraction:
    """Accept exact fractions, integer turns, or integer numerator/denominator pairs."""
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if (isinstance(value, tuple) and len(value) == 2
            and all(type(part) is int for part in value) and value[1] > 0):
        return Fraction(*value)
    raise ValueError("Template phases must be exact fractions with positive denominators")


def _aspect_turn(name: str) -> Fraction:
    """Recover the catalog's rational identity, retaining explicit optional fractions."""
    definition = resolve_aspect(name)
    if definition.name in OPTIONAL_ASPECT_FRACTIONS:
        return Fraction(*OPTIONAL_ASPECT_FRACTIONS[definition.name])
    turn = Fraction(definition.angle / 360).limit_denominator(360)
    if abs(float(turn * 360) - definition.angle) > 1e-10:
        raise ValueError("Aspect has no admitted exact rational-turn identity")
    return turn


def _rotations(values: tuple[Fraction, ...]) -> tuple[tuple[Fraction, ...], ...]:
    """Return cyclic rotations of an exact gap sequence."""
    return tuple(values[i:] + values[:i] for i in range(len(values)))


@dataclass(frozen=True, slots=True)
class GeometricPatternTemplate:
    """A closed layout of distinct vertices, in increasing exact fractions of a turn.

    The first phase is zero. Every vertex pair is a required edge; impossible
    edge bags therefore cannot be authored. Apex is an optional vertex index.
    Source labels identify doctrine versus a neutral mathematical construction.
    """

    name: str
    phases: tuple[Fraction, ...]
    apex_index: int | None = None
    source: str = "exact rational-turn geometry"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or self.name != self.name.strip():
            raise ValueError("Template name must be a non-empty trimmed string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Template source must be a non-empty string")
        if not isinstance(self.phases, tuple) or not 3 <= len(self.phases) <= 40:
            raise ValueError("Templates require a tuple of 3 to 40 distinct phases")
        phases = tuple(_exact_turn(value) for value in self.phases)
        if (phases[0] != 0 or phases[-1] >= 1 or tuple(sorted(set(phases))) != phases):
            raise ValueError("Template phases must increase strictly from zero to below one turn")
        if self.apex_index is not None and (
            type(self.apex_index) is not int or not 0 <= self.apex_index < len(phases)
        ):
            raise ValueError("Template apex_index must identify a vertex")
        object.__setattr__(self, "phases", phases)

    @property
    def edges(self) -> tuple[tuple[int, int, Fraction], ...]:
        """All unordered vertex pairs and their exact minor separations."""
        return tuple((i, j, min(self.phases[j] - self.phases[i],
                               1 - self.phases[j] + self.phases[i]))
                     for i, j in combinations(range(len(self.phases)), 2))

    @property
    def harmonic(self) -> int:
        """The smallest integer grid containing the declared phases."""
        return lcm(*(phase.denominator for phase in self.phases))

    @property
    def geometry_key(self) -> tuple[Fraction, ...]:
        """Unlabelled layout identity modulo rotation and reflection."""
        gaps = tuple(b - a for a, b in zip(self.phases, self.phases[1:] + (Fraction(1),)))
        return min(_rotations(gaps) + _rotations(tuple(reversed(gaps))))

    @property
    def reflection_symmetric(self) -> bool:
        """Whether a reflection preserves the unlabelled ideal layout."""
        gaps = tuple(b - a for a, b in zip(self.phases, self.phases[1:] + (Fraction(1),)))
        return tuple(reversed(gaps)) in _rotations(gaps)

    @property
    def required_optional_sets(self) -> tuple[str, ...]:
        """Catalog sets required by this layout, without enabling them implicitly."""
        turns = {turn for _, _, turn in self.edges}
        return tuple(key for key, members in OPTIONAL_ASPECT_SETS.items()
                     if any(Fraction(member.numerator, member.denominator) in turns
                            for member in members))


@dataclass(frozen=True, slots=True)
class PatternGeometryTruth:
    """Preserved exact template, vertex assignment, and observed orientation.

    Forward/reflected refer to the template's increasing-longitude ordering,
    never to planetary retrograde motion or an interpretive quality rating.
    Orientation is unavailable without positions, or ambiguous at broad orbs.
    """

    template: GeometricPatternTemplate
    vertex_bodies: tuple[str, ...]
    orientation: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.template, GeometricPatternTemplate):
            raise ValueError("Geometry truth requires a geometric template")
        if (not isinstance(self.vertex_bodies, tuple)
                or len(self.vertex_bodies) != len(self.template.phases)
                or len(set(self.vertex_bodies)) != len(self.vertex_bodies)
                or any(not isinstance(body, str) or not body.strip() for body in self.vertex_bodies)):
            raise ValueError("Geometry truth must assign each vertex to a distinct body")
        if self.orientation not in {None, "forward", "reflected", "symmetric", "ambiguous"}:
            raise ValueError("Unsupported geometric orientation")


_MATHEMATICAL_LAYOUTS = {
    "H13 Spectrum A": (13, (0, 1, 3, 9), "perfect (13,4,1) cyclic difference set"),
    "H13 Spectrum B": (13, (0, 2, 5, 6), "perfect (13,4,1) cyclic difference set"),
    "H11 Balanced Spectrum": (
        11, (0, 2, 3, 4, 8),
        "cyclic (11,5,2) difference set; Amiot and Sethares (2009), section 4.3; "
        "https://sethares.engr.wisc.edu/paperspdf/AlgofScales.pdf",
    ),
    "Interval Prism A": (
        12, (0, 1, 4, 6),
        "homometric interval pair; Amiot and Sethares (2009), Example 9; "
        "https://sethares.engr.wisc.edu/paperspdf/AlgofScales.pdf",
    ),
    "Interval Prism B": (
        12, (0, 1, 3, 7),
        "homometric interval pair; Amiot and Sethares (2009), Example 9; "
        "https://sethares.engr.wisc.edu/paperspdf/AlgofScales.pdf",
    ),
    "Fibonacci Fan": (12, (0, 1, 2, 4, 7), "cyclic gap sequence 1,1,2,3,5"),
    "Fibonacci Crown": (20, (0, 1, 2, 4, 7, 12), "cyclic gap sequence 1,1,2,3,5,8"),
    "Triadic Braid": (15, (0, 1, 5, 6, 10, 11), "two regular triangles offset by 1/15 turn"),
    "Split Cross": (16, (0, 1, 4, 5, 8, 9, 12, 13), "two squares offset by 1/16 turn"),
    "Harmonic Bridge": (30, (0, 2, 5), "closed 2/30,3/30,5/30 mixed-harmonic triangle"),
}

MATHEMATICAL_PATTERN_TEMPLATES: Mapping[str, GeometricPatternTemplate] = MappingProxyType({
    name: GeometricPatternTemplate(
        name, tuple(Fraction(step, denominator) for step in steps),
        source=f"Moira mathematical construction (2026-10-26); {basis}",
    )
    for name, (denominator, steps, basis) in _MATHEMATICAL_LAYOUTS.items()
})

_MATHEMATICAL_PATTERN_ALIASES: Mapping[str, str] = MappingProxyType({
    "H13 Perfect Spectrum A": "H13 Spectrum A",
    "H13 Perfect Spectrum B": "H13 Spectrum B",
    "Undecile Balanced Spectrum": "H11 Balanced Spectrum",
    "Prism A": "Interval Prism A", "Prism B": "Interval Prism B",
    "Fibonacci Gap Fan": "Fibonacci Fan", "Fibonacci Gap Crown": "Fibonacci Crown",
    "Quindecile-Trine Braid": "Triadic Braid",
    "Hexadecile Split Cross": "Split Cross", "H30 Bridge": "Harmonic Bridge",
})


HARMONIC_PATTERN_PRESETS: Mapping[str, int] = MappingProxyType({
    f"H{h}": h for h in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24, 32, 36, 40)
})
_CATALOG_TURNS = frozenset(_aspect_turn(definition.name) for definition in ASPECT_DEFINITIONS)


def triangle_template(name: str, aspects: tuple[str, str, str]) -> GeometricPatternTemplate:
    """Construct a triangle from three catalog names or aliases; reject non-closing triples.

    Aspect aliases retain their registry meanings: Quindecile is 24 degrees
    and Tao is 165 degrees. Optional aspect selection is enforced at detection.
    """
    if not isinstance(aspects, tuple) or len(aspects) != 3:
        raise ValueError("A triangle requires three aspect names")
    a, b, c = sorted(_aspect_turn(name) for name in aspects)
    if a <= 0:
        raise ValueError("A geometric triangle requires distinct vertices")
    if a + b == c:
        phases = (Fraction(0), a, c)
    elif a + b + c == 1:
        phases = (Fraction(0), a, a + b)
    else:
        raise ValueError("Aspect triple cannot close on a longitude circle")
    return GeometricPatternTemplate(name, phases)


def harmonic_pattern_templates(
    harmonic: int,
    shapes: tuple[str, ...] = ("triangle",),
) -> tuple[GeometricPatternTemplate, ...]:
    """Generate distinct exact triangles, opposition rectangles, or a regular polygon.

    Only supported harmonic grids are admitted. Reducible layouts receive their
    primitive grid name, and duplicate geometry is collapsed. Rectangles whose
    complementary angles are absent from the complete catalog are excluded.
    H13/H32/H36/H40 templates still require explicit optional sets at detection.
    No additional named tradition or interpretation is inferred.
    """
    if type(harmonic) is not int or harmonic not in HARMONIC_PATTERN_PRESETS.values():
        raise ValueError("Unsupported harmonic pattern preset")
    supported = {"triangle", "opposition_rectangle", "polygon"}
    if (not isinstance(shapes, tuple) or not shapes or len(set(shapes)) != len(shapes)
            or any(shape not in supported for shape in shapes)):
        raise ValueError("shapes must select triangle, opposition_rectangle, or polygon uniquely")
    templates: dict[tuple[Fraction, ...], GeometricPatternTemplate] = {}
    if "triangle" in shapes:
        for a, b, c in combinations_with_replacement(range(1, harmonic // 2 + 1), 3):
            if a + b == c:
                phases = (Fraction(0), Fraction(a, harmonic), Fraction(c, harmonic))
            elif a + b + c == harmonic:
                phases = (Fraction(0), Fraction(a, harmonic), Fraction(a + b, harmonic))
            else:
                continue
            template = GeometricPatternTemplate("triangle", phases)
            h = template.harmonic
            separations = sorted(turn for _, _, turn in template.edges)
            label = "-".join(str(int(turn * h)) for turn in separations)
            template = GeometricPatternTemplate(f"H{h} Triangle {label}", phases)
            templates.setdefault(template.geometry_key, template)
    if "opposition_rectangle" in shapes:
        for k in range(1, harmonic // 2 + 1):
            phase = Fraction(k, harmonic)
            a = min(phase, Fraction(1, 2) - phase)
            if a == 0:
                continue
            phases = (Fraction(0), a, Fraction(1, 2), Fraction(1, 2) + a)
            template = GeometricPatternTemplate(f"Rectangle {a}", phases)
            if all(turn in _CATALOG_TURNS for _, _, turn in template.edges):
                templates.setdefault(template.geometry_key, template)
    if "polygon" in shapes:
        template = GeometricPatternTemplate(
            f"H{harmonic} Polygon", tuple(Fraction(k, harmonic) for k in range(harmonic)),
        )
        templates.setdefault(template.geometry_key, template)
    return tuple(sorted(templates.values(), key=lambda item: item.name))
