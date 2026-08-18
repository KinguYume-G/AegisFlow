"""FastAPI application assembly for the modular monolith."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aegisflow_core.health.router import router as health_router
from aegisflow_core.run_graph_router import router as run_graph_router
from aegisflow_core.run_router import router as run_router
from aegisflow_core.control_plane.run_service import PostgresRunService
from aegisflow_core.control_plane.bootstrap import bootstrap_local_mvp
from aegisflow_core.control_plane.domain.session import (
    create_database_engine,
    create_session_factory,
)
from aegisflow_core.control_plane.identity import HttpJwksResolver, OidcVerifier
from aegisflow_core.control_plane.identity import LocalIdentityVerifier, Principal
from aegisflow_core.gateway.github.webhook import (
    InMemoryReplayGuard,
    NoOpWebhookDispatcher,
    router as github_webhook_router,
)
from aegisflow_core.gateway.github.auth import InstallationTokenProvider
from aegisflow_core.gateway.github.read_tools import GitHubReadClient
from aegisflow_core.logging import configure_logging
from aegisflow_core.settings import get_settings
from aegisflow_core.packs.delivery.contracts.determinism import SystemClock
from aegisflow_core.metrics_endpoint import install_metrics
from aegisflow_core.runtime.metrics import Metrics, activate_metrics
from aegisflow_core.runtime.temporal.run_gateway import TemporalRunGateway
from aegisflow_core.telemetry import configure_telemetry


def create_app() -> FastAPI:
    """Validate configuration and construct the minimal ASGI application."""
    configure_logging()
    settings = get_settings()
    database_engine = create_database_engine(settings)
    session_factory = create_session_factory(database_engine)
    local_identity_verifier = (
        LocalIdentityVerifier(
            developer_token=settings.local_mvp_developer_token or "",
            reviewer_token=settings.local_mvp_reviewer_token or "",
        )
        if settings.local_mvp_identity_configured
        else None
    )
    temporal_gateway = TemporalRunGateway(
        address=settings.temporal_address,
        namespace=settings.temporal_namespace,
        task_queue=settings.temporal_task_queue,
    )
    run_service = PostgresRunService(
        session_factory,
        temporal_gateway,
        profile="local_mvp" if settings.local_mvp_profile_enabled else "oidc",
    )
    github_read_client: GitHubReadClient | None = None
    oidc_resolver = (
        HttpJwksResolver(
            settings.oidc_config.jwks_url,
            settings.oidc_config.http_timeout_seconds,
        )
        if settings.oidc_config is not None
        else None
    )
    oidc_verifier = (
        OidcVerifier(settings.oidc_config, oidc_resolver)
        if settings.oidc_config is not None and oidc_resolver is not None
        else None
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if settings.local_mvp_profile_enabled:
            async with session_factory.begin() as session:
                _app.state.local_bootstrap = await bootstrap_local_mvp(
                    session,
                    slug=settings.local_mvp_tenant_slug,
                    developer=Principal(LocalIdentityVerifier.issuer, "developer"),
                    reviewer=Principal(LocalIdentityVerifier.issuer, "reviewer"),
                )
        yield
        if github_read_client is not None:
            await github_read_client.aclose()
        if oidc_resolver is not None:
            await oidc_resolver.aclose()
        await database_engine.dispose()
        tracer_provider.shutdown()

    app = FastAPI(title="AegisFlow Core", lifespan=lifespan)
    metrics = Metrics()
    activate_metrics(metrics)
    install_metrics(app, metrics)
    tracer_provider = configure_telemetry(
        app,
        database_engine,
        service_name=settings.otel_service_name,
        endpoint=settings.otel_exporter_otlp_endpoint,
    )
    app.state.settings = settings
    app.state.database_engine = database_engine
    app.state.session_factory = session_factory
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
    github_read_client = (
        GitHubReadClient(
            token_provider=app.state.github_token_provider,
            timeout_seconds=settings.github_api_timeout_seconds,
        )
        if app.state.github_token_provider is not None
        else None
    )
    app.state.github_read_client = github_read_client
    app.state.oidc_verifier = oidc_verifier
    app.state.local_identity_verifier = local_identity_verifier
    app.state.temporal_gateway = temporal_gateway
    app.state.run_service = run_service
    app.state.metrics = metrics
    app.state.tracer_provider = tracer_provider
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
    app.include_router(run_graph_router)
    app.include_router(run_router)
    return app
