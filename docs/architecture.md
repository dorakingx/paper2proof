# Architecture

Paper2Proof separates the anonymous public edge, durable orchestration, private
agent reasoning, bounded execution, and evidence storage. This keeps model
output advisory while deterministic policy controls every consequential edge.

![Paper2Proof AWS architecture](architecture.png)

The diagram source is [`architecture.svg`](architecture.svg). The submitted
PNG is 2400×1350 so it remains readable in Devpost's image viewer.

## Request and execution flow

1. The browser sends a typed `JobRequest` to the same-origin Lambda Function
   URL. The edge enforces a 32 KiB body limit and an hourly, hashed-IP rate
   limit in DynamoDB.
2. The public Lambda invokes the IAM-protected AgentCore Runtime with `create`.
   The Runtime validates the request, creates an idempotent `QUEUED` record,
   and returns quickly.
3. Lambda writes only the opaque job ID to an encrypted SQS FIFO queue. The
   browser receives `202 Accepted` and polls its unguessable job URL.
4. A concurrency-bounded Lambda worker consumes one job at a time and invokes
   `run_job` on the private Runtime. Failed messages receive three bounded
   attempts before the encrypted DLQ; CloudWatch alarms on any DLQ message.
5. Inside Runtime, the workflow selects deterministic fixture contracts for
   transparent demos or Strands agents backed by Amazon Nova 2 Lite for public
   papers. Every role emits typed trace events.
6. Deterministic URL, license, code, dependency, time, and write policies gate
   the plan. Ambiguity creates `AWAITING_APPROVAL`; prohibited code creates
   `BLOCKED`. The model cannot grant execution authority.
7. Approved code runs through a Strands tool backed by AgentCore Code
   Interpreter. It never runs in the public Lambda or Runtime host process.
8. Deterministic comparison owns the numerical verdict. The report is
   canonicalized and SHA-256-addressed before its JSON is versioned in private
   S3 and its current state is stored in encrypted DynamoDB.

## Trust boundaries

| Boundary | Allowed | Explicitly disallowed |
|---|---|---|
| Public browser → Lambda | typed same-origin GET/POST, public arXiv/GitHub input | credentials, arbitrary proxying, job enumeration |
| Lambda → Runtime | exact Runtime and `DEFAULT` endpoint invoke | Bedrock model access, DynamoDB job reads, S3 evidence access |
| Worker → Runtime | exact Runtime invoke for queued IDs | direct state/evidence mutation |
| Runtime → Bedrock | pinned Nova 2 Lite model/profile | wildcard model invocation |
| Runtime → Code Interpreter | managed `aws.codeinterpreter.v1` session actions | host shell or Docker in production |
| Runtime → data | exact DynamoDB table; `evidence/*` S3 writes | public buckets, broad S3 access |

## Data and durability

- Job IDs and trace IDs contain 128 bits of random entropy.
- Idempotency keys prevent duplicate work; the queue uses job ID as FIFO
  deduplication identity.
- DynamoDB uses on-demand capacity, server-side encryption, point-in-time
  recovery, TTL, and deletion protection.
- Evidence S3 uses server-side encryption, versioning, public-access blocks,
  bucket-owner enforcement, and a TLS-only bucket policy.
- AgentCore Runtime sessions idle out after 300 seconds and have a 900-second
  maximum lifetime. Public code execution is independently budgeted to at most
  90 seconds by default and 300 seconds by schema.
- CloudWatch retains API and worker logs for 30 days. AgentCore OpenTelemetry
  emits runtime traces to CloudWatch/X-Ray.

## Why two execution paths exist

Controlled fixtures are deterministic role contracts. They make PASS,
MISMATCH, BLOCKED, injection, missing-dependency, and approval behavior stable
and auditable. Public papers use Strands + Nova for genuine extraction and
planning. Both paths pass through the same state machine, policy gates,
evidence schema, and production AgentCore execution adapter.

Local development may substitute a hardened Docker executor, always labeled
`docker-local`. Production evidence is labeled `agentcore-live`; the schema
prevents one from being represented as the other.

## Failure semantics

Failure is a first-class result. Validation rejects malformed input. Unsafe
plans stop before execution. Ambiguity pauses with explicit options. Runtime
errors become bounded public messages while full details stay in logs. Worker
timeouts do not silently acknowledge the SQS message. Evidence downloads are
available only once a report exists.

Known limitation: the hackathon demo is anonymous and has no user identity or
per-user deletion token. It therefore accepts only public sources, never paper
uploads or secrets, exposes no job-list endpoint, and uses unguessable job IDs.
A production multi-tenant version should add authentication, ownership checks,
and an owner-authorized deletion workflow.
