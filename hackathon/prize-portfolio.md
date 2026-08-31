# Prize portfolio

Target track: **Professional Agents**

Primary target: **Grand Prize — $10,000**
Secondary target: **Professional Agents Golden Agent — $5,000**

## Judge-facing thesis

Paper2Proof is the clearest possible expression of an agent for humans:
researchers should not spend their scarce attention repeatedly converting a
paper claim into an experiment, a run, a comparison, and a research note.
Agents should do that bounded work in the background. Humans should re-enter
only where science, safety, cost, or licensing requires judgment.

Its magic moment is not a generated answer. It is a content-addressed evidence
trail connecting an exact claim, source hash, executable plan, isolated
AgentCore session, observed value, deterministic verdict, limitations, and
human decision.

## Five-criterion proof

### 1. Technical implementation

**5-point evidence**

- Strands Agents is the core workflow, not a decorative dependency.
- Six typed roles emit visible agent/tool lifecycle events.
- Public-paper reasoning uses the pinned Amazon Nova 2 Lite inference profile.
- Production is deployed to private Bedrock AgentCore Runtime.
- Approved code executes through AgentCore Code Interpreter, never the host.
- The public edge returns a durable queued job through SQS FIFO and a
  retry-bounded worker; DynamoDB and versioned S3 preserve state/evidence.
- Deterministic policy owns URL safety, code safety, state transitions, and
  verdict math; explicit approval owns judgment.
- Live PASS, BLOCKED, approval, idempotency, SSRF, and real-arXiv evidence is
  recorded with job/trace/hash identifiers.
- 116 tests, 86.65% branch-aware coverage, 12/12 evaluated fixtures, static
  typing, lint, source scan, dependency audit, alarms, and least-privilege IaC.

**Proof surfaces:** live trace UI, architecture PNG, public IaC, evaluation
JSON, evidence downloads, GitHub Actions.

### 2. Design

**5-point evidence**

- Purpose-built evidence workspace, not a chat transcript.
- One-click controlled demos with obvious PASS, disagreement, and judgment
  paths.
- State rail, decision card, claim, bounded plan, observed evidence, and trace
  share one screen.
- Empty, loading, queued, failure, approval, completed, and downloadable states.
- Same-origin public experience with keyboard skip link, semantic headings,
  live regions, visible focus, and responsive layout.
- Plain-language guardrails make the agent's authority legible.

**Proof surfaces:** real desktop/mobile capture and a first-time judge test.

### 3. Potential impact

**5-point evidence**

- Narrow user: independent researchers, graduate students, computational
  scientists, and small research teams.
- Narrow repeated job: paper → claim → conditions → plan → safe run →
  comparison → evidence note.
- Six workflow roles automate the repetitive path while escalation protects
  scarce expert attention.
- Real controlled PASS completed in 21 seconds end-to-end.
- Local contract evaluation achieved 12/12 expected outcomes, 100% evidence
  completeness, and zero unapproved external writes.
- First-party dogfooding only; no external-user or market-validation claim.

**Why it matters:** evidence gaps make research results expensive to trust,
reuse, review, or build upon. Paper2Proof reduces the clerical gap without
claiming to automate scientific truth.

### 4. Creativity and originality

**5-point evidence**

- The product output is an evidence object, not a paper summary or Q&A answer.
- It combines claim-level provenance, bounded reproduction, deterministic
  comparison, and human judgment in one domain-specific workflow.
- Failure, blocking, and uncertainty are useful structured outcomes.
- Evidence hashes and truth labels prevent local, recorded, and managed runs
  from being conflated.
- The product's authority architecture is visible: models propose; policy and
  humans authorize.

### 5. Presentation

**5-point plan**

- Show the PASS magic moment in the first 60 seconds.
- Spend at least half the video inside the real live application.
- Then show the human gate and unsafe BLOCK without execution.
- Use the architecture diagram only after viewers understand the user value.
- Display measured 12/12 results and one honest limitation.
- Add readable English captions; target 3:50–4:10, safely below five minutes.

## Tie-break advantage

Technical Implementation is the first tie-break. The final presentation must
name and visibly prove **Strands Agents**, **AgentCore Runtime**, **AgentCore
Code Interpreter**, typed state, SQS durability, deterministic gates, and live
evidence before aesthetic details.

## Claims we will not make

- “Paper2Proof proves papers true.”
- “Any paper is reproducible automatically.”
- “Production-ready for private data.”
- “Validated by external researchers.”
- “Zero cost” or an exact managed per-job cost without billing evidence.
- “Digitally signed evidence” when the implemented property is SHA-256 content
  addressing and private S3 version history.
