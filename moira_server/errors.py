"""HTTP error mapping for the Moira REST access surface."""

from __future__ import annotations

from enum import Enum
import logging
import math
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from moira import (
    MissingEphemerisKernelError,
    OrbitalAmbiguousBodyError,
    OrbitalBodyNotFoundError,
    OrbitalBodyNotLoadedError,
    OrbitalBodyNotSupportedError,
    OrbitalCenterNotAllowedError,
    OrbitalCoverageError,
    OrbitalFrameUnavailableError,
    OrbitalGravityModelError,
    OrbitalInputError,
    OrbitalKernelMissingError,
    OrbitalLegacyBodyNotAllowedError,
    OrbitalPassageUnavailableError,
    OrbitalSearchError,
    OrbitalSourceReceiptError,
    OrbitalStateDegenerateError,
    OrbitalTimeBasisError,
)

from .config import ServerConfigurationError


_LOGGER = logging.getLogger(__name__)


def _error_body(
    *,
    error_code: str,
    message: str,
    category: str,
    request_id: str | None = None,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "error_code": error_code,
        "message": message,
        "category": category,
        "request_id": request_id or str(uuid4()),
        "details": details,
    }


def _safe_orbital_value(value: object) -> object:
    """Serialize one documented error attribute without invoking user repr."""

    if isinstance(value, Enum):
        return _safe_orbital_value(value.value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0.0 else "-Infinity"
        return value
    if isinstance(value, (tuple, list)):
        return [_safe_orbital_value(item) for item in value]
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _ambiguous_candidates(exc: OrbitalAmbiguousBodyError) -> list[str]:
    candidates: list[str] = []
    for candidate in exc.candidates:
        family = getattr(candidate, "family", None)
        name = getattr(candidate, "canonical_name", None)
        if isinstance(family, str) and isinstance(name, str):
            candidates.append(f"{family}:{name}")
        else:
            candidates.append(str(_safe_orbital_value(candidate)))
    return candidates


def _orbital_error_details(exc: Exception) -> dict[str, object] | None:
    """Return the explicit REST allowlist for a structured orbital error."""

    if isinstance(exc, OrbitalInputError):
        return {
            "parameter": exc.parameter,
            "value": _safe_orbital_value(exc.value),
            "allowed": _safe_orbital_value(exc.allowed),
        }
    if isinstance(exc, OrbitalBodyNotSupportedError):
        return {"body": exc.body, "kind": exc.kind, "reason": exc.reason}
    if isinstance(exc, OrbitalCenterNotAllowedError):
        return {
            "body": exc.body,
            "center": exc.center,
            "allowed_centers": list(exc.allowed_centers),
        }
    if isinstance(exc, OrbitalFrameUnavailableError):
        return {
            "frame": exc.frame,
            "epoch_tt": exc.epoch_tt,
            "supported_intervals_tt": [
                [start, end] for start, end in exc.supported_intervals_tt
            ],
        }
    if isinstance(exc, OrbitalLegacyBodyNotAllowedError):
        return {
            "body": exc.body,
            "legacy_api": exc.legacy_api,
            "allowed_bodies": list(exc.allowed_bodies),
            "replacement_api": exc.replacement_api,
        }
    if isinstance(exc, OrbitalAmbiguousBodyError):
        return {"query": exc.query, "candidates": _ambiguous_candidates(exc)}
    if isinstance(exc, OrbitalBodyNotFoundError):
        return {
            "query": _safe_orbital_value(exc.query),
            "close_matches": list(exc.close_matches),
        }
    if isinstance(exc, OrbitalCoverageError):
        return {
            "body": exc.body,
            "naif_id": exc.naif_id,
            "requested_epoch_tdb": exc.requested_epoch_tdb,
            "covered_intervals_tdb": [
                [start, end] for start, end in exc.covered_intervals_tdb
            ],
            "source_labels": list(exc.source_labels),
            "coverage_restricted_to_observed_arc": (
                exc.coverage_restricted_to_observed_arc
            ),
        }
    if isinstance(exc, OrbitalBodyNotLoadedError):
        return {
            "body": exc.body,
            "naif_id": exc.naif_id,
            "catalog": exc.catalog,
            "catalog_version": exc.catalog_version,
            "install_url": exc.install_url,
        }
    if isinstance(exc, OrbitalKernelMissingError):
        # The low-level detail may contain an operator-local kernel path.
        return None
    if isinstance(exc, OrbitalGravityModelError):
        return {
            "planetary_ephemeris": exc.planetary_ephemeris,
            "summary_label": exc.summary_label,
            "admitted": list(exc.admitted),
        }
    if isinstance(exc, OrbitalTimeBasisError):
        return {
            "direction": exc.direction,
            "provisional_identity_label": exc.provisional_identity_label,
            "final_identity_label": exc.final_identity_label,
            "iterations": exc.iterations,
            "source_product": exc.source_product,
            "round_trip_residual_days": exc.round_trip_residual_days,
        }
    if isinstance(exc, OrbitalSourceReceiptError):
        return {
            "center": exc.center,
            "target": exc.target,
            "reader_type": exc.reader_type,
            "missing_capability": exc.missing_capability,
        }
    if isinstance(exc, OrbitalPassageUnavailableError):
        passages = exc.passages
        body = getattr(getattr(passages, "body", None), "name", None)
        pericenter = getattr(getattr(passages, "pericenter", None), "status", None)
        apocenter = getattr(getattr(passages, "apocenter", None), "status", None)
        return {
            "body": _safe_orbital_value(body),
            "missing_kinds": list(exc.missing_kinds),
            "pericenter_status": _safe_orbital_value(pericenter),
            "apocenter_status": _safe_orbital_value(apocenter),
        }
    return None


def _orbital_public_message(exc: Exception) -> str:
    if isinstance(exc, OrbitalInputError):
        return f"Invalid orbital request parameter {exc.parameter!r}."
    if isinstance(exc, OrbitalBodyNotFoundError):
        return "The requested orbital body is not known to Moira."
    if isinstance(exc, OrbitalAmbiguousBodyError):
        return "The requested orbital body name is ambiguous."
    if isinstance(exc, OrbitalKernelMissingError):
        return "The orbital ephemeris kernel is not ready."
    if isinstance(exc, OrbitalGravityModelError):
        return "The active ephemeris has no admitted orbital gravity model."
    if isinstance(exc, OrbitalTimeBasisError):
        return "The orbital time basis could not be established."
    if isinstance(exc, OrbitalSourceReceiptError):
        return "The orbital state could not be bound to a source receipt."
    if isinstance(exc, OrbitalStateDegenerateError):
        return "The supplied state does not define a stable osculating orbit."
    if isinstance(exc, OrbitalSearchError):
        return "The bounded orbital-event search did not converge."
    if isinstance(exc, OrbitalPassageUnavailableError):
        return "A complete pair of orbital passages is unavailable in the searched interval."
    return str(exc)


_ORBITAL_ERROR_POLICIES = (
    (OrbitalInputError, 422, "invalid_parameter", "input_validation", False),
    (
        OrbitalBodyNotSupportedError,
        422,
        "body_not_supported",
        "input_validation",
        False,
    ),
    (
        OrbitalCenterNotAllowedError,
        422,
        "center_not_allowed",
        "input_validation",
        False,
    ),
    (
        OrbitalFrameUnavailableError,
        422,
        "frame_outside_model_range",
        "input_validation",
        False,
    ),
    (
        OrbitalLegacyBodyNotAllowedError,
        422,
        "body_not_allowed_in_legacy_api",
        "input_validation",
        False,
    ),
    (
        OrbitalAmbiguousBodyError,
        422,
        "ambiguous_body",
        "input_validation",
        False,
    ),
    (OrbitalBodyNotFoundError, 422, "unknown_body", "input_validation", False),
    (
        OrbitalCoverageError,
        422,
        "date_outside_ephemeris_coverage",
        "ephemeris_coverage",
        False,
    ),
    (
        OrbitalBodyNotLoadedError,
        503,
        "body_ephemeris_not_installed",
        "ephemeris_availability",
        False,
    ),
    (
        OrbitalKernelMissingError,
        503,
        "kernel_not_ready",
        "kernel_readiness",
        False,
    ),
    (
        OrbitalGravityModelError,
        503,
        "ephemeris_model_not_admitted",
        "server_configuration",
        False,
    ),
    (
        OrbitalTimeBasisError,
        503,
        "time_basis_unavailable",
        "server_configuration",
        False,
    ),
    (
        OrbitalSourceReceiptError,
        503,
        "ephemeris_source_receipt_unavailable",
        "server_configuration",
        False,
    ),
    (
        OrbitalStateDegenerateError,
        500,
        "computation_failed",
        "computation",
        True,
    ),
    (
        OrbitalSearchError,
        500,
        "computation_failed",
        "computation",
        True,
    ),
    (
        OrbitalPassageUnavailableError,
        422,
        "passage_unavailable",
        "orbital_event_availability",
        False,
    ),
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register phase-1 exception handlers."""

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        details = {
            ".".join(str(part) for part in error["loc"]): error["msg"]
            for error in exc.errors()
        }
        first_message = next(iter(details.values()), "request validation failed")
        return JSONResponse(
            status_code=422,
            content=_error_body(
                error_code="validation_error",
                message=first_message,
                category="input_validation",
                request_id=request_id,
                details=details or None,
            ),
        )

    def make_orbital_handler(
        status_code: int,
        error_code: str,
        category: str,
        log_failure: bool,
    ):
        async def handle_orbital_error(
            request: Request,
            exc: Exception,
        ) -> JSONResponse:
            request_id = getattr(request.state, "request_id", str(uuid4()))
            if log_failure:
                _LOGGER.exception(
                    "Orbital computation failed [request_id=%s]",
                    request_id,
                    exc_info=(type(exc), exc, exc.__traceback__),
                )
            return JSONResponse(
                status_code=status_code,
                content=_error_body(
                    error_code=error_code,
                    message=_orbital_public_message(exc),
                    category=category,
                    request_id=request_id,
                    details=(
                        None if log_failure else _orbital_error_details(exc)
                    ),
                ),
            )

        return handle_orbital_error

    # Register the structured orbital hierarchy before compatibility-base
    # handlers. Starlette resolves along the exception MRO, so exact orbital
    # semantics remain distinct from generic ValueError/KeyError behavior.
    for (
        exception_type,
        status_code,
        error_code,
        category,
        log_failure,
    ) in _ORBITAL_ERROR_POLICIES:
        app.add_exception_handler(
            exception_type,
            make_orbital_handler(
                status_code,
                error_code,
                category,
                log_failure,
            ),
        )

    @app.exception_handler(MissingEphemerisKernelError)
    async def handle_missing_kernel(
        request: Request,
        exc: MissingEphemerisKernelError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        return JSONResponse(
            status_code=503,
            content=_error_body(
                error_code="kernel_not_ready",
                message=str(exc),
                category="kernel_readiness",
                request_id=request_id,
            ),
        )

    @app.exception_handler(ServerConfigurationError)
    async def handle_server_configuration_error(
        request: Request,
        exc: ServerConfigurationError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        return JSONResponse(
            status_code=503,
            content=_error_body(
                error_code="server_not_configured",
                message=str(exc),
                category="server_configuration",
                request_id=request_id,
            ),
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        return JSONResponse(
            status_code=422,
            content=_error_body(
                error_code="validation_error",
                message=str(exc),
                category="input_validation",
                request_id=request_id,
            ),
        )

    @app.exception_handler(KeyError)
    async def handle_key_error(request: Request, exc: KeyError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        message = exc.args[0] if exc.args else str(exc)
        return JSONResponse(
            status_code=422,
            content=_error_body(
                error_code="validation_error",
                message=str(message),
                category="input_validation",
                request_id=request_id,
            ),
        )
