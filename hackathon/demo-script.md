# Demo script

Target runtime: **3:55**. Hard limit: **5:00**. Language: English. Use burned-in
English captions, 1440p if practical, and browser zoom large enough to read all
job details.

## Capture prerequisites

- Use the public AWS URL in a logged-out browser.
- Preflight health, queue, Runtime, and Code Interpreter.
- Keep one verified completed PASS job available as fallback, visibly labeled
  recorded only if live execution fails.
- Hide bookmarks, personal browser profile, account email, AWS console account
  details, terminal paths, notifications, and secrets.
- Capture real product behavior; do not accelerate status changes deceptively.

## Timeline and narration

### 0:00–0:18 — Cold open / magic moment

**Screen:** Paper2Proof hero, then click Reproducible mean immediately.

**Narration:**
“A paper reports a number. But can you trace that number to an experiment and
an observed result? Paper2Proof turns one computational claim into auditable
evidence—while the researcher keeps authority over scientific judgment.”

### 0:18–0:55 — Real PASS workflow

**Screen:** Queued state, state rail, live trace; scroll to observed evidence
when complete.

**Narration:**
“This is the real public AWS service. The browser receives a durable queued job
and can leave while six specialized Strands roles continue. The plan passes
deterministic safety policy, so approved code runs in Amazon Bedrock AgentCore
Code Interpreter—not on the host. Here, reported five equals observed five,
inside tolerance: PASS.”

**On-screen callouts:** agentcore-live, session ID, 21-second measured example,
evidence SHA-256.

### 0:55–1:20 — Evidence, not an answer

**Screen:** Claim, plan, provenance, trace drawer, download buttons.

**Narration:**
“The output is not a chat answer. It is a claim-to-evidence object: exact
source, conditions, tolerance, code, runtime provenance, transitions, tool
trace, limitations, and a content hash. JSON and Markdown are downloadable.
A PASS covers this claim under these conditions—not the truth of an entire
paper.”

### 1:20–1:50 — Human authority

**Screen:** Run Ambiguous spread; show AWAITING_APPROVAL and reject.

**Narration:**
“When two scientific interpretations are plausible, the agent does not guess.
It pauses with a concrete decision. I reject this plan. Notice that no execution
record exists: human judgment is a workflow boundary, not a disclaimer added
after the fact.”

### 1:50–2:12 — Safety boundary

**Screen:** Show verified unsafe job URL/result or a prepared product capture.

**Narration:**
“A plan importing host-access modules is deterministically BLOCKED before Code
Interpreter. Models can propose; they cannot grant themselves authority.
The same policy rejects SSRF, subprocesses, network access, undeclared
dependencies, writes, and budget overruns.”

### 2:12–2:42 — Real paper

**Screen:** Public arXiv tab, submit https://arxiv.org/abs/1706.03762, then show
verified awaiting-approval result if live planning would exceed timing.

**Narration:**
“On a real paper, Strands agents backed by Amazon Nova extracted the 28.4 BLEU
English-to-German claim from Attention Is All You Need and planned a bounded
experiment. Paper2Proof stopped before execution because source license and
interpretation need review. That is the responsible result.”

### 2:42–3:15 — Architecture

**Screen:** docs/architecture.png; use a slow pan across the top and bottom.

**Narration:**
“A same-origin Lambda edge validates and rate-limits requests. AgentCore
Runtime persists the job, SQS FIFO dispatches it to a retry-bounded worker, and
the private Runtime coordinates Strands, pinned Nova, and Code Interpreter.
DynamoDB stores idempotent state; versioned private S3 stores canonical
evidence. IAM is scoped to exact resources, and a DLQ alarm catches exhausted
retries.”

### 3:15–3:42 — Measured proof

**Screen:** README evaluation table and evals/results.json.

**Narration:**
“Twelve transparent fixtures cover four golden runs, three mismatches, missing
dependencies, unsafe code, prompt injection, and approval. All twelve matched
their expected outcomes. Unsafe plans were blocked before execution, evidence
and schema completeness were one hundred percent, and there were zero
unapproved external writes. Separately, managed PASS, BLOCK, approval, and
real-paper paths were verified end to end.”

### 3:42–3:55 — Close

**Screen:** Product hero and tagline.

**Narration:**
“Paper2Proof does not replace scientific judgment. It removes the busywork
between reading a claim and having evidence worth judging. From computational
papers to reproducible evidence, without the busywork.”

## Edit checklist

- Final duration ≤ 4:20 and never > 5:00.
- First real verdict visible before 1:00.
- At least 2:00 of the final video shows the live product.
- All captions proofread; “AgentCore” and “Strands Agents” spelled correctly.
- No unsupported statement such as “proves the paper,” “signed evidence,”
  “zero cost,” or “validated by researchers.”
- Public visibility and logged-out playback verified.
- Video URL added to README, submission draft, evidence log, and Devpost.
