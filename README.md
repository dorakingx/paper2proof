# Paper2Proof

> From computational papers to reproducible evidence, without the busywork.

Paper2Proof is an autonomous research reproducibility steward for independent
computational researchers and small teams. It turns a bounded numerical claim
from a public paper into an executable reproduction plan, runs that plan in an
isolated Amazon Bedrock AgentCore Code Interpreter session, compares the
reported and observed values, and returns an auditable claim-to-evidence
bundle. It only interrupts a researcher when scientific judgment or explicit
approval is genuinely required.

Paper2Proof is built around a deterministic six-role **Strands Agents**
workflow rather than a chat interface. Amazon Bedrock AgentCore Runtime hosts
the agent service; AgentCore Code Interpreter supplies the sandbox boundary.

> Build status: active hackathon implementation. Public URLs and measured
> evaluation results are added only after they have been verified.

## Why an agent, not a chatbot

A user supplies a public source and an optional public repository once. The
service continues server-side through intake, claim extraction, planning,
bounded execution, verification, and evidence packaging. Each transition is
persisted, every tool call is traceable, and ambiguous or risky work is routed
to a decision center instead of being guessed.

## Workflow

`QUEUED → INTAKE → CLAIMS_EXTRACTED → PLAN_READY → EXECUTING → VERIFYING → COMPLETED`

Unsafe, ambiguous, expensive, licensed-unclear, or externally mutating plans
branch to `AWAITING_APPROVAL`, `BLOCKED`, or `PARTIAL` with a structured reason.

## Current stack

- Strands Agents SDK 1.54.0 with structured Pydantic outputs and lifecycle hooks
- Amazon Bedrock with `global.anthropic.claude-sonnet-4-6`
- Amazon Bedrock AgentCore Runtime and Code Interpreter
- FastAPI agent API; React/Vite web experience
- DynamoDB job state, S3 evidence bundles, SQS background dispatch
- CloudWatch Logs, metrics, and OpenTelemetry traces

## Development

Prerequisites: Python 3.13, `uv`, Node.js 20+, Docker for the documented local
sandbox fallback, and AWS credentials for live AgentCore integration tests.

```bash
uv sync --all-groups
uv run pytest
uv run paper2proof run-fixture reproducible-mean
```

The fixture mode never presents cached or synthetic output as an AgentCore
result. Runtime provenance is included in every evidence report.

## Disclosure

This project was created from a blank repository on 2026-08-31 during the
Agents for Humans Hackathon submission period. It uses open-source frameworks
and libraries but no pre-existing Paper2Proof code. OpenAI Codex was used as a
development assistant. Full disclosures are in [docs/disclosures.md](docs/disclosures.md).

## License

MIT. See [LICENSE](LICENSE).
