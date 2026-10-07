# Market Research Brief (Insight Monitor)

**English** | [简体中文](README.zh-CN.md)

A small Streamlit application that turns a limited set of user-supplied sources into a reviewable research brief. It is designed as a portfolio demonstration for competitor snapshots, industry updates, and content research—not as an autonomous crawler or a fact-checking service.

![Market Research Brief interface](screenshots/overview.png)

## Features

- Uses one of three source modes: clearly labelled synthetic examples, up to five public web pages, or up to five pasted documents.
- Generates a deterministic report by default, with an executive summary, comparison points, changes, suggested actions, and source-level status.
- Keeps each successful source aligned with its title, URL when supplied, date hint, summary, and a bounded verbatim evidence excerpt.
- Exports the report as Markdown or JSON, or as a ZIP research package containing `project.json` and `report.md`.
- Offers an optional OpenAI-compatible summarization path that is disabled unless both a feature flag and a server-side API key are configured.
- Falls back to the deterministic report when the optional model request fails.

The application does not search the web, sign in to websites, bypass paywalls, schedule jobs, send messages, or maintain a server-side research history.

## Evidence and traceability

The report is grounded in the material supplied during the current session:

- For a public page, the application retains the normalized source URL and an excerpt copied directly from the extracted page text.
- For pasted material, the pasted text is the analyzed source. An optional URL is retained only as a reference link.
- A failed source is marked as unread and receives no generated evidence excerpt.
- Built-in demo sources are synthetic and explicitly labelled; they are not presented as current market facts.

Repository evidence for these behaviors is available in:

| Claim | Implementation or test evidence |
| --- | --- |
| Source limits and pasted-source ordering | `services/sources.py`, `tests/test_sources.py` |
| Public URL validation and redirect checks | `services/urls.py`, `services/fetcher.py`, `tests/test_urls.py`, `tests/test_productization.py` |
| Verbatim evidence excerpts and failed-source handling | `services/report.py`, `tests/test_report.py` |
| Model source-index alignment and safe fallback | `services/model_client.py`, `tests/test_model_client.py` |
| Markdown, JSON, and ZIP exports | `services/export.py`, `tests/test_export.py` |
| Five-source synthetic calibration case | `docs/calibration/2026-09-22-pet-supplies-competitor-case.md` |

These checks establish source alignment and application behavior; they do not establish that a source is authoritative or that a generated conclusion is factually correct.

## Technology stack

- Python 3.10+
- Streamlit 1.64.0
- Python standard-library HTTP, HTML parsing, IP address, JSON, and ZIP modules
- pytest 8.x for automated tests
- Optional OpenAI-compatible Chat Completions endpoint, called without an additional SDK

## Quick start

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`.

The managed start script requires a port and binds to all interfaces:

```bash
PORT=8501 bash start.sh
```

Only expose that development-style process on a trusted host. A production deployment should place it behind an authenticated, TLS-terminating reverse proxy and appropriate network controls.

### Optional model mode

Deterministic mode requires no API key. To allow a user to select the optional model path, configure the server process explicitly:

```bash
export INSIGHT_MONITOR_AI_ENABLED=1
export OPENAI_API_KEY="replace-with-a-server-side-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
export OPENAI_MODEL="gpt-4o-mini"                    # optional
```

Do not commit credentials. When model mode is used, successful source text is sent to the configured provider; review its cost, retention, residency, and cross-border data policies first.

## Tests

The verification workflow runs on Python 3.10 and 3.12. The same checks can be run locally after installing `requirements-dev.txt`:

```bash
PYTHONPATH=. python -m pytest -q tests
python -m compileall -q app.py services tests
python -m pip check
```

## URL and network security boundary

The public-page path accepts only HTTP and HTTPS URLs. It rejects embedded credentials and hosts or resolved addresses classified as local, private, loopback, link-local, reserved, multicast, or unspecified. DNS and destination checks are repeated before each redirect hop. Fetching is also bounded to five URLs, four redirects, a 2 MB response, a 12-second connection timeout, a 20-second overall timeout, HTML content, and 12,000 extracted characters per source.

These are application-level safeguards, not a hardened network sandbox. They do not replace deployment-level egress rules, metadata-service blocking, DNS controls, proxy policy, rate limiting, or abuse monitoring. Deployments handling untrusted users should enforce those controls outside the process as well.

Default deterministic mode makes no model request. Public-page mode still connects to the URLs supplied by the user. If optional model mode is enabled, the application can send at most five sources and 40,000 source characters to the configured OpenAI-compatible endpoint.

## Production boundary

This repository is a customer-demo and portfolio implementation. It does not include authentication or authorization, tenant isolation, persistent storage, audit logs, background jobs, quotas, billing, high availability, backups, production observability, or a factual-accuracy guarantee. Session results exist only in the active Streamlit session unless the user downloads them.

Before using it with customer data, add the controls appropriate to the deployment, obtain permission to process the material, remove sensitive data, and require a person to verify dates, numbers, quotations, and business conclusions against the original sources.

## License

Released under the MIT License. See [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and [SECURITY.md](SECURITY.md).
