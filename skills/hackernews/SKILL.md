---
name: hackernews
description: >-
  Browse and query HackerNews from the command line using the `hn` CLI (or the
  paired FastMCP server). Use this skill whenever the user wants HackerNews
  content: the front page / top stories, new / best / Ask HN / Show HN / job
  posts, a specific story or comment by id, a threaded comment discussion, a
  user's profile and karma, the latest item id, or recently changed items. Also
  use for scripting over HackerNews data (the `--json` flag emits raw JSON for
  piping into `jq`). Triggers include "what's on Hacker News", "top HN stories",
  "show me Ask HN", "look up HN user pg", "get the comments on this HN post".
---

# HackerNews CLI & MCP

A read-only client for the official HackerNews API
(https://github.com/HackerNews/API). Ships two entry points backed by one shared
async client, so behavior is identical between them:

- **`hn`** — a Typer CLI with Rich tables (best for interactive/terminal use).
- **`hn-mcp`** — a FastMCP server exposing the same operations as MCP tools
  (best when driving HackerNews from an MCP client like Claude Desktop).

The API needs no authentication and has no rate limit. Timestamps are Unix
epoch seconds. `title`/`text`/`about` fields contain HTML.

## Setup

From the project root (uses `uv`):

```bash
uv sync
```

Then run either `uv run hn ...` (no install) or install the console scripts with
`uv pip install -e .` and call `hn` / `hn-mcp` directly.

## CLI usage

Every command takes `--json` to emit raw JSON instead of a table — use it when
you need to parse the output.

### Story lists

```bash
hn top                 # front-page (top) stories, 30 by default
hn top --limit 10      # or -n 10
hn new                 # newest stories
hn best                # best recent stories
hn ask                 # latest Ask HN posts
hn show                # latest Show HN posts
hn jobs                # latest job postings
```

`top`/`new`/`best` draw from up to 500 stories; `ask`/`show`/`jobs` from up to
200. `--limit` is capped accordingly.

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

`--depth 0` shows only top-level comments (no replies expanded). Depth is capped
at 5 and limit at 100 per level to bound the number of API calls.

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
hn top -n 5 --json | jq -r '.[] | "\(.title) — \(.url // .hn_url)"'

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
example, in a Claude Desktop / Claude Code MCP config:

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
| `get_stories(category, limit)` | Story list; category = top/new/best/ask/show/job |
| `get_item(item_id)` | One story/comment/job/poll (null if missing) |
| `get_comments(item_id, max_depth, max_per_level)` | Threaded comment tree |
| `get_user(username)` | Public profile (null if no public activity) |
| `get_max_item_id()` | Id of the newest item |
| `get_updates()` | Recently changed items and profiles |

Every item/story result includes an added `hn_url` pointing at the canonical
`news.ycombinator.com` discussion page.

## Notes & gotchas

- **Missing data returns null**, not an error: unknown item ids and users
  without public activity come back as `null` (CLI exits non-zero with a
  message).
- **HTML in text fields**: `text`, `title`, and `about` may contain HTML
  entities and tags. The CLI strips them for display; the MCP/`--json` output
  preserves them raw.
- **`get_stories` fans out** one request per story, so large `--limit` values
  mean many API calls (done concurrently, but still be reasonable).
- **No search endpoint**: the official API has no full-text search. To find a
  story you must already have its id, or scan a category list.
