"""Typer CLI for the HackerNews API.

Examples::

    hn stories top          # front page
    hn stories ask          # latest Ask HN
    hn item 8863            # a single item
    hn comments 8863        # threaded discussion
    hn user pg              # a profile
    hn stories top --json   # raw JSON for scripting
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from html import unescape
from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .client import HNClient
from .models import Comment, Item, StoryCategory

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"hn, version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-V", help="Show the version and exit.", callback=_version_callback
        ),
    ] = False,
) -> None:
    """Unofficial HackerNews command-line client."""


# -- formatting helpers ----------------------------------------------------

_JSON_OPT = Annotated[bool, typer.Option("--json", help="Output raw JSON instead of a table.")]


def _run(operation: Callable[[HNClient], Any]) -> Any:
    """Run an async client operation, closing the client cleanly."""
    return asyncio.run(_with_client(operation))


async def _with_client(operation: Callable[[HNClient], Any]) -> Any:
    async with HNClient() as hn:
        return await operation(hn)


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


def _fail(message: str, suggestion: str | None = None) -> None:
    err_console.print(f"[bold red]Error:[/] {message}")
    if suggestion:
        err_console.print(f"[dim]  {suggestion}[/]")
    raise typer.Exit(code=1)


def _emit_json(obj: Any) -> None:
    """Serialize a pydantic model (or list/dict of them) as compact JSON."""
    sys.stdout.write(json.dumps(obj, default=_json_default) + "\n")


def _json_default(o: Any) -> Any:
    if isinstance(o, BaseModel):
        return o.model_dump(exclude_none=True)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


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
        link = s.url or s.hn_url or ""
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


# -- commands --------------------------------------------------------------


@app.command(
    epilog="Examples:\n  hn stories top\n  hn stories ask --limit 5\n  hn stories job --json"
)
def stories(
    category: Annotated[
        StoryCategory, typer.Argument(help="Which list: top, new, best, ask, show, or job.")
    ],
    limit: Annotated[
        int, typer.Option("--limit", "-n", min=1, max=500, help="Number of stories.")
    ] = 30,
    json_out: _JSON_OPT = False,
) -> None:
    """Show stories from a category: top, new, best, ask, show, or job."""
    if limit > category.max_limit:
        _fail(
            f"{category.title} hold at most {category.max_limit} stories.",
            f"hn stories {category.value} --limit {category.max_limit}",
        )
    stories_list = _run(lambda hn: hn.get_stories(category, limit=limit))
    if json_out:
        _emit_json(stories_list)
        return
    if not stories_list:
        console.print("[yellow]No stories found.[/]")
        return
    console.print(_stories_table(category.title, stories_list))


@app.command(epilog="Examples:\n  hn item 8863\n  hn item 8863 --json")
def item(
    item_id: Annotated[int, typer.Argument(help="The numeric item id.")],
    json_out: _JSON_OPT = False,
) -> None:
    """Show a single item (story, comment, job, or poll)."""
    result = _run(lambda hn: hn.get_item(item_id))
    if result is None:
        _fail(f"No item found with id {item_id}.", "hn stories top --json | jq '.[0].id'")
    if json_out:
        _emit_json(result)
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
    if result.hn_url:
        body_parts.append(f"[dim]{result.hn_url}[/dim]")
    console.print(
        Panel(
            "\n\n".join(body_parts),
            title=header,
            subtitle=meta,
            title_align="left",
            subtitle_align="left",
        )
    )


@app.command(
    epilog=(
        "Examples:\n  hn comments 8863\n  hn comments 8863 --depth 2\n  hn comments 8863 --json"
    )
)
def comments(
    item_id: Annotated[int, typer.Argument(help="Id of the story or comment.")],
    depth: Annotated[
        int, typer.Option("--depth", "-d", min=0, max=5, help="Reply nesting depth.")
    ] = 1,
    limit: Annotated[
        int, typer.Option("--limit", "-n", min=1, max=100, help="Max comments per level.")
    ] = 20,
    json_out: _JSON_OPT = False,
) -> None:
    """Show the threaded comment tree for an item."""
    tree = _run(lambda hn: hn.get_comments(item_id, max_depth=depth, max_per_level=limit))
    if json_out:
        _emit_json(tree)
        return
    if not tree:
        console.print("[yellow]No comments found.[/]")
        return
    for node in tree:
        _print_comment(node, indent=0)


def _print_comment(node: Comment, indent: int) -> None:
    pad = "  " * indent
    author = escape(node.by or "[deleted]")
    age = _relative_time(node.time)
    text = _strip_html(node.text)
    console.print(f"{pad}[green]{author}[/] [dim]· {age}[/]")
    if text:
        for line in text.splitlines():
            console.print(f"{pad}{escape(line)}")
    console.print()
    for reply in node.replies:
        _print_comment(reply, indent + 1)


@app.command(epilog="Examples:\n  hn user pg\n  hn user pg --json")
def user(
    username: Annotated[str, typer.Argument(help="The case-sensitive username.")],
    json_out: _JSON_OPT = False,
) -> None:
    """Show a user's public profile."""
    result = _run(lambda hn: hn.get_user(username))
    if result is None:
        _fail(f"No user found with username '{username}'.", "hn user pg")
    if json_out:
        _emit_json(result)
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
    if result.hn_url:
        lines.append(f"\n[dim]{result.hn_url}[/dim]")
    console.print(Panel("\n".join(lines), title=escape(result.id), title_align="left"))


@app.command(epilog="Examples:\n  hn max-item")
def max_item(json_out: _JSON_OPT = False) -> None:
    """Show the id of the most recently created item."""
    result = _run(lambda hn: hn.get_max_item_id())
    if json_out:
        _emit_json({"max_item_id": result})
        return
    console.print(f"[bold cyan]{result}[/]")


@app.command(epilog="Examples:\n  hn updates")
def updates(json_out: _JSON_OPT = False) -> None:
    """Show items and profiles that changed most recently."""
    result = _run(lambda hn: hn.get_updates())
    if json_out:
        _emit_json(result)
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
