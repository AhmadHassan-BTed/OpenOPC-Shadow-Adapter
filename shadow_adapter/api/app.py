"""FastAPI application factory for the Shadow Adapter API server.

Serves:
- REST API under `/api` (`/api/auth`, `/api/tasks`, `/api/health`)
- Static files for the built React Human Portal (`frontend/dist`) mounted at `/` with HTML SPA fallback routing
- CLI runner `shadow-serve` entry point
"""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

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
        title="OpenOPC Shadow Adapter — Human Portal API",
        version="0.1.0",
        description="REST API and Human Portal for shadow-mode OpenOPC task intercept, park, and resume.",
        lifespan=lifespan,
    )

    # CORS configuration for development React server (Vite)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register REST API routers with /api prefix
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])

    # Endpoint for /api/health directly
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
                "status": "Frontend production build not found in frontend/dist. API routes active under /api.",
            }

    return app


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
