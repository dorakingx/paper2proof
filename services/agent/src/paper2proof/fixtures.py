"""Controlled public fixtures used for reproducible judge and developer runs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field

from paper2proof.schemas import (
    Claim,
    ClaimExtraction,
    ExperimentPlan,
    JobStatus,
    RiskLevel,
    SourceReference,
    StrictModel,
    Tolerance,
    Verdict,
)


class FixtureMetadata(StrictModel):
    fixture_id: str
    title: str
    source_url: AnyHttpUrl
    license: str
    locator: str
    excerpt: str
    reported_value: float
    unit: str
    tolerance_absolute: float = Field(gt=0)
    conditions: list[str]
    ambiguity: list[str]
    requires_approval: bool
    approval_reason: str | None
    risk_level: RiskLevel
    timeout_seconds: int = Field(ge=1, le=60)
    estimated_cost_usd: float = Field(ge=0, le=0.05)
    expected_verdict: Verdict
    expected_status: JobStatus
    evaluation_category: Literal[
        "golden",
        "mismatch",
        "dependency",
        "approval",
        "prompt-injection",
        "unsafe",
    ]
    public_demo: bool = False
    dependencies: list[str] = Field(default_factory=list, max_length=20)
    network_access: bool = False
    external_writes: bool = False
    experiment_file: str


class Fixture:
    def __init__(self, directory: Path, metadata: FixtureMetadata, note: str, code: str) -> None:
        self.directory = directory
        self.metadata = metadata
        self.note = note
        self.code = code

    @property
    def claim_extraction(self) -> ClaimExtraction:
        source = SourceReference(
            url=self.metadata.source_url,
            title=self.metadata.title,
            license=self.metadata.license,
            locator=self.metadata.locator,
            excerpt=self.metadata.excerpt,
            content_sha256=hashlib.sha256(self.note.encode()).hexdigest(),
        )
        claim_id = "claim_" + self.metadata.fixture_id.replace("-", "_")
        claim = Claim(
            claim_id=claim_id,
            statement=self.metadata.excerpt,
            reported_value=self.metadata.reported_value,
            unit=self.metadata.unit,
            tolerance=Tolerance(absolute=self.metadata.tolerance_absolute),
            conditions=self.metadata.conditions,
            source=source,
            ambiguity=self.metadata.ambiguity,
        )
        return ClaimExtraction(
            claims=[claim],
            selected_claim_id=claim_id,
            needs_human_judgment=self.metadata.requires_approval,
            judgment_reason=self.metadata.approval_reason,
        )

    @property
    def plan(self) -> ExperimentPlan:
        claim = self.claim_extraction.selected_claim
        suffix = self.metadata.fixture_id.replace("-", "_")
        return ExperimentPlan(
            plan_id=f"plan_{suffix}",
            claim_id=claim.claim_id,
            code=self.code,
            dependencies=self.metadata.dependencies,
            command_display="python -I - < approved_experiment.py",
            expected_artifacts=[],
            success_criteria=[
                "Sandbox exits successfully",
                "stdout contains PAPER2PROOF_RESULT with a finite observed number",
                "Observed value is compared with the declared tolerance",
            ],
            timeout_seconds=self.metadata.timeout_seconds,
            network_access=self.metadata.network_access,
            external_writes=self.metadata.external_writes,
            estimated_cost_usd=self.metadata.estimated_cost_usd,
            risk_level=self.metadata.risk_level,
            requires_approval=self.metadata.requires_approval,
            approval_reason=self.metadata.approval_reason,
        )


def repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "fixtures").is_dir():
            return parent
    raise RuntimeError("controlled fixture directory is missing from the application package")


def list_fixtures(*, public_only: bool = False) -> list[str]:
    root = repository_root() / "fixtures"
    fixture_ids = sorted(path.name for path in root.iterdir() if (path / "fixture.json").is_file())
    if not public_only:
        return fixture_ids
    return [
        fixture_id for fixture_id in fixture_ids if load_fixture(fixture_id).metadata.public_demo
    ]


def load_fixture(fixture_id: str) -> Fixture:
    if not fixture_id or "/" in fixture_id or ".." in fixture_id:
        raise KeyError("invalid fixture identifier")
    directory = repository_root() / "fixtures" / fixture_id
    metadata_path = directory / "fixture.json"
    if not metadata_path.is_file():
        raise KeyError(f"unknown fixture: {fixture_id}")
    metadata = FixtureMetadata.model_validate_json(metadata_path.read_text())
    if metadata.fixture_id != fixture_id:
        raise ValueError("fixture directory and metadata identifier differ")
    note = (directory / "note.md").read_text()
    code = (directory / metadata.experiment_file).read_text()
    return Fixture(directory, metadata, note, code)
