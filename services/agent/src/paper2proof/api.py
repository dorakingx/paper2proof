"""FastAPI surface for background jobs and downloadable evidence."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from paper2proof.config import Settings, get_settings
from paper2proof.factory import build_workflow
from paper2proof.fixtures import list_fixtures, load_fixture
from paper2proof.reporting import report_to_markdown
from paper2proof.schemas import DecisionSubmission, JobRecord, JobRequest
from paper2proof.store import JobNotFoundError


def create_app(settings: Settings | None = None) -> FastAPI:
    selected_settings = settings or get_settings()
    workflow = build_workflow(selected_settings)
    running_tasks: set[asyncio.Task[JobRecord]] = set()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
        yield
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)

    app = FastAPI(
        title="Paper2Proof API",
        version="0.1.0",
        description="Claim-to-evidence reproducibility workflow built with Strands Agents.",
        lifespan=lifespan,
    )
    app.state.workflow = workflow
    app.state.settings = selected_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=selected_settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "paper2proof-agent",
            "runtime_mode": selected_settings.runtime_mode,
            "strands_agents": True,
            "agentcore_code_interpreter": selected_settings.runtime_mode == "agentcore",
        }

    @app.get("/v1/fixtures")
    async def fixtures() -> list[dict[str, Any]]:
        result = []
        for fixture_id in list_fixtures():
            fixture = load_fixture(fixture_id)
            result.append(
                {
                    "fixture_id": fixture_id,
                    "title": fixture.metadata.title,
                    "expected_verdict": fixture.metadata.expected_verdict,
                    "requires_approval": fixture.metadata.requires_approval,
                }
            )
        return result

    @app.post("/v1/jobs", response_model=JobRecord, status_code=status.HTTP_202_ACCEPTED)
    async def create_job(request: JobRequest, response: Response) -> JobRecord:
        job, created = await workflow.create_job(request)
        if created:
            task = asyncio.create_task(workflow.run(job.job_id))
            running_tasks.add(task)
            task.add_done_callback(running_tasks.discard)
        else:
            response.status_code = status.HTTP_200_OK
        return job

    @app.get("/v1/jobs", response_model=list[JobRecord])
    async def list_jobs() -> list[JobRecord]:
        return await workflow.store.list()

    @app.get("/v1/jobs/{job_id}", response_model=JobRecord)
    async def get_job(job_id: str) -> JobRecord:
        try:
            return await workflow.store.get(job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc

    @app.post("/v1/jobs/{job_id}/decision", response_model=JobRecord)
    async def decide(job_id: str, submission: DecisionSubmission) -> JobRecord:
        try:
            return await workflow.decide(job_id, submission)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/v1/jobs/{job_id}/evidence.json")
    async def evidence_json(job_id: str) -> Response:
        job = await get_job(job_id)
        if job.report is None:
            raise HTTPException(status_code=409, detail="evidence is not ready")
        return Response(
            content=job.report.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.json"'},
        )

    @app.get("/v1/jobs/{job_id}/evidence.md")
    async def evidence_markdown(job_id: str) -> Response:
        job = await get_job(job_id)
        if job.report is None:
            raise HTTPException(status_code=409, detail="evidence is not ready")
        return Response(
            content=report_to_markdown(job.report),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.md"'},
        )

    return app


app = create_app()
