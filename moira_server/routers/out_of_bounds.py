"""Out-of-bounds declination route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.out_of_bounds import (
    OutOfBoundsSearchRequest,
    OutOfBoundsSearchResponse,
)
from ..serializers.out_of_bounds import serialize_out_of_bounds_report
from ..services.out_of_bounds import compute_out_of_bounds


router = APIRouter(prefix="/v1", tags=["predictive"])


@router.post("/out-of-bounds/search", response_model=OutOfBoundsSearchResponse)
def out_of_bounds_search_route(
    request: OutOfBoundsSearchRequest,
    engine: Moira = Depends(get_engine),
) -> OutOfBoundsSearchResponse:
    """Every out-of-bounds declination excursion of one body in a range.

    A body is out of bounds when the magnitude of its geocentric apparent
    declination exceeds the true obliquity of date. Both terms move, so each
    entry and return is solved as a root of ``|declination| - obliquity``, and
    the extremal declination inside each excursion is solved as a root of the
    declination rate rather than read off a scan grid.

    Each crossing carries its declination rate, the rate of the bound function
    itself, the solver's achieved tolerance, and the time cost of one
    arcsecond of declination error. That cost is not incidental: measured
    against this engine it ranges from about six seconds per arcsecond for a
    lunar crossing to over an hour for a Plutonian one, so an instant printed
    to the minute means very different things for different bodies.

    Window edges are explicit rather than silently truncated. A body already
    out of bounds at ``jd_start`` reports ``entry_clipped``, one still out at
    ``jd_end`` reports ``departure_clipped``, and in either case
    ``duration_is_lower_bound`` marks the duration as 'at least this long'.

    Planets, asteroids and comets are all admitted, and the scan
    cadence is derived from the body's own measured motion rather than from a
    per-body table, so a fast minor body is not scanned at a planetary step.
    A body whose ephemeris does not cover the requested range returns an
    explicit unavailable, never an empty list.
    """
    return serialize_out_of_bounds_report(compute_out_of_bounds(engine, request))
