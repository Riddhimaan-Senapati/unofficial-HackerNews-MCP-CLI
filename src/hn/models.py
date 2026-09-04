"""Pydantic models mirroring the HackerNews API item and user schemas.

The HackerNews API is intentionally loose: every field except ``id`` and
``type`` (for items) is optional, and the API may add fields over time. These
models therefore keep all data fields optional and allow extra keys so that
unknown additions never break parsing.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

ItemType = Literal["job", "story", "comment", "poll", "pollopt"]

HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"
HN_USER_URL = "https://news.ycombinator.com/user?id={id}"


class StoryCategory(str, Enum):
    """The six story-list categories, named as the CLI and MCP expose them.

    Each member's value is its user-facing token (``"top"``, ``"new"``, ...),
    which is also what both Typer and FastMCP present to callers. The API
    endpoint stem and the documented story-list cap are derived so client,
    server, and CLI can never drift apart.
    """

    top = "top"
    new = "new"
    best = "best"
    ask = "ask"
    show = "show"
    job = "job"

    @property
    def endpoint(self) -> str:
        return _ENDPOINTS[self]

    @property
    def title(self) -> str:
        return _CATEGORY_TITLES[self]

    @property
    def max_limit(self) -> int:
        return 200 if self in {StoryCategory.ask, StoryCategory.show, StoryCategory.job} else 500


_ENDPOINTS = {
    StoryCategory.top: "topstories",
    StoryCategory.new: "newstories",
    StoryCategory.best: "beststories",
    StoryCategory.ask: "askstories",
    StoryCategory.show: "showstories",
    StoryCategory.job: "jobstories",
}

_CATEGORY_TITLES = {
    StoryCategory.top: "Top Stories",
    StoryCategory.new: "New Stories",
    StoryCategory.best: "Best Stories",
    StoryCategory.ask: "Ask HN",
    StoryCategory.show: "Show HN",
    StoryCategory.job: "Jobs",
}


def item_url(item_id: int | None) -> str | None:
    """The canonical news.ycombinator.com discussion link for an item id."""
    if item_id is None:
        return None
    return HN_ITEM_URL.format(id=item_id)


def user_url(username: str | None) -> str | None:
    """The canonical news.ycombinator.com profile link for a username."""
    if username is None:
        return None
    return HN_USER_URL.format(id=username)


class Item(BaseModel):
    """A HackerNews item: story, comment, job, poll, or poll option."""

    model_config = ConfigDict(extra="allow")

    id: int = Field(description="The item's unique id.")
    type: ItemType | None = Field(
        default=None, description="One of 'job', 'story', 'comment', 'poll', 'pollopt'."
    )
    by: str | None = Field(default=None, description="The username of the item's author.")
    time: int | None = Field(default=None, description="Creation date, in Unix time.")
    text: str | None = Field(default=None, description="The comment, story or poll text (HTML).")
    url: str | None = Field(default=None, description="The URL of the story.")
    score: int | None = Field(default=None, description="The story's score, or poll option votes.")
    title: str | None = Field(
        default=None, description="The title of the story, poll or job (HTML)."
    )
    parent: int | None = Field(
        default=None, description="The comment's parent: either another comment or the story."
    )
    poll: int | None = Field(default=None, description="The pollopt's associated poll.")
    kids: list[int] | None = Field(
        default=None, description="The ids of the item's comments, in ranked display order."
    )
    parts: list[int] | None = Field(
        default=None, description="A list of related pollopts, in display order."
    )
    descendants: int | None = Field(
        default=None, description="In the case of stories or polls, the total comment count."
    )
    deleted: bool | None = Field(default=None, description="True if the item is deleted.")
    dead: bool | None = Field(default=None, description="True if the item is dead.")

    @computed_field(description="Canonical HackerNews discussion link.")
    @property
    def hn_url(self) -> str | None:
        return item_url(self.id)


class User(BaseModel):
    """A HackerNews user profile. Only users with public activity are available."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="The user's unique username. Case-sensitive.")
    created: int | None = Field(
        default=None, description="Creation date of the user, in Unix time."
    )
    karma: int | None = Field(default=None, description="The user's karma.")
    about: str | None = Field(
        default=None, description="The user's optional self-description (HTML)."
    )
    submitted: list[int] | None = Field(
        default=None, description="List of the user's stories, polls and comments."
    )

    @computed_field(description="Canonical HackerNews profile link.")
    @property
    def hn_url(self) -> str | None:
        return user_url(self.id)


class Comment(BaseModel):
    """A comment in a threaded discussion, with its nested replies.

    HackerNews comments may be deleted (``deleted``/``dead``) yet still carry
    an id. Extra API fields are always allowed so parsing never breaks.
    """

    model_config = ConfigDict(extra="allow")

    id: int | None = Field(default=None, description="The comment's id, if present.")
    by: str | None = Field(default=None, description="The comment's author.")
    time: int | None = Field(default=None, description="Creation date, in Unix time.")
    text: str | None = Field(default=None, description="The comment body (HTML).")
    kids: list[int] | None = Field(
        default=None, description="The ids of the comment's replies, in display order."
    )
    deleted: bool | None = Field(default=None, description="True if the comment is deleted.")
    dead: bool | None = Field(default=None, description="True if the comment is dead.")
    replies: list[Comment] = Field(
        default_factory=list, description="The comment's expanded child replies."
    )

    @computed_field(description="Canonical HackerNews discussion link.")
    @property
    def hn_url(self) -> str | None:
        return item_url(self.id)


class Updates(BaseModel):
    """The set of items and profiles that changed most recently."""

    items: list[int] = Field(default_factory=list, description="Changed item ids.")
    profiles: list[str] = Field(default_factory=list, description="Changed usernames.")
