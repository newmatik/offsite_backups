# Offsite Backups

Offsite Backups sends Frappe site backups to S3-compatible storage, Dropbox, or
Google Drive.

## Requirements

- Frappe Framework v16
- Python 3.14
- Node.js 24, MariaDB, and Redis as required by the parent bench

## Installation

Install the default `version-16` branch from the bench root:

```bash
bench get-app --branch version-16 offsite_backups \
  git@github.com:newmatik/offsite_backups.git
bench --site <sitename> install-app offsite_backups
bench --site <sitename> migrate
```

Use an exact release SHA when reproducing production. The full Newmatik app
order and parity workflow are documented in
[`docs/developer-bench-v16.md`](https://github.com/newmatik/eso-newmatik/blob/version-16/docs/developer-bench-v16.md).

## Configuration

Configure only the provider used by the site:

- **S3 Backup Settings** for S3-compatible object storage
- **Dropbox Settings** for Dropbox
- **Google Drive** for Google Drive

Provider credentials belong in these site DocTypes. Never commit access keys,
refresh tokens, downloaded credentials, backup archives, or production site
configuration. Confirm a complete database-and-files backup and a restore test
before relying on a provider for disaster recovery.

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/offsite_backups
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier

## CI

GitHub Actions workflows:

- CI: Installs Frappe v16 and this app, then runs unit tests on pull requests
  and pushes to the default `version-16` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.

## License

MIT
