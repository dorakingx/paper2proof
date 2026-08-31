# Evaluation

Paper2Proof reports local contract evaluation and managed AWS evidence
separately. The distinction is part of the product contract: `docker-local`
can never be presented as `agentcore-live`.

## Versioned 12-case contract suite

[`evals/results.json`](../evals/results.json) was generated on 2026-08-31 by
[`scripts/run-evaluation.py`](../scripts/run-evaluation.py). Each executable
case was a fresh run in a digest-pinned, networkless Docker sandbox.

| Category | Cases | Expected behavior | Result |
|---|---:|---|---:|
| Golden | 4 | successful execution and PASS | 4/4 |
| Mismatch | 3 | successful execution and MISMATCH | 3/3 |
| Missing dependency | 2 | blocked before execution | 2/2 |
| Unsafe code | 1 | blocked before execution | 1/1 |
| Prompt injection | 1 | detect untrusted instruction; continue safely | 1/1 |
| Human approval | 1 | pause without execution | 1/1 |

Aggregate measured results:

- expected outcomes: **12/12 (100%)**;
- schema validation and evidence completeness: **100%**;
- safe executable-case success: **100%**;
- unsafe/dependency block-before-execution rate: **100%**;
- prompt-injection handling: **100%**;
- correct escalation: **100%**;
- unapproved external writes: **0**;
- latency: min 1 ms, median 384 ms, p95 442 ms, max 665 ms.

The controlled fixtures use deterministic role adapters, so model token usage
for this suite is exactly zero. Actual AWS cost for this local suite is $0.
The sum of fixture-declared managed-run budgets is $0.012; that value is a
policy ceiling declaration, not a cloud bill.

## Managed AWS evidence

These checks were made against the public Lambda → SQS → worker → AgentCore
Runtime path in `us-west-2`:

| Scenario | Job | Stable result | Observed wall time |
|---|---|---|---:|
| Controlled golden | `job_c18560e7fe264129a99c60199571bad0` | COMPLETED / PASS / observed 5.0 | 21 s |
| Unsafe host access | `job_abbc697556cb4b91b0fa4cfe216f2825` | BLOCKED before execution | 10 s |
| Approval + reject | `job_0c6cc4bd2d294282a99ed7461809428d` | AWAITING_APPROVAL → BLOCKED, no execution | 11 s + decision |
| Real arXiv paper | `job_acbce73ded684e228165adf8358740c3` | AWAITING_APPROVAL after three Nova-backed roles | 25 s |

The golden run used AgentCore Code Interpreter session
`01M1BSH53AQ7R9VQQE2TG70T02` and produced evidence SHA-256
`3e531b14681239ef4ed418c092e6864b4d68a5103879e947db1b23728c9f508f`.
Submitting the same idempotency key returned the same job, session, hash, and
single S3 archive rather than executing twice.

The real-paper run fetched *Attention Is All You Need* from arXiv, recorded
PDF content hash
`bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697`,
and extracted the reported 28.4 BLEU WMT 2014 English-to-German claim. It did
not execute because source license and scientific interpretation require a
human decision. That pause is the intended safe result.

## Cost interpretation

AgentCore Runtime and Code Interpreter are consumption-priced, while Lambda
and SQS have request/compute free tiers. Exact per-job model and Runtime billing
is not inferred from wall-clock time. Using the published Code Interpreter
rates and the maximum 2 vCPU / 8 GB allocation, a 2.33-second controlled
execution has a conservative compute-only upper bound of about **$0.00017**,
excluding Runtime and model tokens. This is an engineering estimate, not an
AWS invoice. The deployed account also has a $25 monthly budget.

Official pricing references:

- https://aws.amazon.com/bedrock/agentcore/pricing/
- https://aws.amazon.com/bedrock/pricing/
- https://aws.amazon.com/lambda/pricing/
- https://aws.amazon.com/sqs/pricing/

## Reproduce locally

```bash
uv sync --frozen --all-groups
uv run python scripts/run-evaluation.py
```

Latency depends on local Docker warm state and hardware, so regenerating the
file is expected to change timestamps and timings. Semantic assertions should
remain 12/12.

## What this evaluation does not prove

- It does not establish that every computational paper is reproducible.
- It does not measure statistical correctness beyond the bounded fixture
  contracts.
- It does not benchmark model quality across domains, languages, or PDFs.
- It does not test private data, GPUs, arbitrary dependencies, or networked
  experiments; those are intentionally outside the hackathon service boundary.
- Four managed AWS scenarios are strong end-to-end evidence, not a statistically
  representative production reliability study.
