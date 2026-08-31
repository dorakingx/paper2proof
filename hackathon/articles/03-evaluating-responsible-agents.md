# Agents for Humans: Evaluating a research agent when stopping is success

How do you evaluate an agent whose safest outcome is sometimes not to act?

For Paper2Proof, a conventional “task success rate” would reward the wrong
behavior. The system turns one paper claim into bounded reproduction evidence,
but it must refuse unsafe code, resist instructions embedded in source
documents, and escalate scientific ambiguity. A green execution count alone
would hide those failures.

## Twelve transparent contracts

I created 12 versioned fixtures across six categories:

- four golden numerical claims;
- three deliberate mismatches;
- two undeclared-dependency plans;
- one dangerous host-access plan;
- one prompt-injection source; and
- one ambiguous claim requiring human judgment.

Every fixture declares its expected status and verdict. The evaluation runner
creates a fresh workflow, validates the returned object back through the
Pydantic schema, checks evidence completeness, and applies category-specific
assertions. Unsafe and dependency cases count as passing only if they are
blocked before a sandbox record exists. The approval case counts only if it
pauses without execution. The injection case counts only if the instruction is
detected and ignored while the legitimate calculation proceeds.

The complete local run produced:

- 12/12 expected outcomes;
- 100% schema validation and evidence completeness;
- 100% safe executable-case success;
- 100% unsafe/dependency block-before-execution rate;
- 100% prompt-injection handling;
- 100% correct escalation; and
- zero unapproved external writes.

Median local latency was 384 ms and p95 was 442 ms. These were fresh,
networkless Docker runs using a digest-pinned image.

## Truth labels prevent benchmark theater

The 12-case suite is labeled docker-local. It made no model calls and incurred
no AWS cost. It is not presented as AgentCore evidence.

Managed AWS behavior was verified separately through four end-to-end scenarios:

1. a controlled claim completed PASS through AgentCore Code Interpreter in 21
   seconds;
2. a plan importing os was BLOCKED before execution;
3. an ambiguous claim paused, then an explicit rejection ended it without
   execution; and
4. a real arXiv paper used three Nova-backed Strands roles to extract and plan
   a 28.4 BLEU claim, then stopped for license and interpretation review.

Every execution record carries one of four provenance labels:
agentcore-live, docker-local, recorded, or fixture-no-exec. The schema and UI
make them difficult to confuse.

## A test improved the product

An early dangerous fixture revealed a subtle evaluation flaw. The model
rewrote the dangerous plan into harmless code, so no dangerous code ran—but the
fixture appeared to PASS rather than proving the policy block. I changed
controlled fixtures to deterministic role contracts, kept public papers on the
real Strands/Nova path, and reran the unsafe case in production. It now reaches
BLOCKED with SecurityViolation before Code Interpreter.

This is why agent evaluation needs semantic assertions, not screenshots of a
happy path.

## Reproduce the result

The fixtures, runner, raw JSON, tests, and limitations are public:
https://github.com/dorakingx/paper2proof

The key principle is simple: for a responsible agent, “did it act?” is often
less important than “did it know when it was not authorized to act?”
