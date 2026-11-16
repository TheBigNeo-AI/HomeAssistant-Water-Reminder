# Developer guide

## Versioning

Versions follow `<year>.<month>.<increment>` (e.g. `2026.10.2`), without zero-padding the month.

- The increment starts at `1` each month: `2026.11.1`, `2026.11.2`, `2026.12.1`.
- Pre-releases for testing append `b<n>`: `2026.11.1b1`, `2026.11.1b2`.
- `version` in `custom_components/water_reminder/manifest.json` must equal the release tag.
- `0.1.0` was the first release, before this scheme; `2026.x` versions sort above it.

## Local setup

```bash
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt ruff
ruff check . && ruff format --check .
pytest
```

## Testing a development version in Home Assistant

The Marketplace only installs releases (or the default branch while no release exists),
not arbitrary branches. To test unreleased code:

1. Set the manifest `version` on the branch to a pre-release, e.g. `2026.11.1b1`, and push.
2. GitHub → **Releases → Draft a new release**: tag `2026.11.1b1`, target = the branch,
   tick **Set as a pre-release**, publish.
3. Home Assistant → **Settings → Marketplace** → *Water Reminder* → turn on **Pre-release**,
   update, restart Home Assistant.
4. After testing, turn **Pre-release** off again.

## Release

1. Merge the PR into `main`.
2. Set the manifest `version` to the final version (e.g. `2026.11.1`) on `main`.
3. GitHub → **Releases → Draft a new release**: tag = manifest version, target `main`, publish.

## CI

One workflow (`.github/workflows/ci.yaml`) on pull requests and pushes to `main`, no
schedule: shared secret scan, Marketplace validation + hassfest, ruff + pytest.
