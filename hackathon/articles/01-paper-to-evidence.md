# Agents for Humans: Turning a paper claim into evidence with Paper2Proof

Computational researchers rarely stop at reading a paper. To decide whether a
result is useful, they repeatedly locate a numerical claim, recover its
conditions, find or write the smallest corresponding experiment, build an
environment, run it, compare the result, and record what happened.

Most research assistants stop at search, summary, or question answering. That
still leaves the researcher with a paper, not evidence.

I built Paper2Proof for the Agents for Humans Hackathon to close that gap. It is
an autonomous reproducibility steward for independent researchers and small
teams. A user gives it a public arXiv URL or selects a transparent controlled
demo. Six specialized Strands Agents roles move one bounded claim through:

1. source intake and risk assessment;
2. numerical claim extraction;
3. reproduction planning;
4. isolated execution;
5. deterministic verification and critique; and
6. evidence reporting and the next human decision.

The output is not a confident paragraph. It is a content-addressed evidence
object with the exact source locator and hash, reported value and tolerance,
code, runtime provenance, observed output, state transitions, agent/tool trace,
limitations, verdict, and next action.

## The human is an authority boundary

“Human in the loop” can become a vague safety phrase. Paper2Proof makes it a
state transition.

If a claim has multiple valid interpretations, a license is unclear, a plan
needs network access, a dependency is undeclared, or an operation could write
externally, the job does not silently guess. It reaches AWAITING_APPROVAL or
BLOCKED with structured reasons and concrete options. A prohibited operation
cannot be approved into safety.

This division is the product's central rule:

**Models propose. Deterministic policy and explicit human approval authorize.**

The model never owns URL policy, code safety, budgets, state transitions, or
the PASS/MISMATCH comparison. That authority stays in reviewable code.

## A successful run is evidence, not truth

One of the easiest mistakes in reproducibility tooling is to equate a process
that exited successfully with a paper that is scientifically reproduced.
Paper2Proof keeps these separate.

A PASS means one observed number matched one reported number under the recorded
conditions and tolerance. The evidence still states its limitations. A real
public-paper run may correctly end at AWAITING_APPROVAL because source licensing
or scientific interpretation requires a person.

That is not an incomplete demo. It is the intended behavior of a responsible
research agent.

## Try the public service

- Live demo: https://ptvrh62d34oqwkz4x6cjtbvxgm0yaimi.lambda-url.us-west-2.on.aws/
- Source and evaluation: https://github.com/dorakingx/paper2proof

Start with Reproducible mean to see an end-to-end AgentCore Code Interpreter
run. Then try Ambiguous spread to see a human decision stop execution.

Paper2Proof does not promise to reproduce every paper. It automates the bounded
work that can be made inspectable, and returns the rest to the human whose
judgment matters.
