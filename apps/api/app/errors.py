"""One error shape everywhere: {"error": {"code", "message", "hint"}} (TRD 7.1)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("aeroscout")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, hint: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.hint = hint


def not_found(what: str, identifier: str) -> ApiError:
    return ApiError(
        404,
        f"{what.lower()}_not_found",
        f"{what} {identifier} does not exist.",
        "It may have been removed by a demo reset. Go back and open it from the list.",
    )


def _body(code: str, message: str, hint: str | None) -> dict:
    return {"error": {"code": code, "message": message, "hint": hint}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message, exc.hint), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        message = first.get("msg", "Invalid request.")
        return JSONResponse(
            _body(
                "invalid_request",
                f"{location}: {message}" if location else message,
                "Check the highlighted value and try again.",
            ),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        hints = {
            404: "Check the address and try again.",
            405: "This action is not available here.",
        }
        return JSONResponse(
            _body(f"http_{exc.status_code}", str(exc.detail), hints.get(exc.status_code)),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error path=%s", request.url.path, exc_info=exc)
        return JSONResponse(
            _body(
                "internal_error",
                "Something went wrong on our side.",
                "Try again. If it keeps happening, load a demo scenario instead.",
            ),
            status_code=500,
        )
