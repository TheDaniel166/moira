"""Service helpers for the out-of-bounds declination endpoint.

Transport validation and policy assembly only. The search itself belongs to
``moira.out_of_bounds.find_out_of_bounds`` through the ``Moira`` facade; no
doctrine lives here.
"""

from __future__ import annotations

import math

from moira import Body, Moira
from moira.out_of_bounds import OutOfBoundsPolicy
from moira.small_body_identity import resolve_small_body_identity

from ..models.out_of_bounds import OutOfBoundsSearchRequest


#: Ceiling this route imposes on one search. Cost is linear in the requested
#: span — roughly 3,800 declination evaluations per year of lunar scan, or
#: about 2.4 seconds — so an unbounded span would be an unbounded request. At
#: this ceiling a worst-case lunar search runs about a minute, and every other
#: body is far cheaper per year. The engine itself defaults to no ceiling,
#: because a library caller may legitimately scan centuries.
_MAX_DECLINATION_EVALUATIONS = 100_000

_VALID_PLANETARY_BODIES = frozenset(Body.ALL_PLANETS)

#: Points Moira models as longitude-only, which therefore have no declination
#: and no out-of-bounds product. Refused here with a reason rather than left to
#: fail deeper, and named separately from an unknown body because they are
#: known bodies that this product does not cover.
_LONGITUDE_ONLY_POINTS = frozenset(
    {Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH, Body.TRUE_LILITH}
)


def _require_supported_body(body: str) -> None:
    """Admit planets and catalogued small bodies.

    Small-body admission is delegated to the shared identity registry rather
    than re-listed here, so an unqualified name that collides across the
    asteroid and comet catalogs raises the registry's own ambiguity error
    instead of being silently resolved to one family.

    The lunar nodes and apogees are refused with their own reason: they are
    known bodies, but Moira models them as longitude-only, so no declination
    exists to compare against the obliquity.
    """

    if not isinstance(body, str) or not body.strip():
        raise ValueError("body must be a non-empty string")
    stripped = body.strip()
    if stripped in _VALID_PLANETARY_BODIES:
        return
    if stripped in _LONGITUDE_ONLY_POINTS:
        raise ValueError(
            f"out-of-bounds is undefined for {body!r}: Moira models the lunar "
            "nodes and apogees as longitude-only points, so they have no "
            "declination. A node also lies on the ecliptic by construction, so "
            "its declination magnitude could never exceed the obliquity."
        )
    if resolve_small_body_identity(stripped) is not None:
        return
    supported = ", ".join(sorted(_VALID_PLANETARY_BODIES))
    raise ValueError(
        f"unsupported out-of-bounds body {body!r}; supported bodies: "
        f"{supported}, plus globally unique or family-qualified "
        "asteroid/comet names"
    )


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_positive(value: float, name: str) -> None:
    _require_finite(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be > 0")


def _validate_window(jd_start: float, jd_end: float) -> None:
    _require_finite(jd_start, "jd_start")
    _require_finite(jd_end, "jd_end")
    if jd_end <= jd_start:
        raise ValueError("jd_end must be > jd_start")


def _build_policy(request: OutOfBoundsSearchRequest) -> OutOfBoundsPolicy:
    """Assemble the explicit policy this route applies.

    A policy is always built, because this route always imposes an evaluation
    ceiling even when the caller supplies no controls. Search cost is linear in
    the requested span, so an unbounded span behind a request would be an
    unbounded search.
    """

    overrides: dict[str, float | int] = {
        "max_declination_evaluations": _MAX_DECLINATION_EVALUATIONS,
    }
    if request.angular_resolution_deg is not None:
        _require_positive(request.angular_resolution_deg, "angular_resolution_deg")
        overrides["angular_resolution_deg"] = request.angular_resolution_deg
    if request.max_step_days is not None:
        _require_positive(request.max_step_days, "max_step_days")
        overrides["max_step_days"] = request.max_step_days
    if request.solver_tolerance_days is not None:
        _require_positive(request.solver_tolerance_days, "solver_tolerance_days")
        overrides["solver_tolerance_days"] = request.solver_tolerance_days
    if request.max_declination_evaluations is not None:
        if request.max_declination_evaluations < 1:
            raise ValueError("max_declination_evaluations must be >= 1")
        if request.max_declination_evaluations > _MAX_DECLINATION_EVALUATIONS:
            raise ValueError(
                "max_declination_evaluations must be <= "
                f"{_MAX_DECLINATION_EVALUATIONS}"
            )
        overrides["max_declination_evaluations"] = (
            request.max_declination_evaluations
        )
    return OutOfBoundsPolicy(**overrides)


def compute_out_of_bounds(engine: Moira, request: OutOfBoundsSearchRequest):
    """Run one out-of-bounds search for the transport layer.

    Neither ``OutOfBoundsUnavailableError`` nor ``OutOfBoundsBudgetError`` is
    caught here: an uncovered ephemeris range must reach the caller as an
    explicit unavailable, and an exhausted budget as an explicit budget
    failure. Never as an empty or truncated excursion list.
    """

    _require_supported_body(request.body)
    _validate_window(request.jd_start, request.jd_end)
    return engine.out_of_bounds(
        request.body,
        request.jd_start,
        request.jd_end,
        policy=_build_policy(request),
    )


__all__ = ["compute_out_of_bounds"]
