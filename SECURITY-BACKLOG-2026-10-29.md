# Dependency backlog remediation — 29 October 2026

Prepared under TE-GH-20261028-FRESHSERVICE-MCP-REMAINING-01 from main commit `351d91d9e318aa3b1fc11c1772bec0462739c410`. Authorization is the human's direct chat approval of 29 October, limited to compatible fixes, offline validation and a draft PR. No live tool invocation or production merge/deployment/configuration/data change is authorized.

## Change and verification

The lock updates AnyIO 4.9.0 → 4.14.2, MCP 1.23.0 → 1.30.0, PyJWT 2.11.0 → 2.15.1, python-multipart 0.0.22 → 0.0.31, IDNA 3.10 → 3.15, cryptography 46.0.5 → 46.0.7 and Starlette 0.46.2 → 0.49.1. MCP remains on 1.x; cryptography and Starlette remain on their existing major lines. MCP metadata requires compatible Pydantic/typing versions on Python >=3.14, so the universal lock contains additional marker-selected versions for that runtime. Removed sniffio is no longer required by the selected AnyIO graph.

MCP's project minimum is raised; `[tool.uv].constraint-dependencies` retains security floors and major limits for uv resolution. These transitive constraints govern uv, not a raw pip/uvx package installation. Review and release validation must use this checkout and frozen uv lock; PyPI `uvx freshservice-mcp` does not install this unreleased branch.

`uv sync --frozen`, `uv lock --check`, `uv pip check`, eight offline unittest cases, and wheel/source-distribution builds pass on Python 3.13.18. Added-test Ruff checks pass. Run `python -m unittest discover -s tests/offline -v` after the frozen sync. Tests block connect/connect_ex and DNS, disable dotenv loading for the server probe, use a synthetic API key/domain, and use HTTPX MockTransport for a single read. They check tool/schema registration, read pagination, IDNA 2008 TLS hostname handling, early IDNA length rejection, semicolon form parsing, empty HMAC JWK rejection, critical-header handling, options immutability and nested-payload errors. They do not validate a real Freshservice connection or MCP client session.

The original packages fail the AnyIO hostname, IDNA early rejection, multipart separator, unknown critical-header and JWT options-mutation regressions. The selected versions pass. The original nested-payload check passed and is not claimed as a reproduced failure.

The selected versions put 33 of the 42 scoped GitHub alert instances outside their affected ranges. GitHub default-branch alerts remain open until reviewed changes are merged and re-evaluated. Duplicate advisory aliases in pip-audit are not additional unique vulnerabilities.

## Residual decisions and limitations

- cryptography 46.0.7 fixes the 46.x patchable issues, but [GHSA-537c-gmf6-5ccf](https://github.com/advisories/GHSA-537c-gmf6-5ccf), [GHSA-jwv3-5hgf-82ww](https://github.com/advisories/GHSA-jwv3-5hgf-82ww), [GHSA-m2h6-j472-rp4c](https://github.com/advisories/GHSA-m2h6-j472-rp4c) and [GHSA-g6cj-pr64-35w5](https://github.com/advisories/GHSA-g6cj-pr64-35w5) require later major lines (48.0.1, 49.0.0 or 50.0.0). Migration is a separate decision.
- Starlette 0.49.1 fixes the pre-0.47.2/pre-0.49.1 issues, but five current advisories require 1.0.1 through 1.3.1, including [GHSA-82w8-qh3p-5jfq](https://github.com/advisories/GHSA-82w8-qh3p-5jfq). Migration to 1.x remains separate.
- These are nine residual scoped alert instances. The complete pip-audit remains nonzero. It also identifies unchanged certifi [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2), outside the claimed package scope.
- h11 0.14.0/httpcore 1.0.8 remain unchanged. Their existing draft PR #11 is separate and still required. Existing Dependabot PR #10 combines h11 with a Starlette major update and older patch choices; PR #8 proposes PyJWT 2.12.0, which is insufficient for later advisories. Neither is merged or overwritten.
- [GHSA-gvp8-978c-rx2q](https://github.com/advisories/GHSA-gvp8-978c-rx2q) has no first patched release declared; its stated affected range ends at 2.13.0. Selected 2.15.1 is outside that range and passes the options-reuse regression.
- The existing `tests/test-fs-mcp.py` contains live mutation examples and was intentionally not run. Python >=3.14 is resolved in the universal lock but was not executed here.

## Release and rollback

The owner must confirm packaging/deployment, combine or rebase the independently reviewed h11 fix, validate a designated read-only Freshservice account and real MCP-client integration, and decide the residual major upgrades before production promotion. Reverting this commit and rebuilding from the former lock is the rollback; that restores known vulnerable dependencies and is an operational fallback only.
