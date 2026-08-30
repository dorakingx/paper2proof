# Idea Scorecard

Checked: 2026-08-31. Scores are 0–10. The total is unweighted because the
brief asked for eleven explicit factors and supplied no alternate weights.

| Idea | Theme | Strands | AgentCore | Repetition | E2E | Demo | Differentiation | Founder fit | Deadline | Safety | Grand Prize | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Paper2Proof** | 10 | 10 | 10 | 10 | 8 | 10 | 9 | 10 | 8 | 9 | 10 | **104** |
| Artifact Shepherd (research repo release readiness) | 9 | 8 | 8 | 9 | 9 | 8 | 7 | 10 | 9 | 9 | 8 | 94 |
| GrantGuard (grant evidence/requirement steward) | 9 | 8 | 7 | 10 | 8 | 8 | 7 | 7 | 8 | 9 | 8 | 89 |
| LabOps Ledger (small-lab inventory and ordering gate) | 9 | 8 | 7 | 10 | 7 | 8 | 7 | 7 | 7 | 8 | 8 | 86 |
| ReleaseProof (maintainer release verification agent) | 9 | 8 | 8 | 9 | 9 | 9 | 6 | 8 | 9 | 9 | 8 | 92 |
| Accessibility Filing Steward | 9 | 8 | 6 | 9 | 8 | 8 | 8 | 6 | 8 | 8 | 8 | 86 |
| Vendor Evidence Chaser for small businesses | 9 | 8 | 6 | 10 | 8 | 8 | 6 | 6 | 8 | 7 | 7 | 83 |
| Teaching Lab Adapter (lesson-to-accessibility variants) | 9 | 8 | 5 | 9 | 9 | 9 | 6 | 6 | 9 | 9 | 7 | 86 |
| Quantum Experiment Cost Gate | 9 | 9 | 9 | 8 | 6 | 7 | 9 | 10 | 6 | 8 | 9 | 90 |

No alternative exceeds Paper2Proof by 10%; the switch condition is therefore
not met. Paper2Proof stays selected.

## Competitive and feasibility check

The event's own project gallery was not public on 2026-08-31, so no current
entry is claimed as reviewed. Public adjacent work was checked instead:

- RepliCAT (Devpost): multi-agent paper/repository analysis, plan generation,
  sandboxing, and reproducibility rubrics. Direct overlap is high.
  https://devpost.com/software/broshengpt
- veriXiv (Devpost): paper-level reproducibility rubric/evidence workspace.
  https://devpost.com/software/verixiv
- DecodeXiv (Devpost): paper visualization plus a reproduction-notebook
  pipeline. https://devpost.com/software/aaaa-9bx6fi
- CORE benchmark: agents reproduce paper results from repositories and answer
  questions about outputs. https://crab.cs.princeton.edu/core-website/
- ReproAgent (2026): contract-guided paper-to-code reproduction.
  https://arxiv.org/abs/2608.24291

Paper2Proof is not positioned as the first or only paper reproduction agent.
Its defensible product distinction is narrower and operational:

1. claim-level, not paper-level, evidence contracts;
2. reported value → actual command → observed value → tolerance → verdict;
3. managed AgentCore Code Interpreter execution with captured exit/output/file hashes;
4. a persistent background job and explicit decision center, not an agent chat;
5. separation of execution success from scientific reproducibility;
6. honest `INCONCLUSIVE`/`BLOCKED` outcomes and approval before external writes;
7. immutable, downloadable evidence bundles designed for a research notebook.

The vertical slice is the go/no-go proof. It must show a real Strands tool call
and managed Code Interpreter output; a local Docker path can support developer
tests but cannot be presented as AgentCore evidence.
