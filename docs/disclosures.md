# Disclosures

## Project provenance

- Project start: 2026-08-31 JST.
- A blank repository was initialized during the official submission period.
- No pre-existing Paper2Proof code, assets, evaluation results, customers, or
  validation claims were imported.
- This is an individual submission by a resident of Japan.

## Development tools and frameworks

- OpenAI Codex is used as an AI coding and research assistant.
- Standard open-source frameworks and libraries include Strands Agents,
  Amazon Bedrock AgentCore SDK, FastAPI, Pydantic, React, Vite, pytest, and
  Playwright. Exact versions are locked in repository lockfiles.
- The architecture and implementation are original to this submission; no
  existing personal project repository is being repackaged.

## External sources and fixtures

Each final fixture will identify its source URL, paper or note license, code
license, exact excerpt location, and whether any asset is copied. Full PDFs are
not redistributed. The controlled fixtures created in this repository are MIT
licensed with the code unless stated otherwise.

## Runtime truth labels

Every report identifies one of these provenance modes:

- `agentcore-live`: a fresh managed Code Interpreter execution;
- `docker-local`: a fresh local isolated development execution;
- `recorded`: immutable prior evidence displayed for resilience, never labeled live;
- `fixture-no-exec`: deterministic UI/test data with no execution claim.

Cached, mocked, or incomplete behavior will remain visibly labeled in the app,
README, video, and submission text. No unrun test is reported as passing.

## Validation

Executed and unexecuted test lists are maintained in `hackathon/evidence-log.md`
and the final measured results are written to `evals/results.json` only by the
evaluation runner.
