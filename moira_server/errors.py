"""HTTP error mapping for the Moira REST access surface."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from moira import MissingEphemerisKernelError


def _error_body(
    *,
    error_code: str,
    message: str,
    category: str,
    request_id: str | None = None,
    details: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "error_code": error_code,
        "message": message,
        "category": category,
        "request_id": request_id or str(uuid4()),
        "details": details,
    }


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
