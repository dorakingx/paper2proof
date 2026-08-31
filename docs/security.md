# Security and responsible-agent design

## Security objective

Paper2Proof handles untrusted public research text and model-generated plans.
Its primary safety property is: **no model output can authorize code execution
or an external write**. Execution authority belongs to deterministic policy
and, when needed, an explicit human decision.

## Controls

### Input and network

- Only `https` public URLs on a fixed host allowlist are accepted.
- DNS resolution and redirects are revalidated to reject loopback, link-local,
  private, multicast, reserved, and unspecified addresses (SSRF defense).
- Response size is capped at 5 MB by default; API request bodies are capped at
  32 KiB.
- Public papers and repositories are treated as untrusted data. Prompt-like
  instructions inside them are traceable risk signals, not commands.
- Production execution plans declare `network_required=false`; execution has
  no authority to mutate an external system.

### Code and decision policy

- Static policy rejects forbidden imports, dynamic execution, subprocesses,
  host/file access, network access, undeclared dependencies, and writes.
- Plan duration and estimated cost are bounded by typed schemas.
- License ambiguity and scientific ambiguity stop at `AWAITING_APPROVAL`.
- Dangerous plans stop at `BLOCKED`; approval cannot override a prohibited
  operation.
- Deterministic comparison owns PASS/MISMATCH/PARTIAL/BLOCKED verdicts.

### Isolation and least privilege

- Production code runs only in AgentCore Code Interpreter through a Strands
  tool. The Runtime process never calls a host shell for generated code.
- The Runtime role can invoke only Nova 2 Lite, the exact Code Interpreter
  managed ARN, one DynamoDB table, and the `evidence/*` S3 prefix.
- The public Lambda role can invoke only the exact Runtime, increment rate
  counters with `RATE#*` leading keys, and send to the exact SQS queue.
- The worker can consume only that queue and invoke only that Runtime.
- S3 and DynamoDB encryption, S3 public-access blocks, TLS-only bucket policy,
  versioning, point-in-time recovery, deletion protection, retention, and
  CloudWatch alarms are infrastructure as code.

### Public surface

- Same-origin UI/API; production CORS allowlist is empty.
- No endpoint enumerates jobs. Fetches require a random 128-bit job ID.
- DynamoDB-backed rate limit: 30 POST requests per hashed source IP per hour.
- Security headers include a restrictive CSP, HSTS, frame denial, MIME
  sniffing denial, no-referrer, permissions policy, and COOP.
- Public errors omit internal exception strings and AWS details.

## Evidence integrity

Each report includes source content hash, claim and plan, runtime provenance,
session ID, timestamps, transitions, trace events, observed output, limitations,
and a SHA-256 identifier computed from canonical report content. Evidence JSON
is versioned privately in S3. This is content addressing, not a digital
signature; the UI and docs intentionally do not call it signed evidence.

## Verification performed

- 116 unit/contract tests with 86.65% branch-aware coverage.
- Ruff and strict mypy pass.
- Bandit 1.9.4 reports no findings under documented container-specific
  exclusions.
- `pip-audit` reports no known vulnerabilities in the exported application
  requirements.
- The AgentCore CDK package reports zero npm audit vulnerabilities.
- Live negative tests verified 404, 409, 413, and 422 behavior.
- A live SSRF attempt against `127.0.0.1` failed before execution.
- A live `import os` plan was blocked before Code Interpreter invocation.

See [`hackathon/evidence-log.md`](../hackathon/evidence-log.md) for identifiers
and timestamps and [`docs/evaluation.md`](evaluation.md) for scope.

## Privacy and limitations

The public hackathon service intentionally accepts public links only: no file
uploads, private repositories, credentials, personal datasets, or secrets. It
has no accounts and no cross-user job listing. Anyone possessing a job URL can
read that job, so users should treat it as a share link and submit no sensitive
material.

The evidence buckets are retained to preserve judging availability. The demo
does not yet expose owner-authenticated deletion because it cannot reliably
establish ownership without authentication. A production release must add
identity, authorization, tenant-scoped keys, deletion/export workflows,
customer-managed retention, KMS keys where required, WAF controls, and a
formal threat-model review.

To report a vulnerability, do not open a public exploit report containing
sensitive details. Use GitHub's private security advisory flow for the
repository owner.
