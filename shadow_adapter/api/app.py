"""FastAPI application factory for the Shadow Adapter API server.

Serves:
- Versioned REST API under `/api/v1` (`/api/v1/auth`, `/api/v1/tasks`, `/api/v1/health`)
- Legacy backward-compatibility routes under `/api`
- Exception Black Hole global exception handler
- Static files for the built React Human Portal (`frontend/dist`) mounted at `/`
- CLI runner `shadow-serve` entry point
"""

from __future__ import annotations

import argparse
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from shadow_adapter.api.routes_artifacts import artifacts_router
from shadow_adapter.api.routes_auth import router as auth_router
from shadow_adapter.api.routes_tasks import router as tasks_router
from shadow_adapter.config import ShadowConfig
from shadow_adapter.security import SecurityManager
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler


def create_app(config: ShadowConfig | None = None) -> FastAPI:
    """Application factory for the Shadow Adapter FastAPI server."""
    cfg = config or ShadowConfig()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"Initializing Shadow Adapter API (db={cfg.db_path}, upload_dir={cfg.upload_dir})")
        store = ShadowStore(cfg.db_path)
        await store.initialize()

        app.state.config = cfg
        app.state.shadow_store = store
        app.state.security = SecurityManager(cfg)
        app.state.upload_handler = SecureUploadHandler(cfg)

        yield

        logger.info("Shutting down Shadow Adapter API...")
        await store.close()

    app = FastAPI(
        title="OpenOPC Contractor & Silicon Worker Portal API",
        version="0.1.0",
        description="REST API and Contractor Portal for shadow-mode OpenOPC task intercept, park, and resume.",
        lifespan=lifespan,
    )

    # Portal Coexistence Middleware — distinctly identifies responses from Port 8800
    @app.middleware("http")
    async def add_portal_identity_header(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Portal-Identity"] = "OpenOPC-Shadow-Worker-Portal"
        return response

    # CORS configuration for development React server (Vite)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Black Hole (Global Catch-All Exception Handler) ──────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"[Global Exception Black Hole] Unhandled error on {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error occurred.",
                "error_type": type(exc).__name__,
                "path": str(request.url.path),
            },
        )

    # ── Register Versioned REST API routers (/api/v1 and legacy /api) ──────────
    # Versioned v1 endpoints
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth (v1)"])
    app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["Tasks (v1)"])
    app.include_router(artifacts_router, prefix="/api/v1/artifacts", tags=["Artifacts (v1)"])

    # Legacy /api backwards-compatibility endpoints
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth (legacy)"])
    app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks (legacy)"])
    app.include_router(artifacts_router, prefix="/api/artifacts", tags=["Artifacts (legacy)"])

    # Health check endpoints
    @app.get("/api/v1/health", tags=["Health"])
    @app.get("/api/health", tags=["Health"])
    async def health_alias(request: Request):
        from shadow_adapter.api.routes_tasks import health_check

        store = request.app.state.shadow_store
        return await health_check(store=store, config=cfg)

    # Mount static files from frontend/dist if available
    dist_dir = Path(__file__).parent.parent / "frontend" / "dist"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        logger.info(f"Mounting React SPA static files from {dist_dir}")

        app.mount(
            "/assets",
            StaticFiles(directory=str(dist_dir / "assets")),
            name="static_assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            # API requests that didn't match an endpoint return 404 JSON
            if full_path.startswith("api/"):
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"API route '/{full_path}' not found"},
                )

            target_file = dist_dir / full_path
            if target_file.exists() and target_file.is_file():
                return FileResponse(str(target_file))
            # Fallback to index.html for client-side React routing
            return FileResponse(str(dist_dir / "index.html"))

    else:

        @app.get("/", include_in_schema=False)
        async def root_fallback():
            return {
                "message": "OpenOPC Shadow Adapter API Server",
                "version": "0.1.0",
                "docs": "/docs",
                "status": "Frontend production build not found in frontend/dist. API routes active under /api/v1.",
            }

    return app


def start_server_in_thread(
    port: int = 8800,
    host: str = "0.0.0.0",
    config: ShadowConfig | None = None,
) -> threading.Thread:
    """Launch the Shadow Adapter FastAPI server programmatically in a background thread.

    Enables running the Human Portal REST API programmatically inside your
    main OpenOPC application process without needing a separate terminal command.
    """
    import threading

    import uvicorn

    cfg = config or ShadowConfig(api_port=port, api_host=host)
    app = create_app(cfg)

    uv_config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(uv_config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    logger.info(f"Programmatic Shadow Adapter server launched in background thread on http://{host}:{port}")
    return thread


def main() -> None:
    """CLI entry point for ``shadow-serve`` command."""
    parser = argparse.ArgumentParser(description="OpenOPC Shadow Adapter Server")
    parser.add_argument("--port", type=int, default=8800, help="Port to bind (default: 8800)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--db", type=str, default="./shadow_tasks.db", help="Path to SQLite database")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    import uvicorn

    config = ShadowConfig(api_port=args.port, api_host=args.host, db_path=args.db)
    app = create_app(config)

    logger.info(f"Starting shadow-serve on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
