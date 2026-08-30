# Execution Plan

## Product contract

An independent computational researcher submits one public source and an
optional public code repository. Paper2Proof selects or asks approval for one
bounded numerical claim, executes a reproducibility plan, and returns evidence
that identifies exactly what ran and what the result does—and does not—show.

## Gates

1. **Rules and provenance** — complete Dossier, scorecard, blank-repo evidence.
2. **Vertical slice** — Strands structured claim and plan; AgentCore Code
   Interpreter execution; structured comparison and bundle.
3. **Product workflow** — persisted background jobs, decision gate, retries,
   downloads, trace UI, three demo fixtures.
4. **Safety/evaluation** — 12 fixtures, SSRF and injection defenses, secret and
   dependency scans, measured results without invented numbers.
5. **Production** — AgentCore Runtime, S3/DynamoDB/SQS/CloudWatch, public web,
   cost alert, anonymous judge path.
6. **Presentation** — architecture PNG, README, 4-minute real demo, three
   builder.aws articles.
7. **Submission** — logged-out tests, final audit, Devpost submit confirmation,
   immutable release/tag.

## Vertical-slice acceptance

- [ ] The claim, plan, execution, comparison, and verdict validate as Pydantic.
- [ ] `AgentCoreCodeInterpreter` runs the command; the host never executes it.
- [ ] Evidence captures region/service, session ID (redacted-safe), code,
      language, exit/success status, stdout/stderr-equivalent response, files,
      timestamps, and hashes.
- [ ] Strands lifecycle/tool events appear in the trace.
- [ ] Re-running the controlled fixture produces the expected terminal state.
- [ ] Failure produces a structured `FAILED` or `BLOCKED` report.

## Decision policy

Automatic execution is allowed only for public, clearly licensed, bounded,
CPU-sized, non-networked fixture work with no external write. Ambiguous claims,
unclear licenses, expensive computation, network requirements, dangerous
commands, or external mutation must stop at `AWAITING_APPROVAL` or `BLOCKED`.

## Internal timeline

| Gate | Target (JST) |
|---|---|
| Initial public repository and Devpost draft | 2026-08-31 |
| Managed vertical slice | 2026-09-02 |
| Product-complete web workflow | 2026-09-06 |
| 12-fixture evaluation and production deployment | 2026-09-09 |
| Articles and video rough cut | 2026-09-11 |
| Code freeze | 2026-09-13 23:59 |
| Submission package final | 2026-09-14 12:00 |
| Internal submit | 2026-09-14 21:00 |
