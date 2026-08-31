# Agents for Humans: Building a durable Strands workflow on Amazon Bedrock AgentCore

An agent that completes real work has different infrastructure needs from a
chat request. The browser may close. Model reasoning may take tens of seconds.
Execution needs an isolation boundary. Retries must not duplicate work.
Evidence must outlive the session.

Paper2Proof is a claim-to-evidence reproducibility workflow built with Strands
Agents and deployed to Amazon Bedrock AgentCore Runtime. This post walks through
the architecture choices that make its public demo durable and auditable.

## Fast public edge, private agent plane

The same-origin web application and typed FastAPI surface run on AWS Lambda
Function URL. A POST is limited to 32 KiB and rate-limited in DynamoDB. The
public role can invoke one exact AgentCore Runtime endpoint, increment only
rate-limit keys, and send to one exact queue. It cannot invoke Bedrock models,
read arbitrary jobs, or access evidence storage.

On job creation, the private Runtime validates the request and writes an
idempotent QUEUED record to DynamoDB. The public Lambda places only the opaque
job ID in encrypted SQS FIFO and returns 202 Accepted. A concurrency-bounded
Lambda worker consumes one message at a time and invokes run_job on AgentCore
Runtime.

If processing fails, SQS retries at most three times before moving the message
to an encrypted dead-letter queue. CloudWatch alarms on any visible DLQ message.
The browser polls its random 128-bit job ID; there is no public list endpoint.

## Strands for reasoning, code for authority

Inside AgentCore Runtime, six specialized roles handle Intake & Risk, Claim
Extraction, Reproduction Planning, Execution, Verification & Critique, and
Report & Action. Public-paper roles use Amazon Nova 2 Lite with Pydantic
structured outputs. Strands lifecycle and tool hooks become typed trace events
shown in the UI.

Generated plans do not execute directly. Deterministic policy checks URL
provenance, license signals, dependencies, forbidden imports and calls,
network/write requirements, duration, and cost. Ambiguity becomes a recorded
human decision. Prohibited code becomes BLOCKED.

Approved code is passed to a Strands tool backed by AgentCore Code Interpreter.
The public Lambda and Runtime host never run generated code. The execution
record includes AgentCore provenance, session ID, timing, stdout-equivalent
output, and hashes.

## Durable evidence

DynamoDB stores current job state and idempotency records with on-demand
capacity, encryption, point-in-time recovery, TTL, and deletion protection.
The final report is canonically serialized, SHA-256-addressed, and written to a
private, encrypted, versioned S3 evidence prefix. A TLS-only bucket policy and
public-access blocks are infrastructure as code.

An idempotency replay of the managed golden fixture returned the same job,
session, evidence hash, and single S3 archive instead of executing twice.

## What changed after a real failure

The first managed design kept execution inside a synchronous public request.
A client timeout left one historical job nonterminal. The fix was architectural,
not cosmetic: create first, persist, dispatch through SQS, and let an independent
worker own execution. The final public POST returns in roughly 5–8 seconds while
the managed workflow continues.

That lesson is broadly applicable to agents: if work matters, its lifecycle
cannot depend on a browser connection.

- Architecture and IaC: https://github.com/dorakingx/paper2proof
- Live service: https://ptvrh62d34oqwkz4x6cjtbvxgm0yaimi.lambda-url.us-west-2.on.aws/
