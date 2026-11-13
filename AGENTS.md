# Offsite Backups

Frappe v16 app that uploads site backups to S3-compatible storage, Dropbox or
Google Drive. This is Newmatik's fork of `frappe/offsite_backups`; it carries
fixes the upstream project has not taken.

## This repository is public

Never add customer names, addresses, real data, site names, server addresses,
credentials, tokens or backup contents to code, tests, fixtures, commits, issues
or pull requests. Tests use synthetic values and a mocked provider client.

## Backups are production safety

- Never trigger, delete or restore a backup to test a change. Never call a real
  provider from a test.
- A failed or incomplete upload must fail the run. Do not record success, update
  a "last backup" field or send a success mail after an error.
- Automatic deletion of old backups at the provider is switched off on purpose
  (see the comment in `dropbox_settings.py`). Do not re-enable it without the
  owner's decision.
- Methods that store a token or start a backup begin with
  `frappe.only_for("System Manager")`; `test_backup_role.py` enforces this.

## Layout

| Path | Content |
|---|---|
| `offsite_backups/hooks.py` | Scheduler events for the three providers |
| `offsite_backups/offsite_backups/offsite_backup_utils.py` | Shared snapshot selection, lock and status mail |
| `offsite_backups/offsite_backups/doctype/<provider>/` | Settings DocType, upload code and tests per provider |

## Work on a change

- Default branch: `version-16`. Branch from `origin/version-16`, open a pull
  request, squash-merge. Do not push to `version-16` directly.
- Lint: `ruff check .` and `ruff format --check .` (also run by `pre-commit`).
- Tests: `bench --site <test site> run-tests --app offsite_backups` on a local
  developer bench. The classes named `UnitTest*` need no site and run with
  `python -m unittest` in a bench environment that has the provider SDKs.
- CI on every pull request: `Server` (bench tests), `Frappe Linter` (pre-commit
  and Semgrep), `Vulnerable Dependency Check` (pip-audit).
- Get an independent review before merging; green CI is not a review.

## Deployment

The app runs on Newmatik's production ERP bench. A merge deploys nothing by
itself. Production deploys follow the procedure in the private `eso-newmatik`
repository (`deploy/production/`): merged revisions only, one deploy at a time,
never by hand-typed commands on the server. A change to runtime dependencies in
`pyproject.toml` or to the DocType schema cannot go out online and needs a
planned release.
