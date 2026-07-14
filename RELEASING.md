# Releasing

This project publishes to [PyPI](https://pypi.org/project/hackernews-mcp-cli/)
through GitHub Actions. Pushing a version tag such as `v0.1.0` triggers
[`.github/workflows/release.yml`](.github/workflows/release.yml), which builds
the package, uploads it to PyPI, and creates a GitHub Release.

Publishing uses PyPI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
(OIDC). PyPI trusts this repository and workflow directly, so there is no API
token or secret stored in the repo.

## One-time PyPI setup

Do this once, before the first tag. The `hackernews-mcp-cli` project does not
exist on PyPI yet, so you register a *pending* publisher. It becomes a normal
trusted publisher after the first successful upload.

1. Log in at [pypi.org](https://pypi.org) and enable 2FA (PyPI requires it for
   uploads).
2. Open <https://pypi.org/manage/account/publishing/>.
3. Under "Add a new pending publisher", enter exactly:
   - PyPI Project Name: `hackernews-mcp-cli`
   - Owner: `Riddhimaan-Senapati`
   - Repository name: `unofficial-HackerNews-MCP-CLI`
   - Workflow name: `release.yml`
   - Environment name: leave blank (the workflow declares no environment)
4. Click Add.

No secrets are added to GitHub.

## Cutting a release

The version comes from the `version` field in
[`pyproject.toml`](pyproject.toml), so keep the tag and that field in sync.

1. Bump `version` in `pyproject.toml` (for example `0.2.0`).
2. Commit and push `main`.
3. Tag and push:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

Pushing the tag runs the release workflow, which:

1. builds the sdist and wheel with `uv build`,
2. publishes them to PyPI via Trusted Publishing,
3. creates a GitHub Release with generated notes and the built files attached.

Track progress under the repository's Actions tab, in the Release workflow.

PyPI rejects re-uploading a version that already exists, so every release needs
a new version number.

## Verifying

After the workflow finishes:

```bash
uvx hackernews-mcp-cli --help
# or
pipx install hackernews-mcp-cli && hn top
```

## Notes

- If you push a tag before finishing the one-time PyPI setup, the publish step
  fails while the build and GitHub Release steps still succeed. Finish the setup,
  then re-run the workflow from Actions, Release, Run workflow.
- To rehearse on TestPyPI, register the same pending publisher at
  [test.pypi.org](https://test.pypi.org), then temporarily add
  `with: { repository-url: https://test.pypi.org/legacy/ }` to the
  `pypa/gh-action-pypi-publish` step.
- Token fallback if you ever stop using OIDC: create a scoped token at pypi.org
  under Account, API tokens, store it as the `PYPI_API_TOKEN` repository secret,
  and add `with: { password: ${{ secrets.PYPI_API_TOKEN }} }` to the publish
  step. Trusted Publishing is the recommended default.
