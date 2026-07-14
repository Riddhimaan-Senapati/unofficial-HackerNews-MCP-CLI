# unofficial-HackerNews-MCP-CLI

[![CI](https://github.com/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI/actions/workflows/ci.yml/badge.svg)](https://github.com/Riddhimaan-Senapati/unofficial-HackerNews-MCP-CLI/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Unofficial] A HackerNews **MCP server** and **CLI**, built with
[FastMCP](https://gofastmcp.com) and [Typer](https://typer.tiangolo.com).

Wraps the official [HackerNews API](https://github.com/HackerNews/API) behind a
single shared async client, exposed two ways:

- **`hn`** — a Typer command-line client with Rich-formatted output.
- **`hn-mcp`** — a FastMCP server exposing the same operations as MCP tools for
  use with Claude and other MCP clients.

The API is read-only, needs no authentication, and has no rate limit.

## Install

Requires Python 3.10+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                    # create the venv and install
uv run hn top              # run the CLI without installing scripts
# or install the console scripts (hn, hn-mcp) into the environment:
uv pip install -e .
```

## CLI

```bash
hn top                 # front-page (top) stories
hn top --limit 10      # -n 10
hn new                 # newest stories
hn best                # best recent stories
hn ask                 # latest Ask HN
hn show                # latest Show HN
hn jobs                # latest job postings

hn item 8863           # a single story/comment/job/poll
hn comments 8863       # threaded comment tree (--depth, --limit)
hn user pg             # a user's profile (case-sensitive name)

hn max-item            # id of the most recently created item
hn updates             # recently changed items and profiles
```

Add `--json` to any command to emit raw JSON for scripting:

```bash
hn top -n 5 --json | jq -r '.[] | "\(.title) — \(.url // .hn_url)"'
hn user pg --json | jq .karma
```

Run `hn --help` for the full command list.

## MCP server

Run over stdio (the transport MCP clients use by default):

```bash
hn-mcp
```

…or over HTTP:

```bash
hn-mcp --http --host 127.0.0.1 --port 8000
```

Register it with an MCP client (e.g. Claude Desktop / Claude Code):

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
| `get_stories(category, limit)` | Story list — category = `top`/`new`/`best`/`ask`/`show`/`job` |
| `get_item(item_id)` | A single story, comment, job, or poll |
| `get_comments(item_id, max_depth, max_per_level)` | Threaded comment tree |
| `get_user(username)` | A user's public profile |
| `get_max_item_id()` | Id of the most recently created item |
| `get_updates()` | Items and profiles that changed most recently |

## Skill

[`skills/hackernews/SKILL.md`](skills/hackernews/SKILL.md) is an agent skill
teaching Claude how and when to use the `hn` CLI and MCP server.

## Project layout

```
src/hn/
  client.py   # shared async HackerNews API client (httpx)
  models.py   # Pydantic models for items and users
  server.py   # FastMCP server (hn-mcp)
  cli.py      # Typer CLI (hn)
skills/hackernews/SKILL.md
tests/        # pytest + respx (mocked API)
```

## Development

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run pytest                # test suite (API calls are mocked)
```

CI (GitHub Actions) runs lint, format, and the test suite on Python 3.10–3.13.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

## License

MIT — see [LICENSE](LICENSE). This is an unofficial project and is not
affiliated with Hacker News or Y Combinator.
