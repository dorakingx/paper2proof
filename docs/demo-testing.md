# Public demo testing

Public URL:
https://ptvrh62d34oqwkz4x6cjtbvxgm0yaimi.lambda-url.us-west-2.on.aws/

## Judge path

1. `GET /health` should report `status=ok`, `strands_agents=true`,
   `agentcore_code_interpreter=true`, and `agentcore_runtime=true`.
2. Open the home page in a private browser. No sign-in is required.
3. Run **Reproducible mean**. The initial request should return quickly as
   `QUEUED`, then reach `COMPLETED / PASS` and show `agentcore-live` provenance.
4. Download both evidence formats and confirm the same job/trace identifiers
   and evidence hash appear in the UI and JSON.
5. Run **Ambiguous spread**. Confirm it reaches `AWAITING_APPROVAL` with no
   execution record; reject it and confirm `BLOCKED`.
6. Submit a supported arXiv URL. Confirm agent/tool trace events appear and the
   plan stops for license/interpretation review before execution.

## API smoke checks

```bash
PUBLIC_URL=https://ptvrh62d34oqwkz4x6cjtbvxgm0yaimi.lambda-url.us-west-2.on.aws
curl -fsS "$PUBLIC_URL/health"
curl -fsS "$PUBLIC_URL/v1/fixtures"
curl -i "$PUBLIC_URL/v1/jobs"
```

The last request uses GET and should return `405 Method Not Allowed`; anonymous
job enumeration is intentionally absent.

## Expected boundaries

- 30 POST requests per hashed source IP per hour; `429` includes `Retry-After`.
- Request bodies above 32 KiB return `413`.
- Unknown job IDs return `404`.
- Evidence requested before a report exists returns `409`.
- Invalid payloads return `422`.
- Input is restricted to public HTTPS arXiv/GitHub sources and allowlisted
  fixture IDs.

## Truth labels

- `agentcore-live`: fresh managed AgentCore Code Interpreter execution;
- `docker-local`: fresh local isolated execution;
- `recorded`: immutable prior evidence, never represented as live;
- `fixture-no-exec`: deterministic no-execution fixture evidence.

When reporting an issue, include the job ID and approximate timestamp, but do
not include credentials or private source material.
