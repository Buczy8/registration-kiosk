from __future__ import annotations
import enum
import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApplicationErrorCode(str, enum.Enum):
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    BAD_REQUEST = "bad_request"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_SERVER_ERROR = "internal_server_error"
    HTTP_ERROR = "http_error"


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def error_response(
        *,
        request: Request,
        status_code: int,
        code: ApplicationErrorCode,
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


def _error_code_for_status(status_code: int) -> ApplicationErrorCode:
    if status_code == HTTPStatus.NOT_FOUND:
        return ApplicationErrorCode.NOT_FOUND
    if status_code == HTTPStatus.UNAUTHORIZED:
        return ApplicationErrorCode.UNAUTHORIZED
    if status_code == HTTPStatus.BAD_REQUEST:
        return ApplicationErrorCode.BAD_REQUEST
    if status_code == HTTPStatus.CONFLICT:
        return ApplicationErrorCode.CONFLICT
    return ApplicationErrorCode.HTTP_ERROR


async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
) -> JSONResponse:
    code = _error_code_for_status(exc.status_code)
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
        code=ApplicationErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details=jsonable_encoder(exc.errors()),
    )


async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled request error")
    return error_response(
        request=request,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        code=ApplicationErrorCode.INTERNAL_SERVER_ERROR,
        message="Internal server error",
    )


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")
