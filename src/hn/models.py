"""Pydantic models mirroring the HackerNews API item and user schemas.

The HackerNews API is intentionally loose: every field except ``id`` and
``type`` (for items) is optional, and the API may add fields over time. These
models therefore keep all data fields optional and allow extra keys so that
unknown additions never break parsing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ItemType = Literal["job", "story", "comment", "poll", "pollopt"]


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


class Updates(BaseModel):
    """The set of items and profiles that changed most recently."""

    items: list[int] = Field(default_factory=list, description="Changed item ids.")
    profiles: list[str] = Field(default_factory=list, description="Changed usernames.")
