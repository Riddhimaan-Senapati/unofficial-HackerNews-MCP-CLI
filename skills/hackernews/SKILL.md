---
name: hackernews
description: >-
  Browse and query HackerNews from the command line using the `hn` CLI (or the
  paired FastMCP server). Use this skill whenever the user wants HackerNews
  content: the front page and top stories, the new, best, Ask HN, Show HN, and
  job posts, a specific story or comment by id, a threaded comment discussion, a
  user's profile and karma, the latest item id, or recently changed items. Also
  use it for scripting over HackerNews data (the `--json` flag emits raw JSON
  for piping into `jq`). Triggers include "what's on Hacker News", "top HN
  stories", "show me Ask HN", "look up HN user pg", and "get the comments on
  this HN post".
license: MIT
author:
  name: Riddhimaan Senapati
  url: https://github.com/Riddhimaan-Senapati
---

# HackerNews CLI & MCP

A read-only client for the official HackerNews API
(https://github.com/HackerNews/API). It ships two entry points over one shared
async client, so both behave the same way:

- **`hn`**, a Typer CLI with Rich tables, for terminal use.
- **`hn-mcp`**, a FastMCP server exposing the same operations as MCP tools, for
  MCP clients like Claude Desktop.

The API needs no authentication and has no rate limit. Timestamps are Unix
epoch seconds. The `title`, `text`, and `about` fields contain HTML.

## Setup

From the project root (uses `uv`):

```bash
uv sync
```

Then run either `uv run hn ...` (no install) or install the console scripts with
`uv pip install -e .` and call `hn` or `hn-mcp` directly.

## CLI usage

Every command takes `--json` to emit raw JSON instead of a table. Use it when
you need to parse the output.

### Story lists

```bash
hn stories top                 # front-page (top) stories, 30 by default
hn stories top --limit 10      # or -n 10
hn stories new                 # newest stories
hn stories best                # best recent stories
hn stories ask                 # latest Ask HN posts
hn stories show                # latest Show HN posts
hn stories job                 # latest job postings
```

The top, new, and best lists draw from up to 500 stories. The ask, show, and job
lists draw from up to 200. A `--limit` over the category's cap exits non-zero
with a suggestion.

### A single item

```bash
hn item 8863           # story, comment, job, or poll by id
```

### A comment thread

```bash
hn comments 8863               # top-level comments + one level of replies
hn comments 8863 --depth 2     # nest replies 2 levels deep (-d)
hn comments 8863 --limit 50    # up to 50 comments per level (-n)
```

`--depth 0` shows only top-level comments (no replies expanded). Depth is
capped at 5, and limit is capped at 100 per level. These caps bound the number
of API calls.

### A user

```bash
hn user pg             # profile: karma, account age, submission count, about
```

Usernames are **case-sensitive**.

### Live data

```bash
hn max-item            # id of the most recently created item
hn updates             # items and profiles that changed most recently
```

### Scripting examples

```bash
# Titles + links of the top 5 stories
hn stories top -n 5 --json | jq -r '.[] | "\(.title) | \(.url // .hn_url)"'

# pg's karma
hn user pg --json | jq .karma

# Score of a specific story
hn item 8863 --json | jq .score
```

## MCP server usage

Run over stdio (the default for MCP clients):

```bash
hn-mcp
```

Or over HTTP:

```bash
hn-mcp --http --host 127.0.0.1 --port 8000
```

Register it with an MCP client by pointing at the `hn-mcp` command (stdio). For
example, in a Claude Desktop or Claude Code MCP config:

```json
{
  "mcpServers": {
    "hackernews": { "command": "hn-mcp" }
  }
}
```

### Tools exposed

| Tool | Purpose |
|------|---------|
| `get_stories(category, limit)` | Story list; category is one of `top`, `new`, `best`, `ask`, `show`, or `job` |
| `get_item(item_id)` | One story, comment, job, or poll (null if missing) |
| `get_comments(item_id, max_depth, max_per_level)` | Threaded comment tree |
| `get_user(username)` | Public profile (null if no public activity) |
| `get_max_item_id()` | id of the newest item |
| `get_updates()` | Recently changed items and profiles |

Every item and story result includes an `hn_url` pointing at the canonical
`news.ycombinator.com` discussion page.

## Notes and gotchas

- Missing data returns `null`, not an error. Unknown item ids and users without
  public activity come back as `null`; the CLI exits non-zero with a message.
- HTML lives in the text fields. The `text`, `title`, and `about` fields may
  contain HTML entities and tags. The CLI strips them for display; the MCP
  server and `--json` output preserve them raw.
- `get_stories` sends one request per story, so a large `--limit` means many
  requests. The requests run concurrently, so keep the limit modest.
- The official API has no full-text search. To find a story, you need its id,
  or you scan a category list.
