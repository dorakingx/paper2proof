# Evidence Log

This file records only observed evidence. Planned results are never entered as
passes.

| Date (JST) | Evidence | Result | Artifact |
|---|---|---|---|
| 2026-08-31 | Blank Git repository created in `Developer/App/Paper2Proof` | PASS | local `.git` history |
| 2026-08-31 | Official rules, FAQ, resources, updates, schedule checked | PASS | `competition-dossier.md` |
| 2026-08-31 | Current event project gallery checked | NOT PUBLISHED | official gallery URL |
| 2026-08-31 | Current SDK releases checked | PASS | Strands 1.54.0; tools 0.8.7; AgentCore 1.22.0 |
| 2026-08-31 | GitHub authentication | PENDING | `gh auth status` reported invalid prior token |
| 2026-08-31 | AWS credentials | PENDING | AWS CLI absent; no AWS environment/profile detected |
| 2026-08-31 | Unit and contract suite | PASS | 57 tests; 88.66% coverage; Ruff and strict mypy pass |
| 2026-08-31 | Actual local sandbox execution | PASS | Docker-local; exit 0; observed 5.0; verdict PASS |
| 2026-08-31 | Docker isolation regression | PASS | Missing stdin attachment found by live run, fixed, regression-tested |
| 2026-08-31 | Local sandbox image provenance | PASS | `python@sha256:7ce4b6dfe35e55397b7cda544f8a13f191b7ae28dc5aad71fe664dbc9bc2623f` |

## Measured evaluation

Not run yet. No latency, success rate, unsafe-action rate, token usage, or cost
number is claimed before the versioned evaluation artifact exists.
