"""FastAPI surface for background jobs and downloadable evidence."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from paper2proof.agentcore_client import AgentCoreRuntimeClient, AgentRuntimeError
from paper2proof.config import Settings, get_settings
from paper2proof.fixtures import list_fixtures, load_fixture
from paper2proof.queue import JobDispatcher, SQSJobDispatcher
from paper2proof.rate_limit import (
    DynamoDBHourlyRateLimiter,
    RateLimiter,
    RateLimitExceeded,
    RateLimitResult,
)
from paper2proof.reporting import report_to_markdown
from paper2proof.schemas import DecisionSubmission, JobRecord, JobRequest, JobStatus

if TYPE_CHECKING:
    from paper2proof.workflow import Paper2ProofWorkflow

WEB_ROOT = Path(__file__).with_name("web")
LOGGER = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    rate_limiter: RateLimiter | None = None,
    job_dispatcher: JobDispatcher | None = None,
) -> FastAPI:
    selected_settings = settings or get_settings()
    workflow: Paper2ProofWorkflow | None = None
    runtime_client: AgentCoreRuntimeClient | None = None
    local_not_found: type[Exception] = KeyError
    if selected_settings.agent_runtime_arn:
        runtime_client = AgentCoreRuntimeClient(
            runtime_arn=selected_settings.agent_runtime_arn,
            region=selected_settings.aws_region,
        )
    else:
        # Keep the public Lambda package small: local agent, sandbox, and storage
        # dependencies are loaded only for development or the private Runtime.
        from paper2proof.factory import build_workflow
        from paper2proof.store import JobNotFoundError

        workflow = build_workflow(selected_settings)
        local_not_found = JobNotFoundError
    active_rate_limiter = rate_limiter
    if (
        active_rate_limiter is None
        and selected_settings.agent_runtime_arn
        and selected_settings.public_rate_limit_per_hour > 0
    ):
        active_rate_limiter = DynamoDBHourlyRateLimiter(
            table_name=selected_settings.job_table,
            limit=selected_settings.public_rate_limit_per_hour,
            region=selected_settings.aws_region,
        )
    active_job_dispatcher = job_dispatcher
    if active_job_dispatcher is None and selected_settings.queue_url:
        active_job_dispatcher = SQSJobDispatcher(
            queue_url=selected_settings.queue_url,
            region=selected_settings.aws_region,
        )
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
    app.state.runtime_client = runtime_client
    app.state.job_dispatcher = active_job_dispatcher
    app.state.settings = selected_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=selected_settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rate_result: RateLimitResult | None = None
        response: Response
        if request.method == "POST":
            declared_length = request.headers.get("content-length")
            if declared_length is not None:
                try:
                    declared_bytes = int(declared_length)
                except ValueError:
                    declared_bytes = selected_settings.max_api_body_bytes + 1
                if declared_bytes > selected_settings.max_api_body_bytes:
                    response = JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={"detail": "Request body exceeds the public API limit."},
                    )
                else:
                    response = await _guarded_response(request, call_next)
                    rate_result = getattr(request.state, "rate_limit_result", None)
            else:
                response = await _guarded_response(request, call_next)
                rate_result = getattr(request.state, "rate_limit_result", None)
        else:
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
            "form-action 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; font-src 'self'"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if rate_result is not None:
            response.headers["X-RateLimit-Limit"] = str(rate_result.limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_result.remaining)
        if request.url.path == "/health" or request.url.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store"
        elif request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=300"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response

    async def _guarded_response(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        body = await request.body()
        if len(body) > selected_settings.max_api_body_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "Request body exceeds the public API limit."},
            )
        if active_rate_limiter is None:
            return await call_next(request)
        subject = request.client.host if request.client is not None else "unknown"
        try:
            request.state.rate_limit_result = await active_rate_limiter.check(subject)
        except RateLimitExceeded as exc:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Public demo rate limit reached. Try again next hour."},
                headers={"Retry-After": str(exc.retry_after_seconds)},
            )
        except Exception as exc:
            LOGGER.warning("Rate-limit backend failed (%s)", type(exc).__name__)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Public demo protection is temporarily unavailable."},
            )
        return await call_next(request)

    def local_workflow() -> Paper2ProofWorkflow:
        if workflow is None:
            raise RuntimeError("local workflow is not configured")
        return workflow

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "paper2proof-agent",
            "runtime_mode": selected_settings.runtime_mode,
            "store_mode": selected_settings.store_mode,
            "strands_agents": True,
            "agentcore_code_interpreter": selected_settings.runtime_mode == "agentcore",
            "agentcore_runtime": bool(selected_settings.agent_runtime_arn),
        }

    @app.get("/v1/fixtures")
    async def fixtures() -> list[dict[str, Any]]:
        result = []
        for fixture_id in list_fixtures(public_only=True):
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
        if runtime_client is not None:
            try:
                if active_job_dispatcher is not None:
                    job, created = await runtime_client.create(request)
                    if created or job.status == JobStatus.QUEUED:
                        await active_job_dispatcher.dispatch(job.job_id)
                    response.status_code = (
                        status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK
                    )
                    return job
                job, _created = await runtime_client.run(request)
            except AgentRuntimeError as exc:
                raise runtime_http_error(exc) from exc
            except Exception as exc:
                LOGGER.warning("Background dispatch failed (%s)", type(exc).__name__)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Background execution is temporarily unavailable.",
                ) from exc
            response.status_code = status.HTTP_200_OK
            return job
        selected_workflow = local_workflow()
        job, created = await selected_workflow.create_job(request)
        if created:
            if selected_settings.inline_jobs:
                job = await selected_workflow.run(job.job_id)
                response.status_code = status.HTTP_200_OK
            else:
                task = asyncio.create_task(selected_workflow.run(job.job_id))
                running_tasks.add(task)
                task.add_done_callback(running_tasks.discard)
        else:
            response.status_code = status.HTTP_200_OK
        return job

    @app.get("/v1/jobs/{job_id}", response_model=JobRecord)
    async def get_job(job_id: str) -> JobRecord:
        if runtime_client is not None:
            try:
                return await runtime_client.get(job_id)
            except AgentRuntimeError as exc:
                raise runtime_http_error(exc) from exc
        try:
            return await local_workflow().store.get(job_id)
        except local_not_found as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc

    @app.post("/v1/jobs/{job_id}/decision", response_model=JobRecord)
    async def decide(job_id: str, submission: DecisionSubmission) -> JobRecord:
        if runtime_client is not None:
            try:
                return await runtime_client.decide(job_id, submission)
            except AgentRuntimeError as exc:
                raise runtime_http_error(exc) from exc
        try:
            return await local_workflow().decide(job_id, submission)
        except local_not_found as exc:
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

    @app.get("/", include_in_schema=False)
    async def web_app() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    app.mount("/assets", StaticFiles(directory=WEB_ROOT / "assets"), name="assets")

    return app


def runtime_http_error(error: AgentRuntimeError) -> HTTPException:
    """Map a private Runtime failure to a bounded public API error."""

    return HTTPException(status_code=error.status_code, detail=error.public_message)


app = create_app()
