from __future__ import annotations

import re
import time
import uuid
import logging
from asgiref.sync import iscoroutinefunction
from django.utils.decorators import sync_and_async_middleware

from .logging import request_id_var

logger = logging.getLogger("kalanpro.request")
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


def _request_id(request) -> str:
    supplied = str(request.headers.get("X-Request-ID") or "").strip()
    if supplied and _SAFE_REQUEST_ID.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


@sync_and_async_middleware
def request_id_middleware(get_response):
    """Corrèle frontend/proxy/backend et journalise la durée de chaque requête API."""

    if iscoroutinefunction(get_response):
        async def middleware(request):
            rid = _request_id(request)
            token = request_id_var.set(rid)
            request.request_id = rid
            started = time.perf_counter()
            response = None
            try:
                response = await get_response(request)
                response["X-Request-ID"] = rid
                return response
            finally:
                duration_ms = round((time.perf_counter() - started) * 1000, 1)
                logger.info(
                    "%s %s",
                    request.method,
                    request.path,
                    extra={
                        "method": request.method,
                        "path": request.path,
                        "status_code": getattr(response, "status_code", 500),
                        "duration_ms": duration_ms,
                    },
                )
                request_id_var.reset(token)
        return middleware

    def middleware(request):
        rid = _request_id(request)
        token = request_id_var.set(rid)
        request.request_id = rid
        started = time.perf_counter()
        response = None
        try:
            response = get_response(request)
            response["X-Request-ID"] = rid
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.info(
                "%s %s",
                request.method,
                request.path,
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": getattr(response, "status_code", 500),
                    "duration_ms": duration_ms,
                },
            )
            request_id_var.reset(token)
    return middleware
