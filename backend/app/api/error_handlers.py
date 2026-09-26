import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError

logger = logging.getLogger(__name__)


def _problem(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"https://context-router.local/problems/{code}",
            "title": title,
            "status": status,
            "code": code,
            "detail": detail,
            "request_id": request_id,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            request,
            status=exc.status_code,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors: Sequence[dict[str, Any]] = exc.errors()
        detail = "; ".join(str(item.get("msg", "invalid value")) for item in errors)
        return _problem(
            request,
            status=422,
            code="invalid-request",
            title="Invalid request",
            detail=detail,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=exc)
        return _problem(
            request,
            status=500,
            code="internal-error",
            title="Internal server error",
            detail="服务处理请求时发生内部错误。",
        )
