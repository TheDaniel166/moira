"""Structured Stage 1 orbital errors with legacy catch compatibility."""

from __future__ import annotations

from typing import Any

from .small_body_identity import AmbiguousSmallBodyNameError
from .spk_reader import (
    MissingEphemerisKernelError,
    MissingKernelError,
    OutOfRangeError,
)


class OrbitalError(Exception):
    """Base of every public Stage 1 orbital failure."""

    _constructor_args: tuple[Any, ...]

    def __reduce__(self):
        return type(self), self._constructor_args


class OrbitalInputError(OrbitalError, ValueError):
    def __init__(self, parameter: str, value: Any, allowed: tuple[Any, ...] = ()):
        self.parameter = parameter
        self.value = value
        self.allowed = tuple(allowed)
        self._constructor_args = (parameter, value, self.allowed)
        suffix = f"; allowed: {self.allowed!r}" if self.allowed else ""
        super().__init__(f"invalid orbital parameter {parameter!r}: {value!r}{suffix}")


class OrbitalBodyNotFoundError(OrbitalError, KeyError):
    def __init__(self, query: Any, close_matches: tuple[str, ...] = ()):
        self.query = query
        self.close_matches = tuple(close_matches)
        self._constructor_args = (query, self.close_matches)
        hint = (
            f" Close matches: {', '.join(self.close_matches)}."
            if self.close_matches
            else ""
        )
        super().__init__(f"orbital body {query!r} is not known to Moira.{hint}")

    def __str__(self) -> str:
        return str(self.args[0])


class OrbitalAmbiguousBodyError(OrbitalError, AmbiguousSmallBodyNameError):
    def __init__(self, query: str, candidates: tuple[Any, ...]):
        self._constructor_args = (query, tuple(candidates))
        super().__init__(query, tuple(candidates))


class OrbitalBodyNotSupportedError(OrbitalError, ValueError):
    def __init__(self, body: str, kind: str, reason: str):
        self.body = body
        self.kind = kind
        self.reason = reason
        self._constructor_args = (body, kind, reason)
        super().__init__(
            f"{body!r} ({kind}) has no Stage 1 osculating-orbit product: {reason}"
        )


class OrbitalCenterNotAllowedError(OrbitalError, ValueError):
    def __init__(
        self,
        body: str,
        center: str,
        allowed_centers: tuple[str, ...],
    ):
        self.body = body
        self.center = center
        self.allowed_centers = tuple(allowed_centers)
        self._constructor_args = (body, center, self.allowed_centers)
        super().__init__(
            f"center {center!r} is not allowed for {body!r}; "
            f"choose one of {self.allowed_centers!r}"
        )


class OrbitalFrameUnavailableError(OrbitalError, ValueError):
    def __init__(
        self,
        frame: str,
        epoch_tt: float,
        supported_intervals_tt: tuple[tuple[float, float], ...],
    ):
        self.frame = frame
        self.epoch_tt = float(epoch_tt)
        self.supported_intervals_tt = tuple(
            (float(start), float(end)) for start, end in supported_intervals_tt
        )
        self._constructor_args = (
            frame,
            self.epoch_tt,
            self.supported_intervals_tt,
        )
        super().__init__(
            f"orbital frame {frame!r} is unavailable at JD(TT) {self.epoch_tt}; "
            f"supported intervals: {self.supported_intervals_tt!r}"
        )


class OrbitalLegacyBodyNotAllowedError(OrbitalError, KeyError, ValueError):
    def __init__(
        self,
        body: str,
        legacy_api: str,
        allowed_bodies: tuple[str, ...],
        replacement_api: str,
    ):
        self.body = body
        self.legacy_api = legacy_api
        self.allowed_bodies = tuple(allowed_bodies)
        self.replacement_api = replacement_api
        self._constructor_args = (
            body,
            legacy_api,
            self.allowed_bodies,
            replacement_api,
        )
        super().__init__(
            f"{body} ({body.upper()}) is not admitted by {legacy_api}; "
            f"use {replacement_api} "
            f"with an explicit center (legacy bodies: {self.allowed_bodies!r})"
        )

    def __str__(self) -> str:
        return str(self.args[0])


class OrbitalBodyNotLoadedError(OrbitalError, KeyError):
    def __init__(
        self,
        body: str,
        naif_id: int,
        catalog: str,
        catalog_version: str | None,
        install_url: str,
    ):
        self.body = body
        self.naif_id = int(naif_id)
        self.catalog = catalog
        self.catalog_version = catalog_version
        self.install_url = install_url
        self._constructor_args = (
            body,
            self.naif_id,
            catalog,
            catalog_version,
            install_url,
        )
        super().__init__(
            f"{body} (NAIF {self.naif_id}) is catalogued but its {catalog} "
            f"ephemeris is not loaded; install it from {install_url}"
        )

    def __str__(self) -> str:
        return str(self.args[0])


class OrbitalCoverageError(OrbitalError, OutOfRangeError):
    def __init__(
        self,
        body: str,
        naif_id: int,
        requested_epoch_tdb: float,
        covered_intervals_tdb: tuple[tuple[float, float], ...],
        source_labels: tuple[str, ...] = (),
        coverage_restricted_to_observed_arc: bool | None = None,
    ):
        self.body = body
        self.naif_id = int(naif_id)
        self.requested_epoch_tdb = float(requested_epoch_tdb)
        self.covered_intervals_tdb = tuple(
            (float(start), float(end)) for start, end in covered_intervals_tdb
        )
        self.source_labels = tuple(source_labels)
        self.coverage_restricted_to_observed_arc = (
            coverage_restricted_to_observed_arc
        )
        self._constructor_args = (
            body,
            self.naif_id,
            self.requested_epoch_tdb,
            self.covered_intervals_tdb,
            self.source_labels,
            coverage_restricted_to_observed_arc,
        )
        source = f" from {self.source_labels!r}" if self.source_labels else ""
        super().__init__(
            f"{body!r} (NAIF {self.naif_id}) is not covered at "
            f"JD(TDB) {self.requested_epoch_tdb}{source}; exact intervals: "
            f"{self.covered_intervals_tdb!r}",
            True,
        )


class OrbitalKernelMissingError(
    OrbitalError,
    MissingKernelError,
    MissingEphemerisKernelError,
):
    def __init__(self, detail: Any):
        self.detail = detail
        self._constructor_args = (detail,)
        super().__init__(f"orbital ephemeris kernel is not ready: {detail}")


class OrbitalGravityModelError(OrbitalError, RuntimeError):
    def __init__(
        self,
        planetary_ephemeris: str | None,
        summary_label: str | None,
        admitted: tuple[str, ...] = ("DE440", "DE441"),
    ):
        self.planetary_ephemeris = planetary_ephemeris
        self.summary_label = summary_label
        self.admitted = tuple(admitted)
        self._constructor_args = (
            planetary_ephemeris,
            summary_label,
            self.admitted,
        )
        super().__init__(
            f"planetary ephemeris {planetary_ephemeris!r} ({summary_label!r}) "
            f"has no admitted orbital gravity model; admitted: {self.admitted!r}"
        )


class OrbitalTimeBasisError(OrbitalError, RuntimeError):
    def __init__(
        self,
        direction: str,
        provisional_identity_label: str | None,
        final_identity_label: str | None,
        iterations: int,
        source_product: str | None,
        round_trip_residual_days: float | None = None,
    ):
        self.direction = direction
        self.provisional_identity_label = provisional_identity_label
        self.final_identity_label = final_identity_label
        self.iterations = int(iterations)
        self.source_product = source_product
        self.round_trip_residual_days = round_trip_residual_days
        self._constructor_args = (
            direction,
            provisional_identity_label,
            final_identity_label,
            self.iterations,
            source_product,
            round_trip_residual_days,
        )
        super().__init__(
            f"orbital time basis failed during {direction} after "
            f"{self.iterations} iteration(s): {provisional_identity_label!r} -> "
            f"{final_identity_label!r} (source {source_product!r})"
        )


class OrbitalSourceReceiptError(OrbitalError, RuntimeError):
    def __init__(
        self,
        center: int,
        target: int,
        reader_type: str,
        missing_capability: str,
    ):
        self.center = int(center)
        self.target = int(target)
        self.reader_type = reader_type
        self.missing_capability = missing_capability
        self._constructor_args = (
            self.center,
            self.target,
            reader_type,
            missing_capability,
        )
        super().__init__(
            f"reader {reader_type} cannot bind orbital state {self.center}->{self.target} "
            f"to a source receipt; missing capability {missing_capability!r}"
        )


class OrbitalStateDegenerateError(OrbitalError, ValueError):
    def __init__(
        self,
        condition: str,
        body: str,
        epoch_tdb: float,
        position_norm_km: float,
        velocity_norm_km_per_day: float,
        normalized_angular_momentum: float,
        threshold: float,
    ):
        self.condition = condition
        self.body = body
        self.epoch_tdb = float(epoch_tdb)
        self.position_norm_km = float(position_norm_km)
        self.velocity_norm_km_per_day = float(velocity_norm_km_per_day)
        self.normalized_angular_momentum = float(normalized_angular_momentum)
        self.threshold = float(threshold)
        self._constructor_args = (
            condition,
            body,
            self.epoch_tdb,
            self.position_norm_km,
            self.velocity_norm_km_per_day,
            self.normalized_angular_momentum,
            self.threshold,
        )
        super().__init__(
            f"orbital state for {body!r} is degenerate at JD(TDB) {self.epoch_tdb}: "
            f"{condition} (normalized angular momentum "
            f"{self.normalized_angular_momentum}, threshold {self.threshold})"
        )


class OrbitalSearchError(OrbitalError, ArithmeticError):
    """The bounded Stage 2 root search could not complete honestly."""

    def __init__(
        self,
        bracket_tdb: tuple[float, float] | None,
        iterations: int,
        evaluations: int,
        tolerance_days: float,
        final_residual: float | None,
        algorithm_version: str,
    ):
        self.bracket_tdb = (
            None
            if bracket_tdb is None
            else (float(bracket_tdb[0]), float(bracket_tdb[1]))
        )
        self.iterations = int(iterations)
        self.evaluations = int(evaluations)
        self.tolerance_days = float(tolerance_days)
        self.final_residual = (
            None if final_residual is None else float(final_residual)
        )
        self.algorithm_version = algorithm_version
        self._constructor_args = (
            self.bracket_tdb,
            self.iterations,
            self.evaluations,
            self.tolerance_days,
            self.final_residual,
            algorithm_version,
        )
        location = (
            ""
            if self.bracket_tdb is None
            else f" in TDB bracket {self.bracket_tdb!r}"
        )
        residual = (
            ""
            if self.final_residual is None
            else f"; final radial residual {self.final_residual} km/day"
        )
        super().__init__(
            f"apsidal search {algorithm_version} did not converge{location} "
            f"after {self.iterations} iteration(s) and {self.evaluations} "
            f"state evaluation(s) at tolerance {self.tolerance_days} day"
            f"{residual}"
        )


class OrbitalPassageUnavailableError(OrbitalError, ValueError):
    """A legacy all-or-nothing passage vessel lacks one or both events."""

    def __init__(self, passages: Any, missing_kinds: tuple[str, ...]):
        self.passages = passages
        self.missing_kinds = tuple(missing_kinds)
        self._constructor_args = (passages, self.missing_kinds)
        body = getattr(getattr(passages, "body", None), "name", "orbital body")
        super().__init__(
            f"{body!r} has no complete legacy distance-extremes result; "
            f"missing found passage(s): {self.missing_kinds!r}. Inspect the "
            "attached apsidal passage outcomes for the exact search boundary."
        )


__all__ = [
    "OrbitalAmbiguousBodyError",
    "OrbitalBodyNotFoundError",
    "OrbitalBodyNotLoadedError",
    "OrbitalBodyNotSupportedError",
    "OrbitalCenterNotAllowedError",
    "OrbitalCoverageError",
    "OrbitalError",
    "OrbitalFrameUnavailableError",
    "OrbitalGravityModelError",
    "OrbitalInputError",
    "OrbitalKernelMissingError",
    "OrbitalLegacyBodyNotAllowedError",
    "OrbitalSourceReceiptError",
    "OrbitalStateDegenerateError",
    "OrbitalSearchError",
    "OrbitalPassageUnavailableError",
    "OrbitalTimeBasisError",
]
