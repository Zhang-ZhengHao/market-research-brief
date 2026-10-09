# Paste-only v0.1.0 Safety Cut — Implementation Plan

**Approved design:** `docs/superpowers/specs/2026-10-09-paste-only-v0.1-safety-cut-design.md`

## Objective

Ship a reviewable `v0.1.0` that accepts only bundled synthetic examples or
user-pasted text. Optional HTTP(S) reference links remain inert metadata. The
source-ingestion path must not resolve hostnames, open sockets, or retrieve web
pages. The optional, explicitly enabled model client remains the only outbound
runtime integration.

## Guardrails

- Work only on `feat/paste-only-v0.1.0` until review and merge.
- Preserve the five-document, 12,000-character-per-document, and
  40,000-character-total limits.
- Preserve deterministic report generation and Markdown, JSON, and ZIP export.
- Do not broaden the release into authentication, persistence, deployment, or
  a hardened crawler.
- Use red-green-refactor for every behavior change. Record the expected failure
  before writing the corresponding implementation.
- Do not claim an offline application globally: an explicitly enabled model
  request can still send accepted source text to the configured provider.

## Task 1 — Establish the baseline

1. Install or reuse the repository's declared development dependencies.
2. Run:

   ```bash
   PYTHONPATH=. python -m pytest -q tests
   python -m compileall -q app.py services tests
   python -m pip check
   ```

3. Stop and report if the starting branch is not green.

## Task 2 — Replace public-destination validation with inert reference links

**Tests first:** `tests/test_sources.py`

1. Add a failing test showing that a syntactically valid local-looking HTTP(S)
   reference (for example `http://localhost/...`) is accepted as metadata,
   normalized, and has its fragment removed. This must fail under the current
   public-destination policy.
2. Add coverage for scheme normalization, default-port removal, query
   preservation, IPv6 bracket preservation, invalid schemes, missing hosts,
   invalid ports, and embedded credentials.
3. Add a fail-fast DNS/socket double and prove reference normalization never
   invokes it.
4. Implement the smallest pure helper in `services/reference_links.py` and
   route `services/sources.py` through it.
5. Run the focused source tests, then the full suite.

## Task 3 — Remove the public-page UI and runtime path

**Tests first:** `tests/test_app.py`, `tests/test_productization.py`

1. Add a failing UI assertion that the source selector exposes exactly
   `示例资料` and `粘贴正文`.
2. Add failing repository-boundary assertions that the app has no fetcher/URL
   validator import and that the obsolete network-source modules are absent.
3. Keep or add example and pasted-text journey tests with fail-fast network
   doubles so both journeys demonstrate zero page retrieval.
4. Remove the public-page controls, progress state, validation branch, fetch
   branch, and their imports from `app.py`.
5. Delete `services/fetcher.py`, `services/urls.py`, `tests/test_fetcher.py`,
   `tests/test_urls.py`, and fetch-only cases from
   `tests/test_productization.py`.
6. Replace user-facing crawler/fetch wording in the UI, reports, and retained
   tests with paste-only wording where it describes active behavior.
7. Run focused app/productization tests, then the full suite.

## Task 4 — Add release identity

**Tests first:** `tests/test_app.py` and a focused version test if needed.

1. Add a failing assertion that the footer displays semantic version `0.1.0`
   alongside a normalized build SHA.
2. Add `APP_VERSION = "0.1.0"` to `services/version.py` and render both values
   in the footer.
3. Verify the focused test and full suite.

## Task 5 — Align public documentation and visual evidence

1. Update `README.md`, `README.zh-CN.md`, and `SECURITY.md` so they describe:
   two source modes; inert, unverified reference links; offline deterministic
   source processing; the explicit optional-model privacy boundary; and the
   customer-demo production boundary.
2. Add `CHANGELOG.md` with the `v0.1.0` safety-cut entry.
3. Remove crawler, SSRF-protection, DNS validation, redirect, and hard overall
   timeout claims everywhere outside historical design context.
4. Run the app through the managed `$PORT`/`0.0.0.0` start contract, inspect
   both source journeys, and replace `screenshots/overview.png` with a current
   paste-only interface capture that contains no customer or secret data.
5. Re-run textual scans for stale claims and inspect the staged diff.

## Task 6 — Local release verification and review

1. Run the complete verification suite from a clean process:

   ```bash
   PYTHONPATH=. python -m pytest -q tests
   python -m compileall -q app.py services tests
   python -m pip check
   git diff --check
   ```

2. Confirm the source tree contains no page-fetch module or public-page UI.
3. Confirm only the model client imports an outbound HTTP request primitive.
4. Commit in reviewable units, push the branch, and compare local HEAD with the
   matching remote branch SHA.
5. Open a pull request and wait for both Python matrix jobs and CodeQL/security
   checks that are configured for the repository.

## Task 7 — Merge, release, and synchronize public metadata

1. Merge only after required checks are successful and re-verify `main`.
2. Create annotated tag `v0.1.0` at the verified merge commit, push it, and
   publish a GitHub Release with concise behavior, limitations, and verification
   notes.
3. Update repository description and topics; remove `ssrf-protection` and
   `url-validation`.
4. After the Release URL exists, update the profile README's Market Research
   Brief entry to the same paste-only wording and send that change through its
   own repository checks.
5. Compare local and remote SHAs, confirm the public Release/tag target, inspect
   final CI/CodeQL status, and re-read the public README, screenshot, metadata,
   and profile entry as one evidence set.

## Acceptance checklist

- [ ] Exactly two source modes: synthetic example and pasted text.
- [ ] No public-page fetcher, DNS destination validator, redirect loop, or
      page-fetch UI remains in the released tree.
- [ ] Reference links are HTTP(S)-only, credential-free, fragment-free,
      syntactic metadata and cause no network access.
- [ ] Five-source and character limits remain enforced atomically.
- [ ] Deterministic report generation and Markdown/JSON/ZIP export still work.
- [ ] Optional model mode remains off by default with an explicit privacy note.
- [ ] Footer displays `v0.1.0` and build SHA.
- [ ] English/Chinese docs, screenshot, GitHub metadata, Release, and profile
      entry tell the same story.
- [ ] Local suite and remote Python 3.10/3.12 checks pass at the released commit.

