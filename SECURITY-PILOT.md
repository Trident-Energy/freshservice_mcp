# HTTP transport security pilot - 28 October 2026

Prepared under TE-GH-2026-10-28-PILOT-01; no deployment authorized.

Add an h11>=0.16.0 floor to project dependencies so both pip installs and uv installs use the fixed parser. Resolve h11 0.14.0 -> 0.16.0 and its compatible parent httpcore 1.0.8 -> 1.0.9. Other locked packages stay unchanged.

Source: https://github.com/python-hyper/h11/security/advisories/GHSA-vqfr-h8mv-ghfj. The advisory metadata lists 0.16.0 as the patched version. The service currently runs MCP over stdio and uses outbound HTTPX; a vulnerable deployed reverse-proxy path has not been established.

Validation:

- `uv sync --frozen`
- `uv run --frozen python -m unittest discover -s tests/offline -v`
- `uv lock --check`
- `uv pip check`
- `uv build`

Three offline tests check rejection of malformed chunk endings, an actual async HTTPX/HTTPcore loopback chunked-response roundtrip, and MCP tool registration without service calls. The malformed-chunk test fails with the old locked h11 and passes after the update. Wheel and source-distribution builds pass.

Do not run tests/test-fs-mcp.py as a production check: it contains examples that create/update/delete real service records. A read-only tool request using a designated test account, the actual MCP client and hosting configuration still needs validation before separately approved rollout. This scoped fix does not clear the repository's other dependency alerts.

Before deployment, identify runtime owner, packaging/launch command, deployed version and rollback artifact. Preserve the current immutable package/environment. Redeploy that artifact if the approved rollout fails, then verify the MCP session and read-only Freshservice access. Rollback reintroduces the vulnerable parser and must be temporary. No migrations or live settings changes are included.
