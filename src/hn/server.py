"""FastMCP server exposing the HackerNews API as MCP tools.

Run it directly for stdio transport (the default used by MCP clients like
Claude Desktop / Claude Code)::

    hn-mcp
    # or
    python -m hn.server
    # or, over HTTP:
    hn-mcp --http --port 8000
"""

from __future__ import annotations

import argparse
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from .client import STORY_ENDPOINTS, HNClient

mcp = FastMCP(
    name="HackerNews",
    instructions=(
        "Tools for the official HackerNews API. Use `get_stories` for the front "
        "page and category lists (top/new/best/ask/show/job), `get_item` for a "
        "single story/comment/job/poll, `get_comments` for a threaded discussion, "
        "and `get_user` for profiles. Item and comment `text` fields contain HTML. "
        "Timestamps are Unix epoch seconds."
    ),
)

StoryCategory = Literal["top", "new", "best", "ask", "show", "job"]

HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"
HN_USER_URL = "https://news.ycombinator.com/user?id={id}"


@mcp.tool
async def get_stories(
    category: Annotated[
        StoryCategory,
        Field(description="Which list: top, new, best, ask, show, or job stories."),
    ] = "top",
    limit: Annotated[
        int,
        Field(ge=1, le=500, description="How many stories to return (1-500)."),
    ] = 30,
) -> list[dict[str, Any]]:
    """Get a list of HackerNews stories from a category, with full details.

    'top', 'new' and 'best' draw from up to 500 stories; 'ask', 'show' and
    'job' from up to 200. Each result includes title, url, score, author,
    comment count and the canonical HN discussion link.
    """
    async with HNClient() as hn:
        stories = await hn.get_stories(category, limit=limit)
    return [_with_links(s.model_dump(exclude_none=True)) for s in stories]


@mcp.tool
async def get_item(
    item_id: Annotated[int, Field(description="The item's numeric id.")],
) -> dict[str, Any] | None:
    """Get a single HackerNews item (story, comment, job, poll, or poll option).

    Returns null if no item exists with that id.
    """
    async with HNClient() as hn:
        item = await hn.get_item(item_id)
    return _with_links(item.model_dump(exclude_none=True)) if item else None


@mcp.tool
async def get_comments(
    item_id: Annotated[int, Field(description="Id of the story or comment to expand.")],
    max_depth: Annotated[
        int,
        Field(ge=0, le=5, description="Reply nesting depth (0 = top-level comments only)."),
    ] = 1,
    max_per_level: Annotated[
        int,
        Field(ge=1, le=100, description="Max comments to expand per level."),
    ] = 30,
) -> list[dict[str, Any]]:
    """Get the threaded comment tree for an item.

    Each comment includes a nested `replies` list bounded by `max_depth` and
    `max_per_level`. Comment `text` is HTML.
    """
    async with HNClient() as hn:
        return await hn.get_comments(item_id, max_depth=max_depth, max_per_level=max_per_level)


@mcp.tool
async def get_user(
    username: Annotated[str, Field(description="The exact, case-sensitive HackerNews username.")],
) -> dict[str, Any] | None:
    """Get a HackerNews user's public profile (karma, about, created, submissions).

    Returns null if the user has no public activity or does not exist.
    """
    async with HNClient() as hn:
        user = await hn.get_user(username)
    if user is None:
        return None
    data = user.model_dump(exclude_none=True)
    data["hn_url"] = HN_USER_URL.format(id=user.id)
    return data


@mcp.tool
async def get_max_item_id() -> int:
    """Get the id of the most recently created item, useful for walking all items."""
    async with HNClient() as hn:
        return await hn.get_max_item_id()


@mcp.tool
async def get_updates() -> dict[str, Any]:
    """Get the items and user profiles that changed most recently."""
    async with HNClient() as hn:
        updates = await hn.get_updates()
    return updates.model_dump()


def _with_links(data: dict[str, Any]) -> dict[str, Any]:
    """Add the canonical HN discussion link to an item dict."""
    if "id" in data:
        data["hn_url"] = HN_ITEM_URL.format(id=data["id"])
    return data


def main() -> None:
    """Console-script entry point. Defaults to stdio transport."""
    parser = argparse.ArgumentParser(description="HackerNews FastMCP server")
    parser.add_argument("--http", action="store_true", help="Serve over HTTP instead of stdio.")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port.")
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


# Guard against `STORY_ENDPOINTS` drifting from the tool's Literal categories.
assert set(STORY_ENDPOINTS) == set(StoryCategory.__args__)  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
