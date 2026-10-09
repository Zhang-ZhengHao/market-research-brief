# Market Research Brief v0.1.0 Paste-only Safety Cut

**Status:** Approved for specification on 2026-10-09; implementation has not started.

## Context

The current application offers a public-page source mode. It resolves and
classifies a hostname before opening it, then passes the hostname to `urllib`,
which can resolve it again when the connection is created. That check/use gap
does not bind the approved address to the actual connection and therefore does
not establish a reliable DNS-rebinding boundary. The current address
classification also does not explicitly block the shared address space
`100.64.0.0/10`, and the documented overall timeout cannot interrupt a single
blocking read at the deadline.

The public README and repository topics describe stronger SSRF and timeout
guarantees than the implementation can prove. A portfolio project should make
narrow, reviewable claims rather than retain a risky feature behind an
overstated security boundary.

## Decision

Version 0.1.0 will remove public-page retrieval and become a paste-only
research workflow. Users can work from bundled synthetic examples or paste the
text of up to five documents. An optional HTTP(S) reference link may be stored
for later review, but the application will never resolve or fetch that link.

This safety cut is preferred to building a hardened network fetcher in this
release. Correct address pinning, TLS/SNI handling, proxy behavior, redirect
policy, and interruptible end-to-end deadlines form a separate networking
project and are explicitly out of scope.

## Goals

1. Remove the public-page input and every runtime path that retrieves source
   pages.
2. Preserve the useful research workflow for synthetic and user-pasted text.
3. Make the remaining network boundary exact: deterministic source processing
   is offline; the optional configured model is the only deliberate outbound
   request.
4. Align the English and Chinese documentation, screenshot, repository
   description, topics, and profile reference with the implemented behavior.
5. Publish a reviewable v0.1.0 with semantic version and build identity.

## Non-goals

- Building or claiming a secure crawler, browser, URL preview, or web-search
  service.
- Adding authentication, persistence, scheduling, billing, or a production
  deployment.
- Changing CommerceOps Desk, HAURUX ERP, repository pins, avatars, or social
  profiles in this release.
- Claiming factual accuracy, source authority, customer outcomes, or production
  readiness.

## User-facing behavior

The source selector will contain exactly two choices:

- **Synthetic example:** load the bundled, clearly labelled calibration data.
- **Pasted text:** accept one to five documents in a stable user-defined order.

Each pasted document keeps its title, body, and optional reference link. The
reference link is metadata only. The interface and exported report will label
it as user supplied and not fetched or verified by the application.

Existing limits remain:

- at most five pasted documents;
- at most 12,000 characters per document;
- at most 40,000 pasted characters in one report.

The default deterministic report continues to require no API key. Optional
model summarization remains disabled unless both the feature flag and a
server-side key are configured. When enabled, the interface will state that
the pasted text is sent to the configured model provider and may be subject to
that provider's cost, retention, residency, and privacy policies.

## Components and boundaries

### Streamlit application

`app.py` will remove the public-page radio option, URL-list form, fetch
progress, fetch result messages, and imports from the network-fetching modules.
The example and pasted-text journeys remain, with copy updated to describe the
paste-only boundary.

### Pasted-source construction

`services/sources.py` remains responsible for document count, per-document
size, total size, ordering, and metadata. It will no longer depend on DNS or
public-destination validation.

A small pure reference-link normalizer will accept only syntactically valid
HTTP(S) URLs without embedded credentials, discard fragments, and return a
normalized string. It will not call DNS, open a socket, perform a request, or
claim that the destination is public or trustworthy.

### Removed network-source code

The page fetcher and DNS destination validator will be deleted, together with
tests that only exercise the removed retrieval feature. Keeping dormant code
would leave an ambiguous security surface and make the repository's stated
boundary harder to verify.

### Report and export

Report generation, source traceability, deterministic fallback, Markdown,
JSON, and ZIP export remain. Labels and recovery advice that mention fetched
web pages will be replaced with paste-only wording. The existing project schema
identifier remains unchanged because the retained source records are still
compatible.

### Optional model client

The model client remains separate from source ingestion. It receives only the
already accepted synthetic or pasted documents, remains feature-gated, and
continues to fall back to the deterministic report when the provider request
fails. Removing page retrieval must not silently enable or alter model use.

### Version identity

`services/version.py` will expose `APP_VERSION = "0.1.0"` together with the
existing normalized build SHA. The footer will display both values so a
reviewer can distinguish the release from an unversioned or stale deployment.

## Data flow

```text
synthetic example or pasted documents
  -> pasted-source validation and reference-link normalization
  -> deterministic report builder
     -> optional, explicitly enabled model summarizer
     -> deterministic fallback on model failure
  -> human review in the current Streamlit session
  -> Markdown, JSON, or ZIP download
```

No step in source ingestion resolves a hostname or retrieves a page.

## Error handling

- Blank documents, too many documents, oversized individual documents, and an
  oversized combined input fail before report generation with an actionable
  validation message.
- Invalid or credential-bearing reference links are rejected as metadata; no
  connection attempt is made.
- A model timeout, invalid response, or provider error produces the existing
  deterministic fallback and visible status rather than losing the report.

## Verification strategy

The implementation will update or add tests that prove:

1. the source selector exposes only synthetic and pasted-text modes;
2. the application no longer imports or calls the page fetcher;
3. reference-link normalization is purely syntactic and never invokes DNS,
   sockets, or HTTP clients;
4. example and pasted-text report journeys complete while network-source calls
   are replaced with fail-fast test doubles;
5. ordering, document limits, source-level evidence, deterministic fallback,
   and all three export formats remain correct;
6. the footer shows semantic version 0.1.0 and a normalized build SHA;
7. the Python 3.10 and 3.12 CI matrix still passes tests, compilation, and
   dependency consistency checks.

Tests dedicated only to the deleted fetcher, redirects, DNS classification,
and fetch timeouts will be removed. Passing CodeQL is supporting evidence, not
proof of the offline source boundary.

## Documentation and public metadata

Before release:

- update English and Chinese READMEs to describe two source modes;
- remove SSRF, redirect, DNS, crawler, and hard overall-timeout claims;
- update the interface screenshot so it contains no public-page control;
- add a changelog entry for the safety cut;
- update the GitHub description and remove the `ssrf-protection` and
  `url-validation` topics;
- update the profile README sentence that currently advertises supplied public
  pages;
- retain explicit synthetic-data, optional-model, privacy, and production
  boundaries.

## Release sequence

1. Implement the safety cut on a review branch.
2. Run the complete local verification suite and inspect the generated UI.
3. Refresh the screenshot from the verified application.
4. Open or update a pull request and wait for successful repository CI.
5. Merge the reviewed change into `main`.
6. Create annotated tag `v0.1.0` and a formal GitHub Release tied to the green
   main-branch run.
7. Update repository metadata and the profile README only after the release URL
   exists.

## Acceptance criteria

- The released source tree contains no public-page source option and no source
  page fetcher.
- Synthetic and pasted-text workflows work without DNS or page requests.
- Optional model traffic remains explicit, disabled by default, and accurately
  documented.
- Documentation, screenshot, description, and topics make no SSRF or secure
  crawling claim.
- Local verification and the Python 3.10/3.12 main-branch workflow pass.
- The public v0.1.0 Release, README, and profile reference describe the same
  paste-only behavior.

## Rollback

The change is versioned in Git and does not migrate persistent customer data.
If a regression is found before release, the review branch will not be merged.
If a regression is found after release, a follow-up patch will restore the last
known-good paste-only commit; the removed network source mode will not be
re-enabled as a rollback mechanism.
