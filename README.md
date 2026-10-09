# Market Research Brief (Insight Monitor)

**English** | [简体中文](README.zh-CN.md)

[![Verify](https://github.com/Zhang-ZhengHao/market-research-brief/actions/workflows/verify.yml/badge.svg)](https://github.com/Zhang-ZhengHao/market-research-brief/actions/workflows/verify.yml)

Market Research Brief turns up to five user-pasted documents into a reviewable research brief. It preserves source order and verbatim evidence excerpts, then exports Markdown, JSON, or a ZIP handoff package. The bundled examples are synthetic. This project is a portfolio demonstration, not a crawler, fact-checking service, or production research system.

![Paste-only Market Research Brief interface](screenshots/overview.png)

## What it demonstrates

- Exactly two input modes: clearly labelled synthetic examples and user-pasted text.
- Optional reference links are user-supplied metadata. The app does not fetch or verify them.
- Deterministic processing requires no API key or model request.
- Findings remain aligned with source titles, input order, and bounded verbatim evidence excerpts.
- Markdown, JSON, and ZIP exports; the ZIP contains project.json and report.md.
- Results remain in the active Streamlit session unless the user downloads them.
- An optional OpenAI-compatible summarizer is feature-gated, server-configured, and backed by deterministic fallback.

## Five-minute review

1. Choose a synthetic template or switch to pasted text.
2. For pasted text, add one to five documents in the order they should be compared.
3. Optionally store an HTTP(S) reference link. It is not opened, resolved, or verified by the application.
4. Generate the report and inspect each source title, summary, date hint, and verbatim evidence excerpt.
5. Download Markdown, JSON, or the ZIP research package.

Built-in templates are synthetic and are never presented as current market facts. Generated summaries may be incomplete or wrong. Verify dates, numbers, quotations, and business conclusions against the pasted source text before publication or decision-making.

## Evidence map

| Claim | Implementation and tests |
| --- | --- |
| Pasted-source ordering and 1–5 document limits | services/sources.py, tests/test_sources.py |
| Inert HTTP(S) reference metadata with no DNS or page request | services/reference_links.py, tests/test_sources.py, tests/test_productization.py |
| Verbatim evidence and deterministic fallback | services/report.py, tests/test_report.py |
| Model source-index alignment and reference-link minimization | services/model_client.py, tests/test_model_client.py |
| Markdown, JSON, and deterministic ZIP exports | services/export.py, tests/test_export.py |
| Two-mode Streamlit workflow and version identity | app.py, tests/test_app.py, tests/test_version.py |

These checks establish application behavior and traceability. They do not establish that supplied material is authoritative or that a conclusion is factually correct.

## Source and network boundary

Source ingestion does not resolve hostnames, open sockets, or request reference links. Reference links accept syntactically valid HTTP(S) URLs without embedded credentials, discard fragments, and remain unverified metadata. A link can therefore point anywhere; treat it as untrusted before opening it in a browser.

Default deterministic mode makes no model request. If optional model summarization is explicitly enabled, accepted source titles and text are sent to the configured provider; reference links are not included in the prompt. Review that provider's cost, retention, residency, and privacy terms first.

Limits are enforced before report generation:

- one to five pasted documents;
- at most 12,000 characters per document;
- at most 40,000 pasted characters per report.

## Quick start

Python 3.10 or newer:

    python3 -m venv .venv
    . .venv/bin/activate
    python3 -m pip install -r requirements-dev.txt
    python3 -m streamlit run app.py

The managed start command reads its port from the environment and binds to all interfaces:

    PORT=8501 bash start.sh

Only expose this development-style process on a trusted host. A production deployment should place it behind authentication, TLS termination, and appropriate platform controls.

### Optional model mode

Deterministic mode requires no key. The optional model path is unavailable unless the deployment explicitly enables it and supplies a server-side key:

    export INSIGHT_MONITOR_AI_ENABLED=1
    export OPENAI_API_KEY="replace-with-a-server-side-key"
    export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
    export OPENAI_MODEL="gpt-4o-mini"                    # optional

Do not commit credentials. The key is read by the server process and is not rendered in the page.

## Verification

The GitHub Actions matrix runs on Python 3.10 and 3.12. Run the same checks locally after installing development dependencies:

    PYTHONPATH=. python3 -m pytest -q tests
    python3 -m compileall -q app.py services tests
    python3 -m pip check

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Production boundary

This repository is a customer-demo and portfolio implementation. It does not include authentication, authorization, tenant isolation, persistent storage, audit logs, background jobs, quotas, billing, high availability, backups, production observability, or a factual-accuracy guarantee.

Before using customer material, obtain permission, remove sensitive data, review the optional model provider's policies, and require a person to verify the report against the pasted source text.

## License

Released under the MIT License. See [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and [SECURITY.md](SECURITY.md).
