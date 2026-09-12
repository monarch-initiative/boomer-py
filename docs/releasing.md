# Releasing to PyPI

BOOMER uses the same tools as `linkml-term-validator`: `uv build`, Hatch with
`uv-dynamic-versioning`, and the PyPA publishing action with GitHub OIDC trusted
publishing. The PyPI distribution name is `boomer` and the import name is `boomer`.

## One-time setup

Before the first release, sign in to [PyPI account publishing](https://pypi.org/manage/account/publishing/)
and add a pending GitHub publisher with these exact values:

| Field | Value |
| --- | --- |
| PyPI project name | `boomer` |
| Owner | `monarch-initiative` |
| Repository | `boomer-py` |
| Workflow filename | `pypi-publish.yaml` |
| Environment | `release` |

The workflow filename has no directory prefix. The environment name must match
the GitHub Actions job. Create the `release` environment in the repository's
GitHub settings if it does not already exist.

A pending publisher creates the PyPI project on the first successful upload; it
does not reserve the name. See [PyPI's pending-publisher documentation](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
No PyPI API token or password is needed in GitHub secrets.

## Publish a release

1. Merge the intended changes into `main` and check that CI passes.
2. Open [New release](https://github.com/monarch-initiative/boomer-py/releases/new).
3. Create a new tag such as `v0.1.0`, targeting `main`, and enter release notes.
4. Click **Publish release**. Saving a draft does not publish to PyPI.
5. Follow the **Publish Python Package** workflow in GitHub Actions, then check
   [boomer on PyPI](https://pypi.org/project/boomer/).

The tag supplies the package version: `v0.1.0` builds `boomer==0.1.0`. Use
PEP 440 version tags, such as `v0.2.0rc1` for release candidates. Publishing a
GitHub prerelease also uploads to PyPI, so give it a prerelease version tag.
There is no version constant to bump in `pyproject.toml`.

The workflow fetches Git history and tags, builds the source archive and wheel,
checks the wheel version against the release tag, and uploads using trusted
publishing. PyPI does not allow replacing an uploaded distribution; corrections
need a new version/tag.

## Local build check

Run `uv build --no-sources` to build both distributions under `dist/`. Untagged
checkouts produce development versions (or the configured `0.0.0` fallback
before any version tag exists). CI also builds distributions on pull requests.
