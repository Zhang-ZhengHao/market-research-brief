# Changelog

All notable changes to this project are documented here.

## [0.1.1] - 2026-11-10

### Added

- A synthetic sample brief (`examples/synthetic-brief.md`) showing the exported output format.
- A Windows quick start in the English and Chinese READMEs.
- A bilingual public project-inquiry entry in both READMEs.

### Changed

- The industry weekly template now uses the intended report angle.

### Fixed

- Exports are now explicitly labeled as synthetic demonstration output.

### Security

- The runtime now requires Python 3.11 and a patched Pillow release.

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
