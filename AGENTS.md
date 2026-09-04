# AGENTS.md

Guidance for AI coding agents working in this repository. Follow these rules
unless the task says otherwise.

## What this is

A read-only client for the official HackerNews API. One shared async client
backs two entry points:

- `hn`, a Typer CLI (`src/hn/cli.py`) for the terminal.
- `hn-mcp`, a FastMCP server (`src/hn/server.py`) that exposes the same
  operations as MCP tools.

The layers, in order:

- `src/hn/client.py` owns every network call. Keep the CLI and the server thin
  over it, so the two interfaces never drift. It handles the bounded concurrency
  and the API's `null` sentinel for missing resources.
- `src/hn/models.py` holds the Pydantic models. `StoryCategory` is the single
  source of truth for the six story lists (its endpoint stem, display title,
  and story-list cap). Add a category or a model field here, not in each
  interface.
- `src/hn/cli.py` and `src/hn/server.py` do formatting and wire-up only.
- `skills/hackernews/SKILL.md` is the agent-facing skill. It is the source of
  truth. The copies under `.claude/skills/` and `.agents/skills/` are local
  installs from the skills CLI; edit the source, not the copies. The root
  `skills-lock.json` records that install.

The tools and CLI are read-only by design. The API has no authentication and no
rate limit. Timestamps are Unix epoch seconds. The `title`, `text`, and `about`
fields contain HTML.

## Commands

```bash
uv sync                          # install dependencies
uv run hn stories top            # run the CLI
uv run hn-mcp                    # run the MCP server
uv run ruff check .              # lint
uv run ruff format .             # format (`ruff format --check .` in CI)
uv run pytest                    # tests, every API call mocked with respx
uv build                         # build dist/ artifacts (gitignored)
```

Install the skill (regenerates the local copies and `skills-lock.json`):

```bash
npx skills add Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI
```

## Change rules

- When behavior changes, update the docs in the same change: `README.md`,
  `CONTRIBUTING.md`, `RELEASING.md`, `skills/hackernews/SKILL.md`, and this
  file. Do not ship a behavior change without its doc update.
- Change the smallest file that solves the problem. Do not add a layer or an
  abstraction for one call site.
- Name the real command, flag, file, or symbol, not a description of it.
- Keep the CLI and the MCP server calling the same client methods. If a method
  changes in `client.py`, update both callers in that change.
- Add or update tests for behavior changes. Client and server tests mock the
  API with `respx`. CLI tests use `typer.testing.CliRunner`.

## Release rule

- Do not bump the version, create a tag, or push a tag (`vX.Y.Z`) unless the
  user explicitly asks to publish. Publishing uploads to PyPI. Treat a version
  bump or a tag push as pending explicit instruction.
- When told to publish, follow `RELEASING.md`. Keep `pyproject.toml`,
  `src/hn/__init__.py`, and the bug-report placeholder version in sync. Run
  `uv build` and the checks, commit and push `main`, then tag and push.

## Writing style

Prose in this repository follows the poteto-mode standards. Apply these skills:

- `/technical-writing` and `/unslop` to any prose you write or edit.
- `/no-comments` before a review.
- `/unslop` in place of `/deslop` before a commit, since deslop is a
  cursor-team-kit skill and is not available in this opencode setup.

Rules to follow: plain words, active voice, instructions as commands, no em
dashes, no slashes between words in prose, serial commas, and the same name for
the same thing everywhere.
