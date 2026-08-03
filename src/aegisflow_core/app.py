"""FastAPI application assembly for the modular monolith."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aegisflow_core.health.router import router as health_router
from aegisflow_core.control_plane.domain.session import (
    create_database_engine,
    create_session_factory,
)
from aegisflow_core.gateway.github.webhook import (
    InMemoryReplayGuard,
    NoOpWebhookDispatcher,
    router as github_webhook_router,
)
from aegisflow_core.gateway.github.auth import InstallationTokenProvider
from aegisflow_core.logging import configure_logging
from aegisflow_core.settings import get_settings
from aegisflow_core.packs.delivery.contracts.determinism import SystemClock


def create_app() -> FastAPI:
    """Validate configuration and construct the minimal ASGI application."""
    configure_logging()
    settings = get_settings()
    database_engine = create_database_engine(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await database_engine.dispose()

    app = FastAPI(title="AegisFlow Core", lifespan=lifespan)
    app.state.settings = settings
    app.state.database_engine = database_engine
    app.state.session_factory = create_session_factory(database_engine)
    app.state.github_replay_guard = InMemoryReplayGuard()
    app.state.github_webhook_dispatcher = NoOpWebhookDispatcher()
    app.state.github_token_provider = (
        InstallationTokenProvider(
            app_id=settings.github_app_id or "",
            private_key_pem=settings.github_app_private_key or "",
            installation_id=settings.github_installation_id or "",
            clock=SystemClock(),
        )
        if settings.github_app_configured
        else None
    )
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
    app.include_router(github_webhook_router)
    return app
