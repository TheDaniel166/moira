"""Website-only city and timezone lookup routes.

These routes are transport conveniences for chart-entry UX. They do not define
astronomical or astrological truth, and they intentionally avoid request-time
network geocoding.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Query

from ..models.locations import (
    LocationMatchResponse,
    LocationSearchResponse,
    TimezoneLookupRequest,
    TimezoneLookupResponse,
)


router = APIRouter(prefix="/v1/locations", tags=["website-locations"])


_LOCATION_SOURCE = "moira_server.website_seed_gazetteer.v1"
_LOCATIONS: tuple[LocationMatchResponse, ...] = (
    LocationMatchResponse(
        name="New York",
        region="New York",
        country="United States",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        source=_LOCATION_SOURCE,
    ),
    LocationMatchResponse(
        name="Los Angeles",
        region="California",
        country="United States",
        latitude=34.0522,
        longitude=-118.2437,
        timezone="America/Los_Angeles",
        source=_LOCATION_SOURCE,
    ),
    LocationMatchResponse(
        name="Chicago",
        region="Illinois",
        country="United States",
        latitude=41.8781,
        longitude=-87.6298,
        timezone="America/Chicago",
        source=_LOCATION_SOURCE,
    ),
    LocationMatchResponse(
        name="London",
        region="England",
        country="United Kingdom",
        latitude=51.5074,
        longitude=-0.1278,
        timezone="Europe/London",
        source=_LOCATION_SOURCE,
    ),
    LocationMatchResponse(
        name="Paris",
        region="Ile-de-France",
        country="France",
        latitude=48.8566,
        longitude=2.3522,
        timezone="Europe/Paris",
        source=_LOCATION_SOURCE,
    ),
    LocationMatchResponse(
        name="Tokyo",
        region="Tokyo",
        country="Japan",
        latitude=35.6762,
        longitude=139.6503,
        timezone="Asia/Tokyo",
        source=_LOCATION_SOURCE,
    ),
    LocationMatchResponse(
        name="Delhi",
        region="Delhi",
        country="India",
        latitude=28.6139,
        longitude=77.2090,
        timezone="Asia/Kolkata",
        source=_LOCATION_SOURCE,
    ),
    LocationMatchResponse(
        name="Sydney",
        region="New South Wales",
        country="Australia",
        latitude=-33.8688,
        longitude=151.2093,
        timezone="Australia/Sydney",
        source=_LOCATION_SOURCE,
    ),
)
_SEEDED_TIMEZONES = frozenset(location.timezone for location in _LOCATIONS)


def _matches_query(location: LocationMatchResponse, query: str) -> bool:
    needle = query.casefold().strip()
    haystack = " ".join(
        part for part in (location.name, location.region, location.country, location.timezone) if part
    ).casefold()
    return needle in haystack


@router.get("/search", response_model=LocationSearchResponse)
def location_search_route(
    query: str = Query(min_length=1),
    limit: int = Query(default=8, ge=1, le=25),
) -> LocationSearchResponse:
    """Return bounded local city matches for website chart entry."""

    matches = [location for location in _LOCATIONS if _matches_query(location, query)]
    return LocationSearchResponse(query=query, matches=matches[:limit])


@router.post("/timezone/validate", response_model=TimezoneLookupResponse)
def timezone_validate_route(request: TimezoneLookupRequest) -> TimezoneLookupResponse:
    """Validate an IANA timezone identifier with the stdlib zoneinfo database."""

    if request.timezone in _SEEDED_TIMEZONES:
        return TimezoneLookupResponse(timezone=request.timezone, valid=True)

    try:
        ZoneInfo(request.timezone)
    except ZoneInfoNotFoundError:
        return TimezoneLookupResponse(timezone=request.timezone, valid=False)
    return TimezoneLookupResponse(timezone=request.timezone, valid=True)


__all__ = ["router"]
