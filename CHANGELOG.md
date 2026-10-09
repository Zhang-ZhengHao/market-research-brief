# Changelog

All notable changes to this project are documented here.

## [0.1.0] - 2026-10-09

### Added

- Synthetic example and pasted-text research workflows.
- Source-order preservation and bounded verbatim evidence excerpts.
- Markdown, JSON, and deterministic ZIP project exports.
- Semantic application version and build identity.

### Changed

- Reference links are optional, user-supplied metadata only.
- Documentation states the optional model privacy boundary and human-review requirement.
- Optional model prompts omit reference links and send only accepted source titles and text.

### Removed

- Public webpage input and page retrieval.
- DNS destination checks, redirect handling, HTML extraction, and crawler-related claims.

### Security

- Source ingestion no longer resolves hostnames, opens sockets, or retrieves pages.
- Optional model summarization remains disabled by default and is the only intended outbound integration.
