from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.database import initialize_database
from app.evaluation_service import (
    SourceServiceError,
    aggregate_metrics,
    evaluate_source_run,
    list_evaluations,
)
from app.scenarios import SCENARIOS
from app.schemas import EvaluationCreate


def create_app(config: Settings | None = None, transport: httpx.BaseTransport | None = None) -> FastAPI:
    active_config = config or Settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(active_config.database_path)
        yield

    application = FastAPI(title="EvalForge", version="0.1.0", lifespan=lifespan)
    application.state.settings = active_config
    application.state.http_transport = transport
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/api/scenarios")
    def scenarios() -> list[dict[str, str]]:
        return [
            {
                "id": scenario.id,
                "name": scenario.name,
                "description": scenario.description,
                "probe_type": scenario.probe_type,
            }
            for scenario in SCENARIOS.values()
        ]

    @application.get("/api/source-runs")
    def source_runs(request: Request) -> list[dict[str, Any]]:
        try:
            with httpx.Client(
                base_url=active_config.codepilot_api_url,
                transport=request.app.state.http_transport,
                timeout=15,
            ) as client:
                response = client.get("/api/runs")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail="Could not load CodePilot runs") from error

    @application.get("/api/evaluations")
    def evaluations(request: Request) -> list[dict[str, Any]]:
        return list_evaluations(active_config.database_path)

    @application.get("/api/metrics")
    def metrics(request: Request) -> dict[str, Any]:
        return aggregate_metrics(list_evaluations(active_config.database_path))

    @application.post("/api/evaluations", status_code=201)
    def create_evaluation(payload: EvaluationCreate, request: Request) -> dict[str, Any]:
        try:
            return evaluate_source_run(
                payload.run_id,
                payload.scenario_id,
                active_config,
                request.app.state.http_transport,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except SourceServiceError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    return application


app = create_app()
