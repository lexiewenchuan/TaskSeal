# Changelog

All notable TaskSeal changes are documented here.

The project follows semantic versioning while the public API remains in early
alpha.

## 0.1.1

### Added

- Trusted root authorizers and recorded grant provenance
- Authorization revocation with an audit event
- Trusted independent verifier configuration
- External SHA-256 file evidence re-verification
- Work Item domain validation before persistence and after loading
- A plan-step completion API and executable repair-to-planning flow
- Python 3.9 through 3.13 continuous-integration coverage

### Changed

- The runtime, SQLite snapshots, CLI output, example and JSON Schema now share
  one canonical Work Item contract.
- Unsupported free-form authorization conditions now fail closed.
- Verification requires completed plan steps, artifacts and evidence.
- Legacy snapshots remain readable; unverifiable legacy grants are migrated as
  revoked instead of being trusted implicitly.

### Fixed

- ISO 8601 timestamps ending in `Z` now work on Python 3.9.
- Empty acceptance criteria and illegal initial task state can no longer be
  persisted.
- Fabricated or stale local file evidence can no longer pass acceptance.

## 0.1.0

- Initial local reference kernel with task state, scoped authorization, a local
  file gateway, evidence records, independent acceptance, SQLite persistence
  and a runnable CLI demo.
