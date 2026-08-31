# Devpost submission draft

All prose below is final-form English. Bracketed fields are blockers and must
not be submitted as literal placeholders.

## Project name

Paper2Proof

## Tagline

From computational papers to reproducible evidence, without the busywork.

## Track

Professional Agents

## Short description

Paper2Proof is an autonomous research reproducibility steward built with
Strands Agents. It turns one numerical claim from a public computational paper
into a bounded experiment, runs approved code in Amazon Bedrock AgentCore Code
Interpreter, compares reported and observed values, and returns an auditable,
content-addressed evidence report. It interrupts the researcher only when
scientific judgment, safety, cost, or licensing genuinely requires a human.

## Inspiration

Independent researchers and small teams repeatedly do the same invisible work
after reading a paper: locate a testable claim, recover its assumptions, map it
to code and data, build an environment, run it, compare the reported value,
classify failures, and record what happened. Paper search and summarization
tools stop too early. The researcher still has a paper, not evidence.

Paper2Proof starts where summarization ends. Its goal is not to decide whether
a paper is “true.” It moves one bounded claim into a state where a human can
see exactly what was tested, what ran, what was observed, and what judgment is
still required.

## What it does

A researcher supplies a public arXiv URL or chooses a transparent controlled
demo. Paper2Proof then:

1. normalizes and risk-assesses the source as untrusted data;
2. extracts a numerical claim with source locator, conditions, unit, and
   tolerance;
3. plans one CPU-sized, networkless reproduction experiment;
4. blocks prohibited code or pauses for human approval when license,
   interpretation, cost, or safety is unclear;
5. executes approved code in an isolated AgentCore Code Interpreter session;
6. compares the reported and observed values with deterministic code; and
7. packages source hashes, plan, runtime provenance, output, transitions,
   trace, limitations, verdict, and next action as downloadable JSON and
   Markdown evidence.

The browser is not holding the job open. It receives `202 Accepted` and polls
a durable SQS-backed workflow. PASS, MISMATCH, BLOCKED, and
AWAITING_APPROVAL are all intentional, inspectable outcomes.

## How we built it

Paper2Proof is a Python 3.13 Strands Agents workflow with six specialized
roles: Intake & Risk, Claim Extraction, Reproduction Planner, Execution,
Verification & Critic, and Report & Action. Public-paper roles use Amazon Nova
2 Lite with Pydantic structured outputs and Strands lifecycle/tool hooks.

The private agent service runs in Amazon Bedrock AgentCore Runtime with
OpenTelemetry. A same-origin FastAPI web app is served by AWS Lambda Function
URL. New jobs are persisted to DynamoDB and dispatched by encrypted SQS FIFO
to a concurrency-bounded Lambda worker. The worker invokes the private
Runtime; approved code is executed only through a Strands tool backed by
AgentCore Code Interpreter. Evidence is canonicalized, SHA-256-addressed, and
versioned in a private S3 bucket.

The model never authorizes itself. Deterministic policy owns SSRF defense,
allowed sources, dependencies, forbidden code, execution budgets, state
transitions, and numerical verdicts. Human approval is explicit and recorded.
IAM policies are scoped to one model/profile, one Code Interpreter ARN, one
Runtime endpoint, one queue, one table, and one S3 prefix.

## Challenges

The hardest problem was making “agentic” compatible with “auditable.” A model
can generate plausible plans, but research evidence cannot depend on invisible
model discretion. We separated proposal from authority: agents produce typed
artifacts, while deterministic guards decide whether a transition or execution
is legal.

A second challenge was durability. A synchronous browser request disconnected
during an early managed run and left a nonterminal record. We changed the
architecture to create the job first, enqueue only its opaque ID, and let a
retry-bounded worker run it. The public request now returns in roughly 5–8
seconds while managed work continues.

A third challenge surfaced through adversarial testing: a dangerous controlled
fixture was initially rewritten by the model into harmless code, which made the
fixture appear to pass rather than proving the guard. No dangerous code ran,
but the test was semantically weak. We fixed the fixture path to use explicit
deterministic contracts, then verified live that `import os` is blocked before
Code Interpreter invocation.

## Accomplishments

- A public, no-sign-in AWS demo backed by AgentCore Runtime and Code
  Interpreter.
- A live controlled PASS completed in 21 seconds with an AgentCore session ID,
  22 trace events, and versioned evidence hash.
- A live unsafe plan blocked before execution.
- A live human-decision path paused and rejected without execution.
- A real arXiv run used three Nova-backed Strands roles to extract and plan a
  28.4 BLEU claim, then correctly stopped for license/interpretation review.
- Idempotent replay returned the same job, session, hash, and one archive.
- A 12-case networkless evaluation passed 12/12 expected outcomes with 100%
  evidence completeness, 100% unsafe block rate, and zero unapproved writes.
- 116 automated tests, 86.65% branch-aware coverage, strict typing, security
  scans, least-privilege infrastructure, encrypted durable storage, alerts,
  and a $25 budget.

## What we learned

Agents become more trustworthy when uncertainty is a product state rather than
an error to hide. `AWAITING_APPROVAL` is often a better scientific outcome
than an impressive-looking run. Likewise, a successful process execution is
not the same as reproducibility, and a claim-level PASS is not proof of an
entire paper.

We also learned that provenance has to be structural. Every execution is
labeled `agentcore-live`, `docker-local`, `recorded`, or
`fixture-no-exec`; the schema makes them difficult to confuse. The evidence
hash is content addressing, not a signature, so the product says exactly that.

## What's next

The hackathon service deliberately accepts public sources only. The next step
is an authenticated, tenant-isolated version with owner-authorized deletion,
configurable retention, private repository/data connectors, and formal
institutional security review. Scientifically, we would add domain-specific
reproduction adapters, richer dataset provenance, repeated-run statistics,
and reviewer/collaborator workflows while keeping deterministic authority and
human judgment at the center.

## Built with

Strands Agents, Amazon Bedrock AgentCore Runtime, AgentCore Code Interpreter,
Amazon Nova 2 Lite, AWS Lambda, Amazon SQS FIFO, Amazon DynamoDB, Amazon S3,
Amazon CloudWatch, AWS X-Ray, FastAPI, Pydantic, Python, TypeScript, AWS CDK,
CloudFormation, pytest, Docker.

## Links

- Live demo: https://ptvrh62d34oqwkz4x6cjtbvxgm0yaimi.lambda-url.us-west-2.on.aws/
- Source: https://github.com/dorakingx/paper2proof
- Architecture: https://github.com/dorakingx/paper2proof/blob/main/docs/architecture.png
- Demo video: https://youtu.be/4YJcxveYEyk
- Builder article 1: **[PUBLIC URL REQUIRED]**
- Builder article 2: **[PUBLIC URL REQUIRED]**
- Builder article 3: **[PUBLIC URL REQUIRED]**

## Required entrant fields

- Submitter type: Individual
- Country of residence: Japan
- AWS Builder ID email: **[READ FROM AUTHENTICATED ACCOUNT; DO NOT GUESS]**
- Repository license: MIT
- Video visibility: Public; embedding enabled; duration ≤ 5:00

## Honest disclosure

Paper2Proof was created from a blank repository during the hackathon submission
period. OpenAI Codex was used as a development assistant. The controlled
fixtures use deterministic role adapters for stable, auditable contracts;
public papers use Strands Agents backed by Amazon Nova. No external-user study
or universal paper-reproducibility claim is made.
