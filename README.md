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

> Build status: active hackathon implementation. The source is public at
> [github.com/dorakingx/paper2proof](https://github.com/dorakingx/paper2proof).
> Live AWS and web URLs, and measured evaluation results, are added only after
> they have been independently verified.

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

## Implementation status

- [x] Strands Agents SDK 1.54.0 roles, structured Pydantic outputs, and hooks
- [x] Explicit state machine, decision gate, deterministic comparison, and
      downloadable JSON/Markdown evidence
- [x] FastAPI API and three controlled PASS/MISMATCH/INCONCLUSIVE fixtures
- [x] Hardened local Docker fallback with pinned image, disabled network,
      read-only root, dropped capabilities, resource limits, and provenance
- [x] AgentCore Code Interpreter adapter with direct Strands tool calls
- [ ] Verified live Amazon Bedrock and AgentCore execution
- [ ] Durable DynamoDB/S3/SQS state and production AgentCore Runtime
- [ ] Public web experience and CloudWatch/OpenTelemetry observability

## Development

Prerequisites: Python 3.13, `uv`, Node.js 20+, Docker for the documented local
sandbox fallback, and AWS credentials for live AgentCore integration tests.

```bash
uv sync --all-groups
uv run pytest -q --cov=paper2proof --cov-report=term
uv run paper2proof run-fixture reproducible-mean
```

The fixture and local Docker modes never present their output as an AgentCore
result. Runtime provenance is included in every evidence report. The current
contract suite contains 57 tests and enforces at least 85% branch-aware
coverage; the verified local result is 88.29%.

## Disclosure

This project was created from a blank repository on 2026-08-31 during the
Agents for Humans Hackathon submission period. It uses open-source frameworks
and libraries but no pre-existing Paper2Proof code. OpenAI Codex was used as a
development assistant. Full disclosures are in [docs/disclosures.md](docs/disclosures.md).

## License

MIT. See [LICENSE](LICENSE).
