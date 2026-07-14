"""Tests for the FastMCP server, exercised via an in-memory client."""

from __future__ import annotations

import httpx
import respx
from fastmcp import Client

from hn.client import BASE_URL
from hn.server import mcp

STORY = {
    "id": 8863,
    "type": "story",
    "by": "dhouston",
    "title": "My YC app: Dropbox",
    "score": 104,
    "descendants": 71,
}


async def test_all_tools_registered():
    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
    assert names == {
        "get_stories",
        "get_item",
        "get_comments",
        "get_user",
        "get_max_item_id",
        "get_updates",
    }


@respx.mock
async def test_get_stories_tool_adds_links():
    respx.get(f"{BASE_URL}/topstories.json").mock(return_value=httpx.Response(200, json=[8863]))
    respx.get(f"{BASE_URL}/item/8863.json").mock(return_value=httpx.Response(200, json=STORY))
    async with Client(mcp) as client:
        res = await client.call_tool("get_stories", {"category": "top", "limit": 1})
    assert res.data[0]["title"] == "My YC app: Dropbox"
    assert res.data[0]["hn_url"] == "https://news.ycombinator.com/item?id=8863"


@respx.mock
async def test_get_item_tool_missing_returns_none():
    respx.get(f"{BASE_URL}/item/1.json").mock(return_value=httpx.Response(200, text="null"))
    async with Client(mcp) as client:
        res = await client.call_tool("get_item", {"item_id": 1})
    assert res.data is None


@respx.mock
async def test_get_user_tool():
    respx.get(f"{BASE_URL}/user/pg.json").mock(
        return_value=httpx.Response(200, json={"id": "pg", "karma": 157000})
    )
    async with Client(mcp) as client:
        res = await client.call_tool("get_user", {"username": "pg"})
    assert res.data["id"] == "pg"
    assert res.data["hn_url"] == "https://news.ycombinator.com/user?id=pg"
