"""Auditable domain contracts for Paper2Proof."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    INTAKE = "INTAKE"
    CLAIMS_EXTRACTED = "CLAIMS_EXTRACTED"
    PLAN_READY = "PLAN_READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


TERMINAL_STATUSES = {
    JobStatus.COMPLETED,
    JobStatus.PARTIAL,
    JobStatus.BLOCKED,
    JobStatus.FAILED,
}

ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.INTAKE, JobStatus.FAILED}),
    JobStatus.INTAKE: frozenset(
        {
            JobStatus.CLAIMS_EXTRACTED,
            JobStatus.AWAITING_APPROVAL,
            JobStatus.BLOCKED,
            JobStatus.FAILED,
        }
    ),
    JobStatus.CLAIMS_EXTRACTED: frozenset(
        {JobStatus.PLAN_READY, JobStatus.AWAITING_APPROVAL, JobStatus.BLOCKED, JobStatus.FAILED}
    ),
    JobStatus.PLAN_READY: frozenset(
        {JobStatus.EXECUTING, JobStatus.AWAITING_APPROVAL, JobStatus.BLOCKED, JobStatus.FAILED}
    ),
    JobStatus.AWAITING_APPROVAL: frozenset(
        {JobStatus.PLAN_READY, JobStatus.EXECUTING, JobStatus.BLOCKED, JobStatus.FAILED}
    ),
    JobStatus.EXECUTING: frozenset(
        {JobStatus.VERIFYING, JobStatus.PARTIAL, JobStatus.BLOCKED, JobStatus.FAILED}
    ),
    JobStatus.VERIFYING: frozenset(
        {JobStatus.COMPLETED, JobStatus.PARTIAL, JobStatus.BLOCKED, JobStatus.FAILED}
    ),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.PARTIAL: frozenset(),
    JobStatus.BLOCKED: frozenset(),
    JobStatus.FAILED: frozenset(),
}


def assert_transition(current: JobStatus, target: JobStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"invalid job transition: {current} -> {target}")


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    PROHIBITED = "PROHIBITED"


class Verdict(StrEnum):
    PASS = "PASS"  # nosec B105  # noqa: S105 - scientific verdict, not a password
    PARTIAL = "PARTIAL"
    MISMATCH = "MISMATCH"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"


class ExecutionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    BLOCKED = "BLOCKED"


class RuntimeProvenance(StrEnum):
    AGENTCORE_LIVE = "agentcore-live"
    DOCKER_LOCAL = "docker-local"
    RECORDED = "recorded"
    FIXTURE_NO_EXEC = "fixture-no-exec"


class TraceEventType(StrEnum):
    STATE = "state"
    AGENT_START = "agent-start"
    AGENT_OUTPUT = "agent-output"
    TOOL_START = "tool-start"
    TOOL_OUTPUT = "tool-output"
    GUARDRAIL = "guardrail"
    ERROR = "error"


class SourceReference(StrictModel):
    url: AnyHttpUrl
    title: NonEmpty
    license: NonEmpty
    locator: NonEmpty
    excerpt: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000)
    ]
    content_sha256: Sha256


class Tolerance(StrictModel):
    absolute: float | None = Field(default=None, gt=0)
    relative: float | None = Field(default=None, gt=0, le=1)

    @model_validator(mode="after")
    def require_one_tolerance(self) -> Tolerance:
        if self.absolute is None and self.relative is None:
            raise ValueError("at least one tolerance is required")
        return self


class Claim(StrictModel):
    claim_id: Annotated[str, StringConstraints(pattern=r"^claim_[a-z0-9_]{3,64}$")]
    statement: NonEmpty
    reported_value: float
    unit: NonEmpty
    tolerance: Tolerance
    conditions: list[NonEmpty] = Field(min_length=1, max_length=20)
    source: SourceReference
    ambiguity: list[NonEmpty] = Field(default_factory=list, max_length=10)

    @field_validator("reported_value")
    @classmethod
    def reported_value_is_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("reported value must be finite")
        return value


class ClaimExtraction(StrictModel):
    claims: list[Claim] = Field(min_length=1, max_length=5)
    selected_claim_id: NonEmpty
    needs_human_judgment: bool = False
    judgment_reason: str | None = None

    @model_validator(mode="after")
    def selected_claim_exists(self) -> ClaimExtraction:
        ids = {claim.claim_id for claim in self.claims}
        if self.selected_claim_id not in ids:
            raise ValueError("selected_claim_id must reference a claim")
        if self.needs_human_judgment and not self.judgment_reason:
            raise ValueError("judgment_reason is required when human judgment is needed")
        return self

    @property
    def selected_claim(self) -> Claim:
        return next(claim for claim in self.claims if claim.claim_id == self.selected_claim_id)


class IntakeAssessment(StrictModel):
    accepted: bool
    normalized_source_url: AnyHttpUrl
    normalized_repo_url: AnyHttpUrl | None = None
    source_host: NonEmpty
    source_license: NonEmpty
    risk_level: RiskLevel
    risks: list[NonEmpty] = Field(default_factory=list, max_length=20)
    prompt_injection_detected: bool = False
    requires_approval: bool = False
    decision_reason: str | None = None

    @model_validator(mode="after")
    def decision_is_explained(self) -> IntakeAssessment:
        if (not self.accepted or self.requires_approval) and not self.decision_reason:
            raise ValueError("a rejected or gated intake requires a reason")
        return self


class ExperimentPlan(StrictModel):
    plan_id: Annotated[str, StringConstraints(pattern=r"^plan_[a-z0-9_]{3,64}$")]
    claim_id: NonEmpty
    language: Literal["python"] = "python"
    code: Annotated[str, StringConstraints(min_length=1, max_length=20_000)]
    dependencies: list[NonEmpty] = Field(default_factory=list, max_length=20)
    command_display: NonEmpty
    expected_json_key: Literal["observed"] = "observed"
    expected_artifacts: list[NonEmpty] = Field(default_factory=list, max_length=20)
    success_criteria: list[NonEmpty] = Field(min_length=1, max_length=20)
    timeout_seconds: int = Field(ge=1, le=300)
    network_access: bool = False
    external_writes: bool = False
    estimated_cost_usd: float = Field(ge=0, le=5)
    risk_level: RiskLevel
    requires_approval: bool = False
    approval_reason: str | None = None

    @model_validator(mode="after")
    def gated_plan_is_explained(self) -> ExperimentPlan:
        if self.requires_approval and not self.approval_reason:
            raise ValueError("approval_reason is required for a gated plan")
        return self


class ArtifactRecord(StrictModel):
    name: NonEmpty
    media_type: NonEmpty
    size_bytes: int = Field(ge=0)
    sha256: Sha256


class ExecutionRecord(StrictModel):
    execution_id: Annotated[str, StringConstraints(pattern=r"^exec_[a-z0-9]{8,64}$")]
    status: ExecutionStatus
    provenance: RuntimeProvenance
    service: NonEmpty
    region: str | None = None
    sandbox_identifier: str | None = None
    session_id: str | None = None
    started_at: datetime
    completed_at: datetime
    duration_ms: int = Field(ge=0)
    language: Literal["python"] = "python"
    command_display: NonEmpty
    code_sha256: Sha256
    exit_code: int | None = None
    stdout: Annotated[str, StringConstraints(max_length=1_000_000)] = ""
    stderr: Annotated[str, StringConstraints(max_length=1_000_000)] = ""
    observed_value: float | None = None
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    raw_response_sha256: Sha256
    cache_hit: bool = False
    failure_reason: str | None = None

    @model_validator(mode="after")
    def timestamps_and_failure_are_valid(self) -> ExecutionRecord:
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("execution timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be after started_at")
        if self.status != ExecutionStatus.SUCCESS and not self.failure_reason:
            raise ValueError("failure_reason is required for non-success execution")
        if self.observed_value is not None and not math.isfinite(self.observed_value):
            raise ValueError("observed value must be finite")
        return self


class Comparison(StrictModel):
    reported_value: float
    observed_value: float | None = None
    absolute_error: float | None = Field(default=None, ge=0)
    relative_error: float | None = Field(default=None, ge=0)
    tolerance: Tolerance
    within_tolerance: bool | None = None
    rationale: NonEmpty


class CriticAssessment(StrictModel):
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    rationale: NonEmpty
    limitations: list[NonEmpty] = Field(default_factory=list, max_length=20)
    next_decision: str | None = None


class AgentReview(StrictModel):
    accepted: bool
    findings: list[NonEmpty] = Field(default_factory=list, max_length=20)
    requires_human_judgment: bool = False
    judgment_reason: str | None = None


class ReportNarrative(StrictModel):
    summary: NonEmpty
    limitations: list[NonEmpty] = Field(default_factory=list, max_length=20)
    next_decision: str | None = None


class TraceEvent(StrictModel):
    ordinal: int = Field(ge=1)
    trace_id: Annotated[str, StringConstraints(pattern=r"^trace_[a-f0-9]{16,64}$")]
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: TraceEventType
    role: NonEmpty
    name: NonEmpty
    input_summary: str | None = None
    output_summary: str | None = None


class StatusTransition(StrictModel):
    ordinal: int = Field(ge=1)
    from_status: JobStatus | None
    to_status: JobStatus
    timestamp: datetime = Field(default_factory=utc_now)
    reason: NonEmpty


class DecisionOption(StrictModel):
    option_id: NonEmpty
    label: NonEmpty
    impact: NonEmpty


class DecisionRequest(StrictModel):
    reason: NonEmpty
    options: list[DecisionOption] = Field(min_length=2, max_length=4)
    recommended_option_id: NonEmpty


class EvidenceReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    job_id: Annotated[str, StringConstraints(pattern=r"^job_[a-f0-9]{16,64}$")]
    generated_at: datetime = Field(default_factory=utc_now)
    terminal_status: JobStatus
    claim: Claim
    plan: ExperimentPlan | None = None
    execution: ExecutionRecord | None = None
    comparison: Comparison | None = None
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    limitations: list[NonEmpty] = Field(default_factory=list)
    next_decision: str | None = None
    trace_id: Annotated[str, StringConstraints(pattern=r"^trace_[a-f0-9]{16,64}$")]
    evidence_sha256: Sha256 | None = None

    @model_validator(mode="after")
    def terminal_report_is_coherent(self) -> EvidenceReport:
        if self.terminal_status not in TERMINAL_STATUSES | {JobStatus.AWAITING_APPROVAL}:
            raise ValueError("evidence report requires a terminal or approval status")
        if self.verdict == Verdict.PASS and (
            self.execution is None
            or self.execution.status != ExecutionStatus.SUCCESS
            or self.comparison is None
            or self.comparison.within_tolerance is not True
        ):
            raise ValueError("PASS requires successful execution within tolerance")
        return self


class JobRequest(StrictModel):
    fixture_id: str | None = None
    paper_url: AnyHttpUrl | None = None
    repo_url: AnyHttpUrl | None = None
    claim_hint: str | None = Field(default=None, max_length=500)
    execution_budget_seconds: int = Field(default=90, ge=1, le=300)
    idempotency_key: Annotated[str, StringConstraints(min_length=8, max_length=128)]

    @model_validator(mode="after")
    def one_source_is_required(self) -> JobRequest:
        if bool(self.fixture_id) == bool(self.paper_url):
            raise ValueError("provide exactly one of fixture_id or paper_url")
        return self


class JobRecord(StrictModel):
    job_id: Annotated[str, StringConstraints(pattern=r"^job_[a-f0-9]{16,64}$")]
    trace_id: Annotated[str, StringConstraints(pattern=r"^trace_[a-f0-9]{16,64}$")]
    request: JobRequest
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    transitions: list[StatusTransition] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    intake: IntakeAssessment | None = None
    claim_extraction: ClaimExtraction | None = None
    plan: ExperimentPlan | None = None
    execution: ExecutionRecord | None = None
    report: EvidenceReport | None = None
    decision: DecisionRequest | None = None
    error_code: str | None = None
    error_message: str | None = None


class DecisionSubmission(StrictModel):
    option_id: Literal["approve", "reject", "modify"]
    note: str | None = Field(default=None, max_length=1_000)
