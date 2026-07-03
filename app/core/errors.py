from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": get_request_id(request),
        }
    }
    if details is not None:
        body["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    code = "not_found" if exc.status_code == HTTPStatus.NOT_FOUND else "http_error"
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    return error_response(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return error_response(
        request=request,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed",
        details=exc.errors(),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled request error")
    return error_response(
        request=request,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message="Internal server error",
    )


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")
