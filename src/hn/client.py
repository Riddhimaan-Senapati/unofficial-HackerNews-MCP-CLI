"""Async HackerNews API client.

Thin wrapper over the official Firebase-backed HackerNews API
(https://github.com/HackerNews/API) built on ``httpx``. Shared by both the
FastMCP server and the Typer CLI so the two never drift apart.

The API has no authentication and (per the docs) no rate limit, but item and
story-list endpoints are individual documents, so higher-level helpers fan out
concurrent requests with a bounded semaphore to stay polite and fast.
"""

from __future__ import annotations

import asyncio
from types import TracebackType

import httpx

from .models import Item, Updates, User

BASE_URL = "https://hacker-news.firebaseio.com/v0"

# Documented caps on the story-list endpoints, used to validate `limit`.
MAX_TOP_NEW_BEST = 500
MAX_ASK_SHOW_JOB = 200

StoryList = str  # one of the endpoint stems below

STORY_ENDPOINTS: dict[str, str] = {
    "top": "topstories",
    "new": "newstories",
    "best": "beststories",
    "ask": "askstories",
    "show": "showstories",
    "job": "jobstories",
}


class HNError(RuntimeError):
    """Raised when the HackerNews API returns an unexpected response."""


class HNClient:
    """Async client for the HackerNews API.

    Use as an async context manager so the underlying ``httpx.AsyncClient`` is
    closed cleanly::

        async with HNClient() as hn:
            item = await hn.get_item(8863)
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        *,
        timeout: float = 10.0,
        concurrency: int = 20,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(concurrency)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "unofficial-hackernews-mcp-cli"},
        )

    async def __aenter__(self) -> HNClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # -- low-level ---------------------------------------------------------

    async def _get_json(self, path: str):
        async with self._semaphore:
            try:
                resp = await self._client.get(f"{self.base_url}/{path}")
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise HNError(f"Request to '{path}' failed: {e}") from e
            # A missing resource yields the literal `null`; treat an empty
            # body the same way rather than raising a JSON decode error.
            if not resp.content.strip():
                return None
            return resp.json()

    # -- items & users -----------------------------------------------------

    async def get_item(self, item_id: int) -> Item | None:
        """Fetch a single item by id. Returns ``None`` if it does not exist."""
        data = await self._get_json(f"item/{item_id}.json")
        if data is None:
            return None
        return Item.model_validate(data)

    async def get_items(self, item_ids: list[int]) -> list[Item]:
        """Fetch many items concurrently, preserving order, dropping missing."""
        results = await asyncio.gather(*(self.get_item(i) for i in item_ids))
        return [item for item in results if item is not None]

    async def get_user(self, username: str) -> User | None:
        """Fetch a user profile by username. Returns ``None`` if not found."""
        data = await self._get_json(f"user/{username}.json")
        if data is None:
            return None
        return User.model_validate(data)

    # -- story lists -------------------------------------------------------

    async def get_story_ids(self, which: StoryList) -> list[int]:
        """Fetch the raw ordered id list for a story category."""
        if which not in STORY_ENDPOINTS:
            raise ValueError(
                f"Unknown story list '{which}'. Expected one of: {', '.join(STORY_ENDPOINTS)}"
            )
        data = await self._get_json(f"{STORY_ENDPOINTS[which]}.json")
        return data or []

    async def get_stories(self, which: StoryList, limit: int = 30) -> list[Item]:
        """Fetch the first ``limit`` items from a story category, with details."""
        ids = await self.get_story_ids(which)
        return await self.get_items(ids[:limit])

    # -- live data ---------------------------------------------------------

    async def get_max_item_id(self) -> int:
        """The id of the most recently created item."""
        data = await self._get_json("maxitem.json")
        return int(data)

    async def get_updates(self) -> Updates:
        """Items and user profiles that changed most recently."""
        data = await self._get_json("updates.json") or {}
        return Updates.model_validate(data)

    # -- comment trees -----------------------------------------------------

    async def get_comments(
        self, item_id: int, *, max_depth: int = 1, max_per_level: int = 30
    ) -> list[dict]:
        """Fetch a nested comment tree for an item.

        Returns a list of dicts, each an :class:`Item` (as a dict) with an
        added ``replies`` key holding its child comments. ``max_depth`` bounds
        recursion (0 = direct comments only, no replies expanded);
        ``max_per_level`` caps how many children are expanded per node.
        """
        root = await self.get_item(item_id)
        if root is None or not root.kids:
            return []
        return await self._expand_kids(root.kids, max_depth, max_per_level)

    async def _expand_kids(self, kids: list[int], max_depth: int, max_per_level: int) -> list[dict]:
        children = await self.get_items(kids[:max_per_level])
        out: list[dict] = []
        for child in children:
            node = child.model_dump(exclude_none=True)
            if max_depth > 0 and child.kids:
                node["replies"] = await self._expand_kids(child.kids, max_depth - 1, max_per_level)
            else:
                node["replies"] = []
            out.append(node)
        return out
