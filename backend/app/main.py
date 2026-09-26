from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.dependencies import Container
from app.api.error_handlers import register_error_handlers
from app.api.routes import files, health, intake
from app.application.intake.orchestrator import IntakeOrchestrator
from app.core.config import Settings, get_settings
from app.core.ids import new_id
from app.core.logging import configure_logging
from app.infrastructure.database.migrations import upgrade_database
from app.infrastructure.database.registry_repository import SqlAlchemyFileRegistry
from app.infrastructure.database.session import create_database_engine, create_session_factory
from app.infrastructure.storage.local_original_file_store import LocalOriginalFileStore


def create_app(settings: Settings | None = None) -> FastAPI:
    effective_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        effective_settings.prepare_directories()
        upgrade_database(effective_settings.effective_database_url)
        engine = create_database_engine(effective_settings.effective_database_url)
        registry = SqlAlchemyFileRegistry(create_session_factory(engine))
        file_store = LocalOriginalFileStore(effective_settings.runtime_root)
        app.state.container = Container(
            settings=effective_settings,
            engine=engine,
            registry=registry,
            file_store=file_store,
            intake=IntakeOrchestrator(
                registry=registry,
                file_store=file_store,
                settings=effective_settings,
            ),
        )
        yield
        engine.dispose()

    configure_logging()
    app = FastAPI(
        title="Context Router API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(effective_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID") or f"req_{new_id()}"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    register_error_handlers(app)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(intake.router, prefix="/api/v1")
    app.include_router(files.router, prefix="/api/v1")
    return app


app = create_app()
