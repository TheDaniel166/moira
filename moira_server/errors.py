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
    LunarApparentGeometryError,
    LunarOrientationCoverageError,
    LunarOrientationResourceError,
    LunarOrientationResourceIdentityError,
    LunarOrientationResourceMissingError,
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
from moira.gochara_dated import GocharaResourceError, GocharaCoverageError
from moira.gochara_windows import GocharaWindowBudgetError, GocharaWindowDomainError, GocharaWindowUnresolvedError
from moira.sayanadi_dated import SayanadiResourceError, SayanadiCoverageError
from moira.muhurta_search import MuhurtaResourceError, MuhurtaCoverageError
from moira.sade_sati import SadeSatiBudgetError
from moira.muhurta_marriage_dated import MarriageSearchBudgetError
from moira.muhurta_election import ElectionSearchBudgetError
from moira.shadbala_context import ShadbalaContextError
from moira.kalachakra import (
    KalachakraProjectionError, KalachakraCoverageError,
    KalachakraResourceError, KalachakraInvariantError,
)


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


_LUNAR_ORIENTATION_ERROR_POLICIES = (
    (
        LunarOrientationCoverageError,
        422,
        "date_outside_lunar_orientation_coverage",
        "ephemeris_coverage",
        "The requested date is outside the admitted lunar-orientation coverage.",
        False,
    ),
    (
        LunarOrientationResourceMissingError,
        503,
        "lunar_orientation_resource_not_ready",
        "ephemeris_availability",
        "The lunar-orientation resources are not installed.",
        False,
    ),
    (
        LunarOrientationResourceIdentityError,
        503,
        "lunar_orientation_resource_identity_mismatch",
        "server_configuration",
        "The installed lunar-orientation resources failed identity validation.",
        False,
    ),
    (
        LunarOrientationResourceError,
        503,
        "lunar_orientation_resource_not_ready",
        "ephemeris_availability",
        "The lunar-orientation resources are unavailable.",
        False,
    ),
    (
        LunarApparentGeometryError,
        500,
        "lunar_orientation_computation_failed",
        "computation",
        "The lunar apparent-orientation geometry could not be formed.",
        True,
    ),
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register phase-1 exception handlers."""

    # The occultation path solver refuses a path it cannot continue without
    # guessing (an ArithmeticError, so no generic handler caught it: HTTP 500).
    # The request was valid; the answer is "not solvable", not "bad input".
    from moira.occultations import _OccultationPathSolveError

    @app.exception_handler(_OccultationPathSolveError)
    async def handle_occultation_path_not_solvable(
        request: Request,
        exc: _OccultationPathSolveError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        return JSONResponse(
            status_code=422,
            content=_error_body(
                error_code="path_not_solvable",
                message=f"The occultation path cannot be traced for this event: {exc}",
                category="search_resolution",
                request_id=request_id,
            ),
        )

    def kalachakra_handler(status, code, category, message):
        async def handle(request, exc):
            request_id = getattr(request.state, "request_id", str(uuid4()))
            if status == 500:
                _LOGGER.exception("Kalachakra invariant failure [request_id=%s]", request_id,
                    exc_info=(type(exc), exc, exc.__traceback__))
            details = None
            if type(exc) is KalachakraProjectionError:
                path = exc.path
                details = {"reason": "unrepresentable_positive_interval"}
                if type(path) is tuple and 1 <= len(path) <= 2 and all(type(i) is int and 0 <= i <= 8 for i in path):
                    details["path"] = "/".join(str(i) for i in path)
            return JSONResponse(status_code=status, content=_error_body(
                error_code=code, message=message, category=category, request_id=request_id, details=details))
        return handle

    for error, status, code, category, message in (
        (KalachakraProjectionError, 422, "kalachakra_projection_unrepresentable", "input_validation",
         "Positive source intervals cannot be represented at the requested calendar origin."),
        (KalachakraCoverageError, 422, "kalachakra_epoch_out_of_coverage", "resource_coverage",
         "The birth epoch is outside serving ephemeris coverage."),
        (KalachakraResourceError, 503, "kalachakra_resource_unavailable", "kernel_readiness",
         "A required Kalachakra ephemeris, lunar clock identity or live anchor is unavailable."),
        (KalachakraInvariantError, 500, "kalachakra_internal_invariant", "internal_error",
         "An internal Kalachakra result failed validation."),
    ):
        app.add_exception_handler(error, kalachakra_handler(status, code, category, message))

    @app.exception_handler(SadeSatiBudgetError)
    async def handle_sade_budget(request: Request, exc: SadeSatiBudgetError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(
            error_code='sade_sati_budget_exceeded', message=str(exc), category='search_budget',
            request_id=getattr(request.state,'request_id',None),
            details={'max_evaluations':exc.budget,'evaluations':exc.evaluations,'stage':exc.stage}))

    @app.exception_handler(ShadbalaContextError)
    async def handle_strength_context(request: Request, exc: ShadbalaContextError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(
            error_code='shadbala_context_unavailable', message=str(exc), category='calculation_context',
            request_id=getattr(request.state,'request_id',None)))

    @app.exception_handler(SayanadiResourceError)
    async def handle_sayanadi_resource(request: Request, exc: SayanadiResourceError) -> JSONResponse:
        return JSONResponse(status_code=503, content=_error_body(
            error_code="sayanadi_resource_unavailable", message=str(exc),
            category="ephemeris_availability", request_id=getattr(request.state, "request_id", None),
        ))

    @app.exception_handler(SayanadiCoverageError)
    async def handle_sayanadi_coverage(request: Request, exc: SayanadiCoverageError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(
            error_code="sayanadi_date_outside_coverage", message=str(exc),
            category="ephemeris_coverage", request_id=getattr(request.state, "request_id", None),
        ))

    @app.exception_handler(GocharaResourceError)
    async def handle_gochara_resource(request: Request, exc: GocharaResourceError) -> JSONResponse:
        return JSONResponse(status_code=503, content=_error_body(
            error_code="gochara_resource_unavailable", message=str(exc),
            category="ephemeris_availability", request_id=getattr(request.state, "request_id", None),
        ))

    @app.exception_handler(GocharaCoverageError)
    async def handle_gochara_coverage(request: Request, exc: GocharaCoverageError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(
            error_code="gochara_date_outside_coverage", message=str(exc),
            category="ephemeris_coverage", request_id=getattr(request.state, "request_id", None),
        ))

    @app.exception_handler(GocharaWindowBudgetError)
    async def handle_gochara_window_budget(request: Request, exc: GocharaWindowBudgetError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(
            error_code="gochara_window_budget_exceeded", message=str(exc), category="search_budget",
            request_id=getattr(request.state, "request_id", None),
            details={"limit_kind": exc.limit_kind, "limit": exc.limit, "count": exc.count, "stage": exc.stage}))

    @app.exception_handler(GocharaWindowDomainError)
    async def handle_gochara_window_domain(request: Request, exc: GocharaWindowDomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(
            error_code="gochara_window_outside_certified_domain", message=str(exc), category="certified_domain",
            request_id=getattr(request.state, "request_id", None),
            details={"dependency": exc.dependency, "lower_jd_ut1": exc.lower, "upper_exclusive_jd_ut1": exc.upper}))

    @app.exception_handler(GocharaWindowUnresolvedError)
    async def handle_gochara_window_unresolved(request: Request, exc: GocharaWindowUnresolvedError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(
            error_code="gochara_window_unresolved", message=str(exc), category="search_resolution",
            request_id=getattr(request.state, "request_id", None),
            details={"reasons": exc.reasons, "count": exc.count, "maximum_width_seconds": exc.maximum_width_seconds}))

    @app.exception_handler(MarriageSearchBudgetError)
    async def handle_marriage_budget(request: Request, exc: MarriageSearchBudgetError) -> JSONResponse:
        request_id = getattr(request.state, 'request_id', str(uuid4()))
        return JSONResponse(status_code=422, content=_error_body(
            error_code='election_search_budget' if isinstance(exc,ElectionSearchBudgetError) else 'marriage_search_budget', message=str(exc), category='search_budget',
            request_id=request_id, details={'limit_kind':exc.limit_kind,'limit':exc.limit,
                                           'count':exc.count,'stage':exc.stage}))

    @app.exception_handler(MuhurtaResourceError)
    async def handle_muhurta_resource(request: Request, exc: MuhurtaResourceError) -> JSONResponse:
        return JSONResponse(status_code=503, content=_error_body(
            error_code="muhurta_resource_unavailable", message=str(exc),
            category="ephemeris_availability", request_id=getattr(request.state, "request_id", None),
        ))

    @app.exception_handler(MuhurtaCoverageError)
    async def handle_muhurta_coverage(request: Request, exc: MuhurtaCoverageError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body(
            error_code="muhurta_date_outside_coverage", message=str(exc),
            category="ephemeris_coverage", request_id=getattr(request.state, "request_id", None),
        ))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors=exc.errors()
        # Pydantic wraps ValueError subclasses raised by admission validators.
        # Preserve the engine's named deterministic budget failure even when
        # preflight rejects before the route can acquire its reader.
        if len(errors)==1:
            cause=errors[0].get('ctx',{}).get('error')
            if isinstance(cause,MarriageSearchBudgetError):
                return await handle_marriage_budget(request,cause)
            if isinstance(cause,GocharaWindowBudgetError):
                return await handle_gochara_window_budget(request,cause)
            if isinstance(cause,GocharaWindowDomainError):
                return await handle_gochara_window_domain(request,cause)
        request_id = getattr(request.state, "request_id", str(uuid4()))
        details = {
            ".".join(str(part) for part in error["loc"]): error["msg"]
            for error in errors
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

    def make_lunar_orientation_handler(
        status_code: int,
        error_code: str,
        category: str,
        message: str,
        log_failure: bool,
    ):
        async def handle_lunar_orientation_error(
            request: Request,
            exc: Exception,
        ) -> JSONResponse:
            request_id = getattr(request.state, "request_id", str(uuid4()))
            if log_failure:
                _LOGGER.exception(
                    "Lunar orientation computation failed [request_id=%s]",
                    request_id,
                    exc_info=(type(exc), exc, exc.__traceback__),
                )
            return JSONResponse(
                status_code=status_code,
                content=_error_body(
                    error_code=error_code,
                    message=message,
                    category=category,
                    request_id=request_id,
                ),
            )

        return handle_lunar_orientation_error

    for (
        exception_type,
        status_code,
        error_code,
        category,
        message,
        log_failure,
    ) in _LUNAR_ORIENTATION_ERROR_POLICIES:
        app.add_exception_handler(
            exception_type,
            make_lunar_orientation_handler(
                status_code,
                error_code,
                category,
                message,
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
        message = str(exc.args[0] if exc.args else exc)
        if message and " " not in message:
            # A bare key (e.g. 'Mars') means the request lacks a value the
            # computation needs; say so instead of echoing the name alone.
            message = f"The request is missing a required value: {message}"
        return JSONResponse(
            status_code=422,
            content=_error_body(
                error_code="validation_error",
                message=message,
                category="input_validation",
                request_id=request_id,
            ),
        )
