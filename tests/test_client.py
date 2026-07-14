"""Tests for the async HN client, using respx to mock the Firebase API."""

from __future__ import annotations

import httpx
import pytest
import respx

from hn.client import BASE_URL, HNClient, HNError

STORY_ITEM = {
    "id": 8863,
    "type": "story",
    "by": "dhouston",
    "time": 1175714200,
    "title": "My YC app: Dropbox",
    "url": "http://www.getdropbox.com/u/2/screencast.html",
    "score": 104,
    "descendants": 71,
    "kids": [9224, 8952],
}


@respx.mock
async def test_get_item_parses_story():
    respx.get(f"{BASE_URL}/item/8863.json").mock(return_value=httpx.Response(200, json=STORY_ITEM))
    async with HNClient() as hn:
        item = await hn.get_item(8863)
    assert item is not None
    assert item.id == 8863
    assert item.type == "story"
    assert item.score == 104
    assert item.kids == [9224, 8952]


@respx.mock
async def test_get_item_missing_returns_none():
    # The real API returns the literal JSON `null` for missing items.
    respx.get(f"{BASE_URL}/item/1.json").mock(return_value=httpx.Response(200, text="null"))
    async with HNClient() as hn:
        assert await hn.get_item(1) is None


@respx.mock
async def test_get_item_allows_unknown_fields():
    respx.get(f"{BASE_URL}/item/1.json").mock(
        return_value=httpx.Response(200, json={"id": 1, "type": "story", "brandNew": 42})
    )
    async with HNClient() as hn:
        item = await hn.get_item(1)
    assert item is not None
    assert item.model_dump()["brandNew"] == 42


@respx.mock
async def test_get_stories_fetches_details_up_to_limit():
    respx.get(f"{BASE_URL}/topstories.json").mock(
        return_value=httpx.Response(200, json=[8863, 100, 200])
    )
    respx.get(f"{BASE_URL}/item/8863.json").mock(return_value=httpx.Response(200, json=STORY_ITEM))
    respx.get(f"{BASE_URL}/item/100.json").mock(
        return_value=httpx.Response(200, json={"id": 100, "type": "story", "title": "B"})
    )
    async with HNClient() as hn:
        stories = await hn.get_stories("top", limit=2)
    assert [s.id for s in stories] == [8863, 100]


async def test_get_story_ids_rejects_unknown_category():
    async with HNClient() as hn:
        with pytest.raises(ValueError, match="Unknown story list"):
            await hn.get_story_ids("bogus")


@respx.mock
async def test_get_user():
    respx.get(f"{BASE_URL}/user/pg.json").mock(
        return_value=httpx.Response(200, json={"id": "pg", "karma": 157000, "created": 1160418092})
    )
    async with HNClient() as hn:
        user = await hn.get_user("pg")
    assert user is not None
    assert user.id == "pg"
    assert user.karma == 157000


@respx.mock
async def test_get_comments_builds_nested_tree():
    root = {"id": 1, "type": "story", "kids": [2]}
    child = {"id": 2, "type": "comment", "by": "a", "text": "hi", "kids": [3]}
    grandchild = {"id": 3, "type": "comment", "by": "b", "text": "yo"}
    respx.get(f"{BASE_URL}/item/1.json").mock(return_value=httpx.Response(200, json=root))
    respx.get(f"{BASE_URL}/item/2.json").mock(return_value=httpx.Response(200, json=child))
    respx.get(f"{BASE_URL}/item/3.json").mock(return_value=httpx.Response(200, json=grandchild))
    async with HNClient() as hn:
        tree = await hn.get_comments(1, max_depth=1)
    assert len(tree) == 1
    assert tree[0]["id"] == 2
    assert tree[0]["replies"][0]["id"] == 3
    # max_depth=1 means the grandchild's own replies are not expanded.
    assert tree[0]["replies"][0]["replies"] == []


@respx.mock
async def test_get_comments_depth_zero_no_replies():
    root = {"id": 1, "type": "story", "kids": [2]}
    child = {"id": 2, "type": "comment", "by": "a", "text": "hi", "kids": [3]}
    respx.get(f"{BASE_URL}/item/1.json").mock(return_value=httpx.Response(200, json=root))
    respx.get(f"{BASE_URL}/item/2.json").mock(return_value=httpx.Response(200, json=child))
    async with HNClient() as hn:
        tree = await hn.get_comments(1, max_depth=0)
    assert tree[0]["replies"] == []


@respx.mock
async def test_max_item_and_updates():
    respx.get(f"{BASE_URL}/maxitem.json").mock(return_value=httpx.Response(200, json=48907576))
    respx.get(f"{BASE_URL}/updates.json").mock(
        return_value=httpx.Response(200, json={"items": [1, 2], "profiles": ["pg"]})
    )
    async with HNClient() as hn:
        assert await hn.get_max_item_id() == 48907576
        updates = await hn.get_updates()
    assert updates.items == [1, 2]
    assert updates.profiles == ["pg"]


@respx.mock
async def test_http_error_wrapped_as_hnerror():
    respx.get(f"{BASE_URL}/item/9.json").mock(return_value=httpx.Response(500))
    async with HNClient() as hn:
        with pytest.raises(HNError):
            await hn.get_item(9)
