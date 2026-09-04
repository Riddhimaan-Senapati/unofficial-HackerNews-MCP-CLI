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
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from .client import HNClient
from .models import Comment, Item, StoryCategory, Updates, User

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


@mcp.tool
async def get_stories(
    category: Annotated[
        StoryCategory,
        Field(description="Which list: top, new, best, ask, show, or job stories."),
    ] = StoryCategory.top,
    limit: Annotated[
        int,
        Field(ge=1, le=500, description="How many stories to return (1-500)."),
    ] = 30,
) -> list[Item]:
    """Get a list of HackerNews stories from a category, with full details.

    'top', 'new' and 'best' draw from up to 500 stories; 'ask', 'show' and
    'job' from up to 200. Each result includes title, url, score, author,
    comment count and the canonical HN discussion link.
    """
    async with HNClient() as hn:
        return await hn.get_stories(category, limit=limit)


@mcp.tool
async def get_item(
    item_id: Annotated[int, Field(description="The item's numeric id.")],
) -> Item | None:
    """Get a single HackerNews item (story, comment, job, poll, or poll option).

    Returns null if no item exists with that id.
    """
    async with HNClient() as hn:
        return await hn.get_item(item_id)


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
) -> list[Comment]:
    """Get the threaded comment tree for an item.

    Each comment includes a nested `replies` list bounded by `max_depth` and
    `max_per_level`. Comment `text` is HTML.
    """
    async with HNClient() as hn:
        return await hn.get_comments(item_id, max_depth=max_depth, max_per_level=max_per_level)


@mcp.tool
async def get_user(
    username: Annotated[str, Field(description="The exact, case-sensitive HackerNews username.")],
) -> User | None:
    """Get a HackerNews user's public profile (karma, about, created, submissions).

    Returns null if the user has no public activity or does not exist.
    """
    async with HNClient() as hn:
        return await hn.get_user(username)


@mcp.tool
async def get_max_item_id() -> int:
    """Get the id of the most recently created item, useful for walking all items."""
    async with HNClient() as hn:
        return await hn.get_max_item_id()


@mcp.tool
async def get_updates() -> Updates:
    """Get the items and user profiles that changed most recently."""
    async with HNClient() as hn:
        return await hn.get_updates()


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


if __name__ == "__main__":
    main()
