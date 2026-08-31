# Execution plan

## Product contract

An independent computational researcher submits one public source and an
optional public repository. Paper2Proof selects or asks approval for one
bounded numerical claim, executes a policy-safe reproduction plan, and returns
evidence identifying exactly what ran and what the result does—and does not—show.

## Gate status

| Gate | Status | Exit evidence |
|---|---|---|
| Rules and provenance | COMPLETE | official dossier, blank-repo history, public MIT repository |
| Managed vertical slice | COMPLETE | live AgentCore Runtime + Code Interpreter PASS with session and evidence hash |
| Product workflow | COMPLETE | durable SQS worker, persisted states, approvals, downloads, trace UI |
| Safety and evaluation | COMPLETE | 12/12 fixture evaluation, scans, live unsafe/SSRF negatives |
| Production | COMPLETE | public AWS URL, least-privilege IaC, encrypted state/evidence, alarms, budget |
| Presentation package | IN PROGRESS | architecture and docs complete; video and articles need publication |
| Devpost submission | PENDING | must end with confirmed **Submitted** status |

## Decision policy

Automatic execution is allowed only for public, clearly licensed, bounded,
CPU-sized, non-networked fixture work with no external write. Ambiguous claims,
unclear licenses, expensive computation, network requirements, dangerous code,
undeclared dependencies, or external mutation must stop at
`AWAITING_APPROVAL` or `BLOCKED`.

## Remaining critical path

1. Deploy and verify the privacy-hardening update that removes anonymous job
   enumeration and DynamoDB `Scan`.
2. Perform logged-out desktop/mobile visual QA and capture final screenshots.
3. Commit and push the complete source, docs, IaC, evaluation, and assets;
   verify all GitHub Actions jobs.
4. Record a 3:45–4:15 English demo from the real public product, then upload
   publicly to YouTube or Vimeo and verify duration/access.
5. Publish three concise builder.aws articles, each with “Agents for Humans”
   in its title, and record their URLs.
6. Read the exact Builder ID email from the authenticated account; do not
   infer it.
7. Populate Devpost, run a logged-out link audit, submit, and independently
   confirm both the confirmation screen and submission manager show
   **Submitted**.
8. Create a final immutable Git tag/release only after submission materials
   reference the verified commit.

## Internal deadlines (JST)

| Milestone | Target |
|---|---|
| Code/docs freeze and video capture | 2026-09-11 |
| Articles + submission draft complete | 2026-09-12 |
| Final logged-out audit | 2026-09-13 |
| Internal Devpost submit | 2026-09-14 21:00 |
| Official deadline | 2026-09-15 09:00 |

The internal schedule deliberately preserves more than 12 hours for account,
upload, or Devpost failures.
