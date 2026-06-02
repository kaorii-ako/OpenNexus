from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.core.config import NexusConfig
from backend.core.llm import create_backend
from backend.core.memory import MemoryStore
from backend.api.routes import chat, digest, notion, connectors, memory


def create_app(cfg: NexusConfig) -> FastAPI:
    engine = create_backend(cfg.llm)
    store = MemoryStore(Path(cfg.memory.chroma_dir).expanduser())

    app = FastAPI(title="NEXUS API")
    app.state.cfg = cfg
    app.state.engine = engine
    app.state.store = store

    app.include_router(chat.router, prefix="/api")
    app.include_router(digest.router, prefix="/api")
    app.include_router(notion.router, prefix="/api")
    app.include_router(connectors.router, prefix="/api")
    app.include_router(memory.router, prefix="/api")

    dist = Path(cfg.server.frontend_dist)
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

        @app.get("/", include_in_schema=False)
        async def serve_spa():
            return FileResponse(str(dist / "index.html"))

    return app
