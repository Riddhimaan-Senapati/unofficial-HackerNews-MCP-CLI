"""Tests for the Typer CLI, exercising the non-interactive path and `--json`."""

from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from hn import __version__
from hn.cli import app
from hn.client import BASE_URL

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_lists_stories_command():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "stories" in result.output


@respx.mock
def test_stories_table_happy_path():
    respx.get(f"{BASE_URL}/topstories.json").mock(return_value=httpx.Response(200, json=[8863]))
    respx.get(f"{BASE_URL}/item/8863.json").mock(
        return_value=httpx.Response(
            200,
            json={"id": 8863, "type": "story", "title": "My YC app: Dropbox", "score": 104},
        )
    )
    result = runner.invoke(app, ["stories", "top", "--limit", "1"])
    assert result.exit_code == 0
    assert "My YC app: Dropbox" in result.output


@respx.mock
def test_stories_json_is_serializable():
    respx.get(f"{BASE_URL}/topstories.json").mock(return_value=httpx.Response(200, json=[8863]))
    respx.get(f"{BASE_URL}/item/8863.json").mock(
        return_value=httpx.Response(
            200,
            json={"id": 8863, "type": "story", "title": "Dropbox", "score": 104},
        )
    )
    result = runner.invoke(app, ["stories", "top", "--limit", "1", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["hn_url"] == "https://news.ycombinator.com/item?id=8863"


def test_stories_limit_capped_per_category():
    result = runner.invoke(app, ["stories", "ask", "--limit", "250"])
    assert result.exit_code == 1
    assert "200" in result.output
    assert "hn stories ask --limit 200" in result.output


def test_stories_requires_category():
    result = runner.invoke(app, ["stories"])
    assert result.exit_code != 0
    assert "CATEGORY" in result.output or "missing" in result.output.lower()
