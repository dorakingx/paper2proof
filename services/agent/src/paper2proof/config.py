"""Typed configuration with safe, reviewable defaults."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PAPER2PROOF_",
        env_file=".env",
        extra="ignore",
    )

    runtime_mode: str = "fixture"
    store_mode: str = "memory"
    archive_mode: str = "none"
    aws_region: str = "us-west-2"
    bedrock_model_id: str = "global.amazon.nova-2-lite-v1:0"
    job_table: str = "paper2proof-jobs"
    evidence_bucket: str = ""
    queue_url: str = ""
    agent_runtime_arn: str = ""
    inline_jobs: bool = False
    cors_origins: str = "http://localhost:5173"
    max_source_bytes: int = Field(default=5_000_000, ge=1_000, le=20_000_000)
    execution_timeout_seconds: int = Field(default=90, ge=1, le=300)
    max_output_bytes: int = Field(default=1_000_000, ge=1_000, le=5_000_000)
    max_api_body_bytes: int = Field(default=32_768, ge=1_024, le=1_000_000)
    public_rate_limit_per_hour: int = Field(default=0, ge=0, le=1_000)
    docker_image: str = (
        "python@sha256:7ce4b6dfe35e55397b7cda544f8a13f191b7ae28dc5aad71fe664dbc9bc2623f"
    )
    allowed_source_hosts: str = (
        "arxiv.org,export.arxiv.org,github.com,raw.githubusercontent.com,paper2proof.dev"
    )

    @field_validator("runtime_mode")
    @classmethod
    def validate_runtime_mode(cls, value: str) -> str:
        allowed = {"fixture", "docker", "bedrock", "agentcore"}
        if value not in allowed:
            raise ValueError(f"runtime_mode must be one of {sorted(allowed)}")
        return value

    @field_validator("store_mode")
    @classmethod
    def validate_store_mode(cls, value: str) -> str:
        if value not in {"memory", "dynamodb"}:
            raise ValueError("store_mode must be memory or dynamodb")
        return value

    @field_validator("archive_mode")
    @classmethod
    def validate_archive_mode(cls, value: str) -> str:
        if value not in {"none", "s3"}:
            raise ValueError("archive_mode must be none or s3")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def source_host_allowlist(self) -> frozenset[str]:
        return frozenset(
            item.strip().lower() for item in self.allowed_source_hosts.split(",") if item.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
