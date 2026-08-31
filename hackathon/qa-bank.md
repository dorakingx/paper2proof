# Judge Q&A bank

## Why does this need agents instead of a script?

Public papers express claims, conditions, caveats, and implementation hints in
unstructured, inconsistent language. Strands roles handle source assessment,
claim extraction, planning, critique, and reporting with typed outputs. A
deterministic workflow still owns transitions, policy, and verdicts. The
agentic portion resolves open-ended interpretation; code owns authority.

## Is this just paper summarization?

No. The terminal artifact is executable evidence: source locator and hash,
numerical claim and tolerance, bounded code, isolated runtime provenance,
observed output, deterministic comparison, limitations, trace, and a human
decision when needed.

## What proves Strands is actually used?

The dependency is pinned, agent definitions and structured schemas are public,
and live real-paper evidence contains role-specific Strands agent-start,
agent-output, tool-start, and tool-output events. AgentCore Code Interpreter is
invoked through a Strands tool.

## What prevents a prompt injection in the paper?

Source content is labeled untrusted data in system prompts and structured
contracts. Deterministic URL/code/dependency policy is outside the model.
The prompt-injection fixture is detected and safely ignored; it passes its
scientific calculation without obeying the embedded instruction.

## Can the model authorize dangerous code?

No. Static policy and schema gates run after planning. Forbidden imports,
dynamic execution, subprocesses, host/file/network access, undeclared
dependencies, writes, and budget breaches block before execution. Approval
cannot make a prohibited plan legal.

## Why is a real paper left in AWAITING_APPROVAL?

That is intentional. The system could extract and plan a bounded claim, but
the source license and interpretation were not safe to infer automatically.
Paper2Proof optimizes for trustworthy work completed, not the number of green
badges.

## Does PASS mean the paper is correct?

No. It means one observed value matched one reported value under the recorded
conditions and tolerance. The report explicitly carries limitations.

## Is the evidence digitally signed?

No. It is canonically serialized and SHA-256 content-addressed, with private
S3 version history. Cryptographic signatures and an independent transparency
log are future work.

## What happens if the browser closes?

The job already exists in DynamoDB and its opaque ID is in SQS FIFO. A
concurrency-bounded worker continues independently. Idempotency prevents
duplicate execution, and exhausted retries go to an alarmed DLQ.

## Why deterministic fixtures and a model path?

Fixtures are transparent contracts that reliably demonstrate every branch and
make regression evaluation meaningful. Public papers genuinely need model
reasoning. Both use the same state machine, policy gates, evidence schema, and
production execution adapter.

## What data can users submit?

Only public supported HTTPS sources or controlled fixture IDs. No uploads,
private repositories, credentials, secrets, or private datasets. The service
is intentionally anonymous and should be treated like a public share-link
workflow.

## Can users delete their data?

Not through this anonymous hackathon demo. Without identity, the service cannot
reliably prove ownership. There is no cross-user list endpoint, job IDs are
128-bit random, and only public material is accepted. An authenticated
production version must add owner-authorized deletion and retention controls.

## What was actually evaluated?

Twelve fresh local Docker contracts passed 12/12 expected outcomes. Four
separate managed AWS scenarios verified PASS, BLOCKED, approval, and real
arXiv planning. This is not represented as a statistically comprehensive
external-user study.

## What did it cost?

The local 12-case evaluation used no AWS and no model tokens. Managed services
are consumption-priced; the Code Interpreter portion of the measured golden
execution has a conservative compute-only upper bound near $0.00017 at maximum
allocation, excluding Runtime and model tokens. This is an estimate, not a bill.
A $25 monthly AWS budget is deployed.

## Biggest limitation?

It handles one bounded, CPU-sized numerical claim from public sources. It does
not yet support private data, arbitrary dependency installation, networked
experiments, GPUs, authenticated collaboration, or universal reproduction.

## Why could this win?

It combines a legible human problem, a visibly non-chat workflow, deep Strands
and AgentCore use, real isolated execution, durable operations, measurable
safety, claim-level evidence, and honest human authority in one compact demo.
