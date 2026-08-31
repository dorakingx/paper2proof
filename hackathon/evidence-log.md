# Evidence log

Last updated: 2026-09-01 JST. This file records observed results only. Planned
work is never represented as a pass.

## Repository and quality

| Evidence | Result | Artifact |
|---|---|---|
| Blank repository created during submission period | PASS | initial Git history, 2026-08-31 |
| Public repository and anonymous license fetch | PASS | https://github.com/dorakingx/paper2proof · MIT detected |
| Python quality gate | PASS | Ruff; strict mypy |
| Unit and contract suite | PASS | 116 tests; 86.65% branch-aware coverage |
| Python source security scan | PASS | Bandit 1.9.4; no findings after documented exclusions |
| Application dependency audit | PASS | pip-audit; no known vulnerabilities |
| AgentCore CDK dependency audit | PASS | npm audit; 0 vulnerabilities |
| Deterministic Lambda package build | PASS | two builds produced byte-identical SHA-256 |
| Architecture diagram | PASS | `docs/architecture.png`, 2400×1350 |
| Public CI on production commit | PASS | https://github.com/dorakingx/paper2proof/actions/runs/33390100698 — quality/contracts, dependency/source security, and secret-history scan all passed |

Two warnings in the test run originate in upstream FastAPI TestClient and
AgentCore SDK deprecation paths; there are no failing tests.

## Versioned evaluation

Generated at `2026-08-31T11:28:14.008893+00:00`:

| Measure | Observed |
|---|---:|
| Expected outcomes | 12 / 12 |
| Unsafe/dependency block before execution | 3 / 3 |
| Prompt-injection fixture detected and safely handled | 1 / 1 |
| Correct human escalation | 1 / 1 |
| Evidence completeness | 100% |
| Schema validation | 100% |
| Safe execution success | 100% |
| Unapproved external writes | 0 |
| Median / p95 local latency | 384 ms / 442 ms |

Artifact: `evals/results.json`. Runtime truth: fresh `docker-local` runs; no
AgentCore execution or model token use is claimed for this suite.

## AWS infrastructure

| Evidence | Result |
|---|---|
| Foundation stack | `paper2proof-foundation` / UPDATE_COMPLETE |
| AgentCore stack | `AgentCore-Paper2Proof-production` / UPDATE_COMPLETE |
| Public application stack | `paper2proof-application` / UPDATE_COMPLETE |
| AgentCore Runtime | `arn:aws:bedrock-agentcore:us-west-2:291877508281:runtime/Paper2Proof_Paper2ProofRuntime-2lOGp4BbiI` / DEFAULT READY |
| Public URL | https://ptvrh62d34oqwkz4x6cjtbvxgm0yaimi.lambda-url.us-west-2.on.aws/ |
| Durable orchestration | encrypted SQS FIFO, Lambda worker, max concurrency 2, 3 attempts, encrypted DLQ alarm |
| Durable data | encrypted/deletion-protected/PITR DynamoDB; encrypted/versioned/private S3 |
| Cost guard | `Paper2Proof-Hackathon-Monthly` / $25 monthly budget |

The final responsive/no-enumeration Lambda artifact has SHA-256
`ca1353b916625a3f2504a913d40a8e06992bee3781f2d70508e22c09e6d76aca`.
Its deployed Lambda `CodeSha256` exactly matches the versioned S3 object's
checksum (`yhNTuRZiWj8lBKkT1AqOBpkr7jeB8tcFCOIsCebXaso=`). The immediately
preceding privacy-hardening artifact was rebuilt twice with byte-identical
SHA-256 `be6fae33d39558827ea078c42c51e39f513dd308e3ea7c110bb10370c02afbf9`.

## Managed end-to-end runs

### Post-hardening golden PASS

- Job: `job_b6269f5a094349e193bc14fdaff7aa0b`
- Result: `COMPLETED / PASS`; reported 5.0, observed 5.0
- Initial POST: `202` in 6.05 seconds; terminal result in 20.11 seconds
- Runtime: `agentcore-live`
- Code Interpreter session: `01M1BTZXNS4NXHHK4SVSW0GW3F`
- Evidence SHA-256:
  `855a456901da02844fc9ce27917e3329fdbbe6df838186635a395b3a88b2ea75`
- Trace events: 22
- Queue and DLQ after completion: empty
- Public `GET /v1/jobs`: 405; Runtime role actions are exactly `GetItem`,
  `PutItem`, and `TransactWriteItems` (no `Scan`)

### Golden PASS

- Job: `job_c18560e7fe264129a99c60199571bad0`
- Trace: `trace_c7a28283712d49279f0060ab9b6aa4d6`
- Result: `COMPLETED / PASS`; reported 5.0, observed 5.0
- Initial POST: `202` in 7.59 seconds; terminal result in 21 seconds
- Runtime: `agentcore-live`
- Code Interpreter session: `01M1BSH53AQ7R9VQQE2TG70T02`
- Evidence SHA-256:
  `3e531b14681239ef4ed418c092e6864b4d68a5103879e947db1b23728c9f508f`
- Idempotency replay: HTTP 200; same job, session, hash, and one S3 archive
- Queue and DLQ after completion: empty

### Unsafe plan

- Job: `job_abbc697556cb4b91b0fa4cfe216f2825`
- Trace: `trace_81b31b9eb6d74018b8194529abbb1098`
- Result: `BLOCKED`; `SecurityViolation: forbidden imports: os`
- Initial POST: `202` in 5.31 seconds; terminal result in 10 seconds
- Execution record: none
- Evidence SHA-256:
  `b996f965f6855f7470f7c12354138456f660a876b12dd09aab71f98e3367f281`

### Human decision

- Job: `job_0c6cc4bd2d294282a99ed7461809428d`
- Trace: `trace_e79d7226bb3c4b9d87be644b91a2b312`
- Result: `AWAITING_APPROVAL / INCONCLUSIVE`, then explicit reject →
  `BLOCKED`
- Execution record: none before or after decision
- Awaiting evidence SHA:
  `da96f9db3cb98b30485db41c01a0131dd63ea41e8e35531db8857f0c0079d93c`
- Rejected evidence SHA:
  `1ed7753f0f59cf1e74838ddda2cd9d14a49cf466af432cf2cad22f93537179ce`
- S3 evidence versions: 2

### Real public paper

- Source: https://arxiv.org/abs/1706.03762 (*Attention Is All You Need*)
- Job: `job_acbce73ded684e228165adf8358740c3`
- Trace: `trace_ccd75bb65ea44183acd57a9a64719f81`
- Result: `AWAITING_APPROVAL / INCONCLUSIVE` in 25 seconds
- Model roles observed: Intake, Claim Extraction, Planner; each emitted
  Strands agent start/output and structured tool events
- Selected claim: reported 28.4 BLEU on WMT 2014 English-to-German, tolerance
  0.1 BLEU
- PDF content SHA-256:
  `bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697`
- Evidence SHA-256:
  `859fa5660afcff51a6a88e7ee089bef3c85e4134437694fa335527a022d09482`
- Execution record: none; the license/interpretation gate remains unapproved

## Negative public API checks

- unknown job: 404;
- evidence before readiness / incompatible decision: 409;
- oversized body: 413;
- invalid payload: 422;
- SSRF input targeting `127.0.0.1`: failed before execution;
- required CSP, HSTS, frame, MIME, referrer, permissions, COOP, and cache
  headers: observed.
- logged-out Chrome desktop 1440×1000 and responsive 500×844 hero views:
  visually inspected; no overflow after the mobile metric fix.

## Public demo video

- URL: https://youtu.be/4YJcxveYEyk
- Channel ID: `UC3xjDoAdqmNA_mUfccK5n2g` (`doraking_en` selection)
- Published: 2026-09-01 JST
- Duration: 261 seconds (4:21), below the five-minute limit
- Visibility and access: public; anonymous HTTP fetch reports
  `playabilityStatus=OK`, `playableInEmbed=true`, and `isPrivate=false`
- Accessibility: English (United States) timed subtitles uploaded from the
  versioned final SRT; custom 16:9 thumbnail uploaded
- Platform checks: copyright and Community Guidelines both reported no issues
- Local final MP4 SHA-256:
  `c6383cc3817f368898f04cf3d1eeec96a9f6ccc590f48c0214bc47cb8c209478`

## AWS Builder Center bonus articles

All three articles were published from the authenticated `dorakingx` Builder
profile on 2026-09-01 JST. Each title contains the exact phrase `Agents for
Humans`; anonymous HTTP requests returned 200 for all three URLs.

| Article | Public URL | Anonymous check |
|---|---|---:|
| Agents for Humans: Turning a paper claim into evidence with Paper2Proof | https://builder.aws.com/content/3IhG4Wzvjq3mT4Z3PybT1TzjYxE/agents-for-humans-turning-a-paper-claim-into-evidence-with-paper2proof | 200 |
| Agents for Humans: A Durable AgentCore Workflow | https://builder.aws.com/content/3IhGUvAhZ6b0S8haL5BEyAMppP0/agents-for-humans-a-durable-agentcore-workflow | 200 |
| Agents for Humans: When Stopping Is Agent Success | https://builder.aws.com/content/3IhGko62tQxPGWDVRSHqefe5tPc/agents-for-humans-when-stopping-is-agent-success | 200 |

The exact AWS Builder ID email was also observed in the authenticated account.
It is intentionally not stored in the public repository and will be entered
directly into Devpost.

## Devpost submission

- Project page: https://devpost.com/software/paper2proof
- Submission manager:
  https://devpost.com/submit-to/30317-agents-for-humans-hackathon/manage/submissions
- Submitted: 2026-09-01 06:13:56 JST
- Immediate confirmation: the public project page displayed
  `Project submitted! Continue to edit your project until the hackathon deadline`.
- Independent confirmation: after a fresh navigation to the submission manager,
  the Paper2Proof card displayed `Submitted`.
- Final public-preview audit: YouTube player, project story, AWS architecture,
  live-demo link, public repository, Built With values, and all three Builder
  article links rendered. The demo, repository, video, and all three Builder
  article URLs returned anonymous HTTP 200 immediately before submission.
- Devpost fields record Individual / Japan, Professional Agents, the exact
  authenticated AWS Builder ID email, public demo and repository, public video,
  architecture PNG, testing instructions, and bonus-content evidence. The email
  remains intentionally absent from this public repository.
