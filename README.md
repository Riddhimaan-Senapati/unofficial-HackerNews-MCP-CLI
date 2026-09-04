<h1 align="center">unofficial-HackerNews-MCP-CLI</h1>

<p align="center">
  An unofficial HackerNews MCP server and CLI. Reads the top, new, best, Ask, Show, and job story lists, individual items, threaded comments, and user profiles through one shared async client. Built with FastMCP and Typer.
</p>

<p align="center">
  <a href="https://pypi.org/project/hackernews-mcp-cli/"><img src="https://img.shields.io/pypi/v/hackernews-mcp-cli.svg?cacheSeconds=200" alt="PyPI version"></a>
  <a href="https://pypi.org/project/hackernews-mcp-cli/"><img src="https://img.shields.io/pypi/dm/hackernews-mcp-cli.svg?cacheSeconds=60" alt="PyPI downloads"></a>
  <a href="https://github.com/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI/actions/workflows/ci.yml"><img src="https://github.com/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI/actions/workflows/release.yml"><img src="https://github.com/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI/actions/workflows/release.yml/badge.svg" alt="Release workflow"></a>
  <a href="https://skills.sh/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI"><img src="https://skills.sh/b/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI" alt="skills.sh"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI.svg" alt="license"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
</p>

<p align="center">
  <a href="#install">Install</a> •
  <a href="#cli">CLI</a> •
  <a href="#mcp-server">MCP server</a> •
  <a href="#skill">Skill</a> •
  <a href="./CONTRIBUTING.md">Contributing</a>
</p>

This project wraps the official [HackerNews API](https://github.com/HackerNews/API)
behind one shared async client and exposes it two ways:

- `hn`, a Typer CLI that renders Rich tables in the terminal.
- `hn-mcp`, a FastMCP server that exposes the same operations as MCP tools for
  Claude and other MCP clients.

The API is read-only, needs no authentication, and has no rate limit.

## Install

Requires Python 3.10+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                    # create the venv and install
uv run hn stories top     # run the CLI without installing scripts
# or install the console scripts (hn, hn-mcp) into the environment:
uv pip install -e .
```

## CLI

```bash
hn stories top             # front-page (top) stories
hn stories top --limit 10  # -n 10
hn stories new             # newest stories
hn stories best            # best recent stories
hn stories ask             # latest Ask HN
hn stories show            # latest Show HN
hn stories job             # latest job postings

hn item 8863               # a single story, comment, job, or poll
hn comments 8863           # threaded comment tree (--depth, --limit)
hn user pg                 # a user's profile (case-sensitive name)

hn max-item                # id of the most recently created item
hn updates                 # recently changed items and profiles

hn --version               # print the installed version
```

Add `--json` to any command to get raw JSON instead of a table, for scripting:

```bash
hn stories top -n 5 --json | jq -r '.[] | "\(.title) (\(.url // .hn_url))"'
hn user pg --json | jq .karma
```

Run `hn --help` for the full command list, or `hn <command> --help` for that
command's options and examples.

## MCP server

Run over stdio, the default transport for MCP clients:

```bash
hn-mcp
```

Or over HTTP:

```bash
hn-mcp --http --host 127.0.0.1 --port 8000
```

Register it with an MCP client such as Claude Desktop or Claude Code:

```json
{
  "mcpServers": {
    "hackernews": { "command": "hn-mcp" }
  }
}
```

### Tools

| Tool | Description |
|------|-------------|
| `get_stories(category, limit)` | A list of stories; `category` is one of `top`, `new`, `best`, `ask`, `show`, or `job` |
| `get_item(item_id)` | A single story, comment, job, or poll |
| `get_comments(item_id, max_depth, max_per_level)` | Threaded comment tree |
| `get_user(username)` | A user's public profile |
| `get_max_item_id()` | id of the most recently created item |
| `get_updates()` | Items and profiles that changed most recently |

## Skill

[`skills/hackernews/SKILL.md`](skills/hackernews/SKILL.md) is an Agent Skill that
teaches an agent how and when to use the `hn` CLI and the `hn-mcp` MCP server.
It is published on [skills.sh](https://skills.sh/). Install it with the skills
CLI, or add the console scripts and let your agent load it from this directory:

```bash
npx skills add Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI
```

## Project layout

```
src/hn/
  client.py   # shared async HackerNews API client (httpx)
  models.py   # Pydantic models + StoryCategory (endpoint, title, cap)
  server.py   # FastMCP server (hn-mcp)
  cli.py      # Typer CLI (hn)
skills/hackernews/SKILL.md
tests/        # pytest + respx (mocked API)
```

### How it works

`client.py` owns every network call and bounds concurrency. `server.py` and
`cli.py` stay thin over it, so the CLI and the MCP tools behave identically.
`StoryCategory` in `models.py` is the single source of truth for the six story
lists: it holds a category's endpoint stem, display title, and cap. Add a
category or a model field there, not in each interface.

Changing behavior also means updating the docs in the same change: README,
CONTRIBUTING, RELEASING, the agent skill, and AGENTS.md. Only the maintainer
publishes a release, so follow RELEASING.md and push a tag only when asked.

Read [AGENTS.md](AGENTS.md) for the agent-facing rules, and
[CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

## Development

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run pytest                # test suite (API calls are mocked)
```

CI runs lint, formatting, and the test suite on Python 3.10 through 3.13 via
GitHub Actions. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

## License

MIT. See [LICENSE](LICENSE). This is an unofficial project and is not affiliated
with Hacker News or Y Combinator.
