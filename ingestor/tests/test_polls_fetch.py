"""``fetch-polls``: fixed-revision wikitext snapshots (no network, no database).

The API responses and the wikitext snippet are real captures from 2026-10-17
(see specs/polls_fetch/design.md).
"""

import ast
import io
import json
import logging
import sys
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pytest

from ingestor.cli import main
from ingestor.errors import IngestError
from ingestor.polls.fetch import (
    DEFAULT_PAGE,
    RAW_URL,
    TIMEOUT_SECONDS,
    fetch_snapshot,
    parse_revision_response,
    resolve_revision,
    snapshot_dir,
)
from ingestor.settings import settings

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wikipedia_polls"
REVISION_RESPONSE = FIXTURES / "api_revision.json"
MISSING_RESPONSE = FIXTURES / "api_missing.json"
REPO_ROOT = Path(__file__).resolve().parents[2]

# Real head of the wikitext of revision 1380713440 (captured 2026-10-17),
# trimmed to keep the tests light; the real snapshot is ~650 KB.
WIKITEXT = (
    b"{{short description|none}}\n"
    b"{{pp-sock|small=yes}}\n"
    b"{{use dmy dates|date=October 2026}}\n"
    b"In the run up to the [[2026 Spanish general election]], various organisations "
    b"carry out [[opinion polling]] to gauge voting intention in [[Spain]] during the "
    b"term of the [[15th Cortes Generales]]. Results of such polls are displayed in "
    b"this article. The date range for these opinion polls is from the [[2023 Spanish "
    b"general election|previous general election]], held on 23 July 2023, to the "
    b"present day.\n"
)


def _fixture_revision() -> tuple[int, str]:
    payload = json.loads(REVISION_RESPONSE.read_bytes())
    revision = payload["query"]["pages"][0]["revisions"][0]
    return revision["revid"], revision["timestamp"]


REVID, TIMESTAMP = _fixture_revision()


class FakeOpener:
    """Stand-in for ``urllib.request.urlopen``: records calls, replays payloads.

    Each payload is returned as ``io.BytesIO``; an ``Exception`` payload is
    raised instead, which is how the tests exercise retries.
    """

    def __init__(self, *payloads: bytes | Exception) -> None:
        self.payloads = payloads
        self.calls: list[tuple[Request, int]] = []

    def __call__(self, request: Request, timeout: int) -> io.BytesIO:
        self.calls.append((request, timeout))
        payload = self.payloads[min(len(self.calls) - 1, len(self.payloads) - 1)]
        if isinstance(payload, Exception):
            raise payload
        return io.BytesIO(payload)


def test_parse_revision_response():  # R1
    assert parse_revision_response(REVISION_RESPONSE.read_bytes()) == (REVID, TIMESTAMP)


def test_parse_missing_page_raises():  # R13
    with pytest.raises(IngestError):
        parse_revision_response(MISSING_RESPONSE.read_bytes())


def _params(request: Request) -> dict[str, list[str]]:
    return parse_qs(urlparse(request.full_url).query)


def test_resolve_queries_current_revision():  # R1
    opener = FakeOpener(REVISION_RESPONSE.read_bytes())
    resolve_revision(DEFAULT_PAGE, opener)
    assert _params(opener.calls[0][0]) == {
        "action": ["query"],
        "prop": ["revisions"],
        "rvprop": ["ids|timestamp"],
        "redirects": ["1"],
        "format": ["json"],
        "formatversion": ["2"],
        "titles": [DEFAULT_PAGE],
    }


def test_user_agent_header():  # R8
    opener = FakeOpener(REVISION_RESPONSE.read_bytes())
    resolve_revision(DEFAULT_PAGE, opener)
    assert "votoscope" in opener.calls[0][0].get_header("User-agent")


def test_timeout_applied():  # R9
    opener = FakeOpener(REVISION_RESPONSE.read_bytes())
    resolve_revision(DEFAULT_PAGE, opener)
    assert opener.calls[0][1] == TIMEOUT_SECONDS


def test_retry_once_then_success(caplog):  # R10
    opener = FakeOpener(URLError("network down"), REVISION_RESPONSE.read_bytes())
    with caplog.at_level(logging.WARNING):
        assert resolve_revision(DEFAULT_PAGE, opener) == (REVID, TIMESTAMP)
    assert len(opener.calls) == 2
    assert "retrying once" in caplog.text


def test_retry_once_on_incomplete_read(caplog):  # R10
    opener = FakeOpener(IncompleteRead(b"partial"), REVISION_RESPONSE.read_bytes())
    with caplog.at_level(logging.WARNING):
        assert resolve_revision(DEFAULT_PAGE, opener) == (REVID, TIMESTAMP)
    assert len(opener.calls) == 2
    assert "retrying once" in caplog.text


def test_retry_gives_up():  # R11
    opener = FakeOpener(URLError("network down"))
    with pytest.raises(IngestError, match="2 attempts"):
        resolve_revision(DEFAULT_PAGE, opener)
    assert len(opener.calls) == 2


def test_fetch_downloads_fixed_revision(tmp_path):  # R2, R3
    opener = FakeOpener(REVISION_RESPONSE.read_bytes(), WIKITEXT)
    outcome = fetch_snapshot(raw_dir=tmp_path, opener=opener)
    raw_request = opener.calls[1][0]
    assert raw_request.full_url.startswith(f"{RAW_URL}?")
    assert _params(raw_request) == {"oldid": [str(REVID)], "action": ["raw"]}
    expected = (
        tmp_path / "polls" / "wikipedia-en" / "2026-general" / f"{REVID}.wikitext"
    )
    assert outcome == (REVID, TIMESTAMP, expected, True)
    assert expected.read_bytes() == WIKITEXT


def test_fetch_creates_missing_directories(tmp_path):  # R3
    opener = FakeOpener(REVISION_RESPONSE.read_bytes(), WIKITEXT)
    outcome = fetch_snapshot(raw_dir=tmp_path / "nested" / "raw", opener=opener)
    assert outcome.path.read_bytes() == WIKITEXT


def test_download_failure_leaves_no_snapshot(tmp_path):  # R11
    opener = FakeOpener(REVISION_RESPONSE.read_bytes(), URLError("network down"))
    with pytest.raises(IngestError, match="2 attempts"):
        fetch_snapshot(raw_dir=tmp_path, opener=opener)
    assert not list(tmp_path.rglob("*.wikitext"))


def test_snapshot_write_is_atomic(tmp_path, monkeypatch):  # R11
    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr("ingestor.polls.fetch.os.replace", fail_replace)
    opener = FakeOpener(REVISION_RESPONSE.read_bytes(), WIKITEXT)
    with pytest.raises(OSError, match="replace failed"):
        fetch_snapshot(raw_dir=tmp_path, opener=opener)
    expected = (
        tmp_path / "polls" / "wikipedia-en" / "2026-general" / f"{REVID}.wikitext"
    )
    assert not expected.exists()
    assert not list(tmp_path.rglob("*.tmp"))


def test_fetch_skips_existing_revision(tmp_path):  # R4
    path = tmp_path / "polls" / "wikipedia-en" / "2026-general" / f"{REVID}.wikitext"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"previous snapshot")
    opener = FakeOpener(REVISION_RESPONSE.read_bytes())
    outcome = fetch_snapshot(raw_dir=tmp_path, opener=opener)
    assert len(opener.calls) == 1
    assert path.read_bytes() == b"previous snapshot"
    assert outcome == (REVID, TIMESTAMP, path, False)


def test_page_option_title_and_dir(tmp_path):  # R5, R6
    other = "Opinion polling for the 2027 Spanish general election"
    opener = FakeOpener(REVISION_RESPONSE.read_bytes(), WIKITEXT)
    outcome = fetch_snapshot(other, raw_dir=tmp_path, opener=opener)
    assert _params(opener.calls[0][0])["titles"] == [other]
    expected_dir = "opinion-polling-for-the-2027-spanish-general-election"
    assert outcome.path == (
        tmp_path / "polls" / "wikipedia-en" / expected_dir / f"{REVID}.wikitext"
    )


def test_default_dir():  # R6
    assert snapshot_dir(DEFAULT_PAGE) == "2026-general"
    assert snapshot_dir(DEFAULT_PAGE.replace(" ", "_")) == "2026-general"
    assert (
        snapshot_dir("Opinion polling for the 2027 Spanish general election")
        == "opinion-polling-for-the-2027-spanish-general-election"
    )


def test_cli_fetch_polls_downloads(tmp_path, monkeypatch):  # R14, R16
    opener = FakeOpener(REVISION_RESPONSE.read_bytes(), WIKITEXT)
    monkeypatch.setattr("ingestor.polls.fetch.urlopen", opener)
    monkeypatch.setattr("ingestor.cli.configure_logging", lambda: None)
    monkeypatch.setattr(settings, "raw_dir", tmp_path)
    assert main(["fetch-polls"]) == 0
    expected = (
        tmp_path / "polls" / "wikipedia-en" / "2026-general" / f"{REVID}.wikitext"
    )
    assert expected.read_bytes() == WIKITEXT


def test_cli_fetch_polls_no_news(tmp_path, monkeypatch):  # R4, R14, R16
    path = tmp_path / "polls" / "wikipedia-en" / "2026-general" / f"{REVID}.wikitext"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"previous snapshot")
    opener = FakeOpener(REVISION_RESPONSE.read_bytes())
    monkeypatch.setattr("ingestor.polls.fetch.urlopen", opener)
    monkeypatch.setattr("ingestor.cli.configure_logging", lambda: None)
    monkeypatch.setattr(settings, "raw_dir", tmp_path)
    assert main(["fetch-polls"]) == 0
    assert len(opener.calls) == 1
    assert path.read_bytes() == b"previous snapshot"


def test_cli_failure_exit_1(tmp_path, monkeypatch, caplog):  # R12
    opener = FakeOpener(URLError("network down"))
    monkeypatch.setattr("ingestor.polls.fetch.urlopen", opener)
    monkeypatch.setattr("ingestor.cli.configure_logging", lambda: None)
    monkeypatch.setattr(settings, "raw_dir", tmp_path)
    with caplog.at_level(logging.ERROR):
        assert main(["fetch-polls"]) == 1
    assert "request failed" in caplog.text


def test_logs_revision_and_outcome(tmp_path, caplog):  # R15
    with caplog.at_level(logging.INFO):
        opener = FakeOpener(REVISION_RESPONSE.read_bytes(), WIKITEXT)
        fetch_snapshot(raw_dir=tmp_path, opener=opener)
        assert f"revid={REVID}" in caplog.text
        assert "downloaded snapshot" in caplog.text
        fetch_snapshot(
            raw_dir=tmp_path, opener=FakeOpener(REVISION_RESPONSE.read_bytes())
        )
    assert "up to date" in caplog.text


def test_no_real_urlopen_used(tmp_path, monkeypatch):  # R16
    def forbidden(*args, **kwargs):
        raise AssertionError("urlopen must not be used when an opener is injected")

    monkeypatch.setattr("ingestor.polls.fetch.urlopen", forbidden)
    opener = FakeOpener(REVISION_RESPONSE.read_bytes(), WIKITEXT)
    fetch_snapshot(raw_dir=tmp_path, opener=opener)
    assert opener.calls


def test_stdlib_only():  # R7
    import ingestor.polls.fetch

    source = Path(ingestor.polls.fetch.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= sys.stdlib_module_names | {"ingestor"}
    assert ingestor.polls.fetch.urlopen.__module__ == "urllib.request"


def test_docs_architecture():  # R17
    text = (REPO_ROOT / ".agents" / "architecture.md").read_text(encoding="utf-8")
    assert "fetch-polls" in text
    assert "se descargan por CLI" in text
    assert "data/raw/polls/" in text


def test_docs_ingestor_agents():  # R18
    text = (REPO_ROOT / "ingestor" / "AGENTS.md").read_text(encoding="utf-8")
    assert "fetch-polls" in text
    assert "fetch.py" in text
    assert "se descargan por CLI" in text


def test_docs_ingesta():  # R19
    text = (REPO_ROOT / "docs" / "ingestor" / "ingesta.md").read_text(encoding="utf-8")
    assert "fetch-polls" in text
    assert "polls/wikipedia-en/" in text
