# Security Policy

## Supported versions

Paper2Proof is a hackathon-stage research tool. Only the current `main` branch
is supported while the first public release is being prepared.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or exposed secret.
Use GitHub's private vulnerability reporting for this repository. Include the
affected commit, a minimal reproduction, impact, and any safe mitigation you
have already tested. We will acknowledge a report within 72 hours.

## Trust boundary

Public papers, repositories, extracted text, generated plans, and experiment
output are untrusted data. A language model cannot authorize execution. Code
must pass deterministic policy checks and run only in a declared isolated
backend. Evidence reports always label runtime provenance; recorded or local
results must never be represented as live Amazon Bedrock AgentCore results.
