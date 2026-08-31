# Contributing

Thanks for helping Paper2Proof make reproducibility evidence safer and clearer.

## Before opening a change

- Keep the core boundary intact: models advise; deterministic policy and human
  approval authorize consequential actions.
- Do not add private datasets, copyrighted PDFs, credentials, or generated
  evidence containing sensitive information.
- Add or update a transparent fixture for behavior changes.
- Preserve runtime truth labels. Never present a local or recorded result as a
  live AgentCore run.

## Development checks

```bash
uv sync --frozen --all-groups
uv run ruff check services/agent/src tests
uv run ruff format --check services/agent/src tests
uv run mypy services/agent/src
uv run pytest -q --cov=paper2proof --cov-report=term
```

Changes to the AgentCore CDK package should also pass:

```bash
cd agentcore/cdk
npm ci
npm test
npm run build
```

Open a focused pull request explaining the user outcome, safety impact,
verification performed, and any limitations. Security vulnerabilities should
use GitHub private security advisories instead of a public issue.
