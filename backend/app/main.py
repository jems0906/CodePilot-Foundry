from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, reviews, runs, tasks
from app.config import Settings, settings
from app.database import initialize_database


def create_app(config: Settings = settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        initialize_database(config.database_path)
        yield

    application = FastAPI(title="CodePilot Foundry", version="0.1.0", lifespan=lifespan)
    application.state.settings = config
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(health.router)
    application.include_router(tasks.router)
    application.include_router(runs.router)
    application.include_router(reviews.router)
    return application


app = create_app()
