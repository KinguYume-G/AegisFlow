"""FastAPI application assembly for the modular monolith."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aegisflow_core.health.router import router as health_router
from aegisflow_core.logging import configure_logging
from aegisflow_core.settings import get_settings


def create_app() -> FastAPI:
    """Validate configuration and construct the minimal ASGI application."""
    configure_logging()
    get_settings()

    app = FastAPI(title="AegisFlow Core")
    logger = logging.getLogger("aegisflow")

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        _request: Request, _error: Exception
    ) -> JSONResponse:
        logger.error("unhandled_request_error")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An internal error occurred.",
                }
            },
        )

    app.include_router(health_router)
    return app
