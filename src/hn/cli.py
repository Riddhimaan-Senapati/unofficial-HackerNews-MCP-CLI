"""Typer CLI for the HackerNews API.

Examples::

    hn top --limit 10          # front page
    hn ask                     # latest Ask HN
    hn item 8863               # a single item
    hn comments 8863           # threaded discussion
    hn user pg                 # a profile
    hn top --json | jq         # raw JSON for scripting
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from .client import HNClient
from .models import Item, User

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Unofficial HackerNews command-line client.",
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True)

HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"
HN_USER_URL = "https://news.ycombinator.com/user?id={id}"

_CATEGORY_TITLES = {
    "top": "Top Stories",
    "new": "New Stories",
    "best": "Best Stories",
    "ask": "Ask HN",
    "show": "Show HN",
    "job": "Jobs",
}


# -- formatting helpers ----------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


def _relative_time(ts: int | None) -> str:
    if ts is None:
        return "-"
    delta = datetime.now(timezone.utc) - datetime.fromtimestamp(ts, tz=timezone.utc)
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def _fail(message: str) -> None:
    err_console.print(f"[bold red]Error:[/] {message}")
    raise typer.Exit(code=1)


def _dump(obj: Any) -> None:
    """Print an object (pydantic model, list, or dict) as JSON."""

    def default(o):
        if isinstance(o, (Item, User)):
            return o.model_dump(exclude_none=True)
        raise TypeError

    console.print_json(json.dumps(obj, default=default))


def _stories_table(title: str, stories: list[Item]) -> Table:
    table = Table(title=title, title_justify="left", expand=True, header_style="bold cyan")
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Title", style="bold", ratio=3)
    table.add_column("Score", justify="right", no_wrap=True)
    table.add_column("By", no_wrap=True)
    table.add_column("Cmts", justify="right", no_wrap=True)
    table.add_column("Age", justify="right", no_wrap=True, style="dim")
    table.add_column("ID", justify="right", style="dim", no_wrap=True)

    for i, s in enumerate(stories, start=1):
        title_text = escape(s.title or "(untitled)")
        link = s.url or HN_ITEM_URL.format(id=s.id)
        table.add_row(
            str(i),
            f"[link={link}]{title_text}[/link]",
            str(s.score if s.score is not None else "-"),
            escape(s.by or "-"),
            str(s.descendants if s.descendants is not None else "-"),
            _relative_time(s.time),
            str(s.id),
        )
    return table


# -- story commands --------------------------------------------------------


def _show_stories(category: str, limit: int, as_json: bool) -> None:
    async def _fetch() -> list[Item]:
        async with HNClient() as hn:
            return await hn.get_stories(category, limit=limit)

    stories = _run(_fetch())
    if as_json:
        _dump(stories)
        return
    if not stories:
        console.print("[yellow]No stories found.[/]")
        return
    console.print(_stories_table(_CATEGORY_TITLES[category], stories))


_LIMIT_OPT = Annotated[
    int, typer.Option("--limit", "-n", min=1, max=500, help="Number of stories.")
]
_JSON_OPT = Annotated[bool, typer.Option("--json", help="Output raw JSON instead of a table.")]


@app.command()
def top(limit: _LIMIT_OPT = 30, json_out: _JSON_OPT = False) -> None:
    """Show the top (front-page) stories."""
    _show_stories("top", limit, json_out)


@app.command()
def new(limit: _LIMIT_OPT = 30, json_out: _JSON_OPT = False) -> None:
    """Show the newest stories."""
    _show_stories("new", limit, json_out)


@app.command()
def best(limit: _LIMIT_OPT = 30, json_out: _JSON_OPT = False) -> None:
    """Show the best recent stories."""
    _show_stories("best", limit, json_out)


@app.command()
def ask(limit: _LIMIT_OPT = 30, json_out: _JSON_OPT = False) -> None:
    """Show the latest Ask HN posts."""
    _show_stories("ask", limit, json_out)


@app.command()
def show(limit: _LIMIT_OPT = 30, json_out: _JSON_OPT = False) -> None:
    """Show the latest Show HN posts."""
    _show_stories("show", limit, json_out)


@app.command()
def jobs(limit: _LIMIT_OPT = 30, json_out: _JSON_OPT = False) -> None:
    """Show the latest job postings."""
    _show_stories("job", limit, json_out)


# -- item / user / comments ------------------------------------------------


@app.command()
def item(
    item_id: Annotated[int, typer.Argument(help="The numeric item id.")],
    json_out: _JSON_OPT = False,
) -> None:
    """Show a single item (story, comment, job, or poll)."""

    async def _fetch() -> Item | None:
        async with HNClient() as hn:
            return await hn.get_item(item_id)

    result = _run(_fetch())
    if result is None:
        _fail(f"No item found with id {item_id}.")
    if json_out:
        _dump(result)
        return

    header = escape(result.title or f"{(result.type or 'item').title()} {result.id}")
    meta = " · ".join(
        part
        for part in [
            f"[cyan]{result.score} points[/]" if result.score is not None else "",
            f"by [green]{escape(result.by)}[/]" if result.by else "",
            _relative_time(result.time),
            f"{result.descendants} comments" if result.descendants is not None else "",
        ]
        if part
    )
    body_parts = []
    if result.url:
        body_parts.append(f"[link={result.url}]{escape(result.url)}[/link]")
    if result.text:
        body_parts.append(escape(_strip_html(result.text)))
    body_parts.append(f"[dim]{HN_ITEM_URL.format(id=result.id)}[/dim]")
    console.print(
        Panel(
            "\n\n".join(body_parts),
            title=header,
            subtitle=meta,
            title_align="left",
            subtitle_align="left",
        )
    )


@app.command()
def comments(
    item_id: Annotated[int, typer.Argument(help="Id of the story or comment.")],
    depth: Annotated[
        int, typer.Option("--depth", "-d", min=0, max=5, help="Reply nesting depth.")
    ] = 1,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", min=1, max=100, help="Max comments per level."),
    ] = 20,
    json_out: _JSON_OPT = False,
) -> None:
    """Show the threaded comment tree for an item."""

    async def _fetch() -> list[dict]:
        async with HNClient() as hn:
            return await hn.get_comments(item_id, max_depth=depth, max_per_level=limit)

    tree = _run(_fetch())
    if json_out:
        _dump(tree)
        return
    if not tree:
        console.print("[yellow]No comments found.[/]")
        return
    for node in tree:
        _print_comment(node, indent=0)


def _print_comment(node: dict, indent: int) -> None:
    pad = "  " * indent
    author = node.get("by", "[deleted]")
    age = _relative_time(node.get("time"))
    text = _strip_html(node.get("text"))
    console.print(f"{pad}[green]{escape(author)}[/] [dim]· {age}[/]")
    if text:
        for line in text.splitlines():
            console.print(f"{pad}{escape(line)}")
    console.print()
    for reply in node.get("replies", []):
        _print_comment(reply, indent + 1)


@app.command()
def user(
    username: Annotated[str, typer.Argument(help="The case-sensitive username.")],
    json_out: _JSON_OPT = False,
) -> None:
    """Show a user's public profile."""

    async def _fetch() -> User | None:
        async with HNClient() as hn:
            return await hn.get_user(username)

    result = _run(_fetch())
    if result is None:
        _fail(f"No user found with username '{username}'.")
    if json_out:
        _dump(result)
        return

    lines = [
        f"[bold]karma[/]: {result.karma if result.karma is not None else '-'}",
        "[bold]created[/]: "
        + (
            datetime.fromtimestamp(result.created, tz=timezone.utc).strftime("%Y-%m-%d")
            if result.created
            else "-"
        ),
        f"[bold]submissions[/]: {len(result.submitted) if result.submitted else 0}",
    ]
    if result.about:
        lines.append("")
        lines.append(escape(_strip_html(result.about)))
    lines.append(f"\n[dim]{HN_USER_URL.format(id=result.id)}[/dim]")
    console.print(Panel("\n".join(lines), title=escape(result.id), title_align="left"))


# -- live data -------------------------------------------------------------


@app.command(name="max-item")
def max_item(json_out: _JSON_OPT = False) -> None:
    """Show the id of the most recently created item."""

    async def _fetch() -> int:
        async with HNClient() as hn:
            return await hn.get_max_item_id()

    result = _run(_fetch())
    if json_out:
        _dump({"max_item_id": result})
        return
    console.print(f"[bold cyan]{result}[/]")


@app.command()
def updates(json_out: _JSON_OPT = False) -> None:
    """Show items and profiles that changed most recently."""

    async def _fetch():
        async with HNClient() as hn:
            return await hn.get_updates()

    result = _run(_fetch())
    if json_out:
        _dump(result.model_dump())
        return
    console.print(
        f"[bold]Changed items[/] ({len(result.items)}): "
        f"{', '.join(str(i) for i in result.items[:20])}"
        + (" ..." if len(result.items) > 20 else "")
    )
    console.print(
        f"[bold]Changed profiles[/] ({len(result.profiles)}): "
        f"{', '.join(result.profiles[:20])}" + (" ..." if len(result.profiles) > 20 else "")
    )


if __name__ == "__main__":
    app()
