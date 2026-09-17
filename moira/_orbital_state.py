"""Identity-bound, receipted ICRF states for Stage 1 orbital elements.

This module owns the one-call state boundary: resolve one admitted body and
center, bind UT1/TT/TDB and a content-derived planetary identity to one reader
snapshot, choose the pinned gravity rule, and return the exact routed state in
kilometres and kilometres per day.  Element extraction and frame policy remain
in :mod:`moira.orbits`.
"""

from __future__ import annotations

import difflib
import math
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Any

from ._ephemeris_gm import _OrbitalGravity, select_orbital_gravity
from ._ephemeris_time import (
    _BoundEphemerisTime,
    _EphemerisTimeBasisError,
    _bind_ephemeris_time,
)
from ._orbital_errors import (
    OrbitalAmbiguousBodyError,
    OrbitalBodyNotFoundError,
    OrbitalBodyNotLoadedError,
    OrbitalBodyNotSupportedError,
    OrbitalCenterNotAllowedError,
    OrbitalCoverageError,
    OrbitalInputError,
    OrbitalKernelMissingError,
    OrbitalSourceReceiptError,
    OrbitalTimeBasisError,
)
from .constants import Body
from .small_body_identity import (
    AmbiguousSmallBodyNameError,
    SmallBodyIdentity,
    resolve_small_body_identity,
)
from .spk_reader import KernelPool, OutOfRangeError, _RoutedState, get_active_reader


class OrbitalBodyKind(str, Enum):
    """Physical identity class used by the Stage 1 orbit surface."""

    PLANET_BODY = "PLANET_BODY"
    PLANET_SYSTEM_BARYCENTER = "PLANET_SYSTEM_BARYCENTER"
    EARTH_MOON_BARYCENTER = "EARTH_MOON_BARYCENTER"
    MOON = "MOON"
    ASTEROID = "ASTEROID"
    COMET = "COMET"


@dataclass(frozen=True, slots=True)
class OrbitalBodyIdentity:
    """One resolved orbital body with stable display and NAIF identity."""

    name: str
    kind: OrbitalBodyKind
    naif_id: int


@dataclass(frozen=True, slots=True)
class OrbitalStateLeg:
    """Path-free receipt for one exact SPK segment used by a state route."""

    center_naif_id: int
    target_naif_id: int
    traversal_sign: int
    segment_type: int
    coverage_start_tdb: float
    coverage_end_tdb: float
    kernel_label: str
    kernel_sha256: str
    kernel_bytes: int
    pool_index: int
    catalog_id: str | None
    catalog_version: str | None
    manifest_sha256: str | None
    released_utc: str | None
    planetary_ephemeris: str | None
    coverage_restricted_to_observed_arc: bool | None


@dataclass(frozen=True, slots=True)
class OrbitalStateSource:
    """Complete source and exact-coverage receipt for one routed ICRF state."""

    legs: tuple[OrbitalStateLeg, ...]
    covered_intervals_tdb: tuple[tuple[float, float], ...]
    pool_generation: int


@dataclass(frozen=True, slots=True)
class _BoundOrbitalState:
    """Internal state product consumed by frame rotation and extraction."""

    body: OrbitalBodyIdentity
    center_key: str
    time: _BoundEphemerisTime
    gravity: _OrbitalGravity
    position_icrf_km: tuple[float, float, float]
    velocity_icrf_km_per_day: tuple[float, float, float]
    source: OrbitalStateSource


@dataclass(frozen=True, slots=True)
class _LeasedOrbitalContext:
    """Stage 2 search inputs valid only while the owning lease is active."""

    body: OrbitalBodyIdentity
    center_key: str
    center_naif_id: int
    time: _BoundEphemerisTime
    gravity: _OrbitalGravity
    pool: KernelPool
    snapshot: Any
    initial_route: tuple[Any, ...]
    initial_state: _RoutedState


_PLANET_NAME_IDENTITIES: dict[str, OrbitalBodyIdentity] = {
    "mercury": OrbitalBodyIdentity(
        Body.MERCURY, OrbitalBodyKind.PLANET_BODY, 199
    ),
    "venus": OrbitalBodyIdentity(Body.VENUS, OrbitalBodyKind.PLANET_BODY, 299),
    "earth": OrbitalBodyIdentity(Body.EARTH, OrbitalBodyKind.PLANET_BODY, 399),
    "earth-moon barycenter": OrbitalBodyIdentity(
        "Earth-Moon Barycenter", OrbitalBodyKind.EARTH_MOON_BARYCENTER, 3
    ),
    "earth moon barycenter": OrbitalBodyIdentity(
        "Earth-Moon Barycenter", OrbitalBodyKind.EARTH_MOON_BARYCENTER, 3
    ),
    "emb": OrbitalBodyIdentity(
        "Earth-Moon Barycenter", OrbitalBodyKind.EARTH_MOON_BARYCENTER, 3
    ),
    "mars": OrbitalBodyIdentity(
        Body.MARS, OrbitalBodyKind.PLANET_SYSTEM_BARYCENTER, 4
    ),
    "jupiter": OrbitalBodyIdentity(
        Body.JUPITER, OrbitalBodyKind.PLANET_SYSTEM_BARYCENTER, 5
    ),
    "saturn": OrbitalBodyIdentity(
        Body.SATURN, OrbitalBodyKind.PLANET_SYSTEM_BARYCENTER, 6
    ),
    "uranus": OrbitalBodyIdentity(
        Body.URANUS, OrbitalBodyKind.PLANET_SYSTEM_BARYCENTER, 7
    ),
    "neptune": OrbitalBodyIdentity(
        Body.NEPTUNE, OrbitalBodyKind.PLANET_SYSTEM_BARYCENTER, 8
    ),
    "pluto": OrbitalBodyIdentity(
        Body.PLUTO, OrbitalBodyKind.PLANET_SYSTEM_BARYCENTER, 9
    ),
    "moon": OrbitalBodyIdentity(Body.MOON, OrbitalBodyKind.MOON, 301),
}
_PLANET_ID_IDENTITIES = {
    identity.naif_id: identity for identity in _PLANET_NAME_IDENTITIES.values()
}
_KNOWN_NON_ORBITAL_NAMES = {
    Body.SUN.casefold(),
    Body.TRUE_NODE.casefold(),
    Body.MEAN_NODE.casefold(),
    Body.LILITH.casefold(),
    Body.TRUE_LILITH.casefold(),
    "solar system barycenter",
    "ssb",
}
_KNOWN_UNSERVED_PLANET_IDS = {
    0,
    1,
    2,
    10,
    499,
    599,
    699,
    799,
    899,
    999,
}
_INSTALL_URL = "https://moira-astro.com/ephemerides"


@lru_cache(maxsize=1)
def _small_body_ids() -> dict[int, tuple[SmallBodyIdentity, ...]]:
    from .asteroids import ASTEROID_NAIF
    from .comets import _CANONICAL_COMET_NAIF

    by_id: dict[int, list[SmallBodyIdentity]] = {}
    for name, naif_id in ASTEROID_NAIF.items():
        by_id.setdefault(naif_id, []).append(
            SmallBodyIdentity("asteroid", name, naif_id, name, False)
        )
    for name, naif_id in _CANONICAL_COMET_NAIF.items():
        by_id.setdefault(naif_id, []).append(
            SmallBodyIdentity("comet", name, naif_id, name, False)
        )
    return {naif_id: tuple(items) for naif_id, items in by_id.items()}


@lru_cache(maxsize=1)
def _known_body_names() -> tuple[str, ...]:
    from .asteroids import ASTEROID_NAIF
    from .comets import _CANONICAL_COMET_NAIF, _COMET_ALIASES

    return tuple(
        sorted(
            {
                *(identity.name for identity in _PLANET_NAME_IDENTITIES.values()),
                "EMB",
                "Sun",
                "True Node",
                "Mean Node",
                "Lilith",
                "True Lilith",
                *ASTEROID_NAIF,
                *_CANONICAL_COMET_NAIF,
                *_COMET_ALIASES,
            },
            key=str.casefold,
        )
    )


def _small_body_public_identity(identity: SmallBodyIdentity) -> OrbitalBodyIdentity:
    kind = (
        OrbitalBodyKind.ASTEROID
        if identity.family == "asteroid"
        else OrbitalBodyKind.COMET
    )
    return OrbitalBodyIdentity(identity.canonical_name, kind, identity.naif_id)


def resolve_orbital_body(body: str | int) -> OrbitalBodyIdentity:
    """Resolve the strict Stage 1 body grammar without guessing precedence."""

    if isinstance(body, bool) or not isinstance(body, (str, int)):
        raise OrbitalInputError("body", body, ("non-empty string", "integer NAIF ID"))

    if isinstance(body, int):
        planet = _PLANET_ID_IDENTITIES.get(body)
        if planet is not None:
            return planet
        candidates = _small_body_ids().get(body, ())
        if len(candidates) > 1:
            raise OrbitalAmbiguousBodyError(str(body), candidates)
        if candidates:
            return _small_body_public_identity(candidates[0])
        if body in _KNOWN_UNSERVED_PLANET_IDS:
            raise OrbitalBodyNotSupportedError(
                f"NAIF {body}", "known solar-system identity", "identity is not an admitted Stage 1 orbital target"
            )
        raise OrbitalBodyNotFoundError(body)

    query = body.strip()
    if not query:
        raise OrbitalInputError("body", body, ("non-empty string",))
    planet = _PLANET_NAME_IDENTITIES.get(query.casefold())
    if planet is not None:
        return planet
    try:
        small = resolve_small_body_identity(query)
    except AmbiguousSmallBodyNameError as exc:
        raise OrbitalAmbiguousBodyError(exc.query, exc.candidates) from exc
    except (TypeError, ValueError) as exc:
        raise OrbitalInputError("body", body, ("known body or family-qualified name",)) from exc
    if small is not None:
        return _small_body_public_identity(small)
    if query.casefold() in _KNOWN_NON_ORBITAL_NAMES:
        reason = (
            f"Body.{query.upper().replace(' ', '_')} is a center or calculated "
            "point, not an orbital target"
        )
        raise OrbitalBodyNotSupportedError(query, "non-orbital point", reason)
    try:
        from .stars import star_name_resolves

        is_star = star_name_resolves(query)
    except (KeyError, ValueError):
        is_star = False
    if is_star:
        raise OrbitalBodyNotSupportedError(
            query, "fixed star", "fixed stars do not have a solar-system SPK orbit product"
        )
    close = tuple(
        difflib.get_close_matches(query, _known_body_names(), n=5, cutoff=0.6)
    )
    raise OrbitalBodyNotFoundError(query, close)


def _validate_center(body: OrbitalBodyIdentity, center_key: str) -> None:
    allowed = ("EARTH",) if body.kind is OrbitalBodyKind.MOON else ("SUN",)
    if center_key not in allowed:
        raise OrbitalCenterNotAllowedError(body.name, center_key, allowed)


def _translate_time_error(exc: _EphemerisTimeBasisError) -> OrbitalTimeBasisError:
    return OrbitalTimeBasisError(
        exc.direction,
        exc.provisional_identity_label,
        exc.final_identity_label,
        exc.iterations,
        exc.source_product,
        exc.round_trip_residual_days,
    )


def _state_source(route: _RoutedState) -> OrbitalStateSource:
    legs: list[OrbitalStateLeg] = []
    for receipt in route.legs:
        source = receipt.source
        if not source.label or not source.sha256:
            raise OrbitalSourceReceiptError(
                receipt.center,
                receipt.target,
                type(source).__name__,
                "content-derived source identity",
            )
        legs.append(
            OrbitalStateLeg(
                center_naif_id=receipt.center,
                target_naif_id=receipt.target,
                traversal_sign=receipt.traversal_sign,
                segment_type=receipt.data_type,
                coverage_start_tdb=receipt.coverage_start_tdb,
                coverage_end_tdb=receipt.coverage_end_tdb,
                kernel_label=source.label,
                kernel_sha256=source.sha256,
                kernel_bytes=source.byte_length,
                pool_index=receipt.pool_index,
                catalog_id=source.catalog_id,
                catalog_version=source.catalog_version,
                manifest_sha256=source.manifest_sha256,
                released_utc=source.released_utc,
                planetary_ephemeris=source.planetary_ephemeris,
                coverage_restricted_to_observed_arc=(
                    source.coverage_restricted_to_observed_arc
                ),
            )
        )
    if not legs or not route.covered_intervals_tdb:
        raise OrbitalSourceReceiptError(0, 0, "KernelPool", "exact route receipt")
    return OrbitalStateSource(
        legs=tuple(legs),
        covered_intervals_tdb=tuple(route.covered_intervals_tdb),
        pool_generation=0 if route.pool_generation is None else route.pool_generation,
    )


def _body_coverage(snapshot: Any, naif_id: int) -> tuple[
    tuple[tuple[float, float], ...], tuple[str, ...], bool | None
]:
    intervals: list[tuple[float, float]] = []
    labels: list[str] = []
    observed_arc: bool | None = None
    for reader in snapshot.readers:
        pairs = getattr(reader, "_coverage_pairs_tdb", None)
        getter = getattr(reader, "coverage_intervals_tdb", None)
        if not callable(pairs) or not callable(getter):
            continue
        source = getattr(reader, "_source_identity", None)
        for center, target in pairs():
            if naif_id not in {center, target}:
                continue
            intervals.extend(getter(center, target))
            if source is not None:
                if source.label not in labels:
                    labels.append(source.label)
                if source.coverage_restricted_to_observed_arc is not None:
                    observed_arc = source.coverage_restricted_to_observed_arc
    intervals.sort()
    merged: list[tuple[float, float]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((float(start), float(end)))
    return tuple(merged), tuple(labels), observed_arc


def _not_loaded_error(body: OrbitalBodyIdentity) -> OrbitalBodyNotLoadedError:
    if body.kind is OrbitalBodyKind.ASTEROID:
        catalog, version = "moira-asteroids", "2026.08.12.1"
    elif body.kind is OrbitalBodyKind.COMET:
        catalog, version = "moira-comets", "2026.07.28.1"
    else:
        catalog, version = "planetary-ephemeris", None
    return OrbitalBodyNotLoadedError(
        body.name,
        body.naif_id,
        catalog,
        version,
        _INSTALL_URL,
    )


def bind_orbital_state(
    body: str | int,
    jd_ut: float,
    *,
    center_key: str,
    reader: object | None,
) -> _BoundOrbitalState:
    """Build one stable, strict, source-receipted ICRF orbital state."""

    identity = resolve_orbital_body(body)
    _validate_center(identity, center_key)
    if isinstance(jd_ut, bool) or not isinstance(jd_ut, (int, float)):
        raise OrbitalInputError("jd_ut", jd_ut, ("finite representable real JD",))
    epoch = float(jd_ut)
    if not math.isfinite(epoch) or math.ulp(epoch) >= 1.0:
        raise OrbitalInputError("jd_ut", jd_ut, ("finite representable real JD",))

    selected_reader = get_active_reader() if reader is None else reader
    if selected_reader is None:
        raise OrbitalKernelMissingError("no active or explicit reader")
    pool = (
        selected_reader
        if isinstance(selected_reader, KernelPool)
        else KernelPool((selected_reader,))
    )

    try:
        lease = pool._read_lease()
    except AttributeError as exc:
        raise OrbitalSourceReceiptError(
            10 if center_key == "SUN" else 399,
            identity.naif_id,
            type(selected_reader).__name__,
            "snapshot lease",
        ) from exc

    with lease as snapshot:
        try:
            time = _bind_ephemeris_time(epoch, pool, snapshot=snapshot)
        except _EphemerisTimeBasisError as exc:
            raise _translate_time_error(exc) from exc
        except OutOfRangeError as exc:
            intervals, labels, observed_arc = _body_coverage(
                snapshot, identity.naif_id
            )
            raise OrbitalCoverageError(
                identity.name,
                identity.naif_id,
                epoch,
                intervals,
                labels,
                observed_arc,
            ) from exc
        except (ArithmeticError, ValueError) as exc:
            raise OrbitalInputError(
                "jd_ut", jd_ut, ("finite representable real JD",)
            ) from exc

        gravity = select_orbital_gravity(
            center_key=center_key,
            body_kind=identity.kind.value,
            naif_id=identity.naif_id,
            identity=time.identity,
        )
        center_id = 399 if center_key == "EARTH" else 10
        evaluator = getattr(pool, "position_and_velocity_tdb_with_receipt", None)
        if not callable(evaluator):
            raise OrbitalSourceReceiptError(
                center_id,
                identity.naif_id,
                type(selected_reader).__name__,
                "position_and_velocity_tdb_with_receipt",
            )
        try:
            route = evaluator(
                center_id,
                identity.naif_id,
                time.epoch_tdb,
                snapshot=snapshot,
            )
        except RuntimeError as exc:
            raise OrbitalSourceReceiptError(
                center_id,
                identity.naif_id,
                type(selected_reader).__name__,
                "atomic state/source receipt",
            ) from exc
        except (OutOfRangeError, KeyError, ValueError) as exc:
            intervals, labels, observed_arc = _body_coverage(
                snapshot, identity.naif_id
            )
            if not intervals:
                raise _not_loaded_error(identity) from exc
            raise OrbitalCoverageError(
                identity.name,
                identity.naif_id,
                time.epoch_tdb,
                intervals,
                labels,
                observed_arc,
            ) from exc

        source = _state_source(route)
        return _BoundOrbitalState(
            body=identity,
            center_key=center_key,
            time=time,
            gravity=gravity,
            position_icrf_km=route.position_km,
            velocity_icrf_km_per_day=route.velocity_km_per_day,
            source=source,
        )


@contextmanager
def lease_orbital_context(
    body: str | int,
    jd_ut: float,
    *,
    center_key: str,
    reader: object | None,
):
    """Lease one strict identity, clock, gravity and route for Stage 2.

    The yielded object must not escape the context.  Keeping this boundary in
    the state layer makes the passage search use the same admission and error
    translation as Stage 1 while retaining the immutable pool generation for
    every sampled state.
    """

    identity = resolve_orbital_body(body)
    _validate_center(identity, center_key)
    if isinstance(jd_ut, bool) or not isinstance(jd_ut, (int, float)):
        raise OrbitalInputError("jd_ut", jd_ut, ("finite representable real JD",))
    epoch = float(jd_ut)
    if not math.isfinite(epoch) or math.ulp(epoch) >= 1.0:
        raise OrbitalInputError("jd_ut", jd_ut, ("finite representable real JD",))

    selected_reader = get_active_reader() if reader is None else reader
    if selected_reader is None:
        raise OrbitalKernelMissingError("no active or explicit reader")
    pool = (
        selected_reader
        if isinstance(selected_reader, KernelPool)
        else KernelPool((selected_reader,))
    )
    try:
        lease = pool._read_lease()
    except AttributeError as exc:
        raise OrbitalSourceReceiptError(
            10 if center_key == "SUN" else 399,
            identity.naif_id,
            type(selected_reader).__name__,
            "snapshot lease",
        ) from exc

    with lease as snapshot:
        try:
            time = _bind_ephemeris_time(epoch, pool, snapshot=snapshot)
        except _EphemerisTimeBasisError as exc:
            raise _translate_time_error(exc) from exc
        except OutOfRangeError as exc:
            intervals, labels, observed_arc = _body_coverage(
                snapshot, identity.naif_id
            )
            raise OrbitalCoverageError(
                identity.name,
                identity.naif_id,
                epoch,
                intervals,
                labels,
                observed_arc,
            ) from exc
        except (ArithmeticError, ValueError) as exc:
            raise OrbitalInputError(
                "jd_ut", jd_ut, ("finite representable real JD",)
            ) from exc

        gravity = select_orbital_gravity(
            center_key=center_key,
            body_kind=identity.kind.value,
            naif_id=identity.naif_id,
            identity=time.identity,
        )
        center_id = 399 if center_key == "EARTH" else 10
        route_finder = getattr(pool, "_find_route_tdb", None)
        evaluator = getattr(pool, "_evaluate_route_tdb", None)
        if not callable(route_finder) or not callable(evaluator):
            raise OrbitalSourceReceiptError(
                center_id,
                identity.naif_id,
                type(selected_reader).__name__,
                "frozen TDB route plan",
            )
        route = route_finder(snapshot, center_id, identity.naif_id, time.epoch_tdb)
        if route is None:
            intervals, labels, observed_arc = _body_coverage(
                snapshot, identity.naif_id
            )
            if not intervals:
                raise _not_loaded_error(identity)
            raise OrbitalCoverageError(
                identity.name,
                identity.naif_id,
                time.epoch_tdb,
                intervals,
                labels,
                observed_arc,
            )
        try:
            initial_state = evaluator(route, time.epoch_tdb, snapshot=snapshot)
            _state_source(initial_state)
        except RuntimeError as exc:
            raise OrbitalSourceReceiptError(
                center_id,
                identity.naif_id,
                type(selected_reader).__name__,
                "atomic state/source receipt",
            ) from exc

        yield _LeasedOrbitalContext(
            body=identity,
            center_key=center_key,
            center_naif_id=center_id,
            time=time,
            gravity=gravity,
            pool=pool,
            snapshot=snapshot,
            initial_route=route,
            initial_state=initial_state,
        )


__all__ = [
    "OrbitalBodyIdentity",
    "OrbitalBodyKind",
    "OrbitalStateLeg",
    "OrbitalStateSource",
]
