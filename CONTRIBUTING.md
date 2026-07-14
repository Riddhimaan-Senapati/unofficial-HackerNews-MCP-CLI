# Contributing

Thanks for your interest in improving **unofficial-HackerNews-MCP-CLI**!

## Development setup

Requires Python 3.10+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --dev        # install runtime + dev dependencies
```

## Before you open a PR

Run the same checks CI runs:

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formatting (drop --check to auto-format)
uv run pytest -q             # tests (all API calls are mocked)
```

CI runs the test suite on Python 3.10–3.13, so please keep changes compatible
across those versions.

## Guidelines

- Keep the CLI (`src/hn/cli.py`) and MCP server (`src/hn/server.py`) thin — they
  should delegate to the shared async client in `src/hn/client.py` so the two
  interfaces never drift.
- Tests mock the HackerNews API with `respx`; don't make real network calls in
  tests.
- The HackerNews API is read-only. This project intentionally exposes no
  write/authenticated operations.

## Reporting bugs & requesting features

Open an issue with clear reproduction steps or a description of the desired
behavior.
