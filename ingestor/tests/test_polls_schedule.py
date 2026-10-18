"""The 2×/day polls cycle (``fetch-polls`` + ``ingest-polls``) and its artifacts.

No network: the MediaWiki API transport is injected through a fake opener on
``ingestor.polls.fetch.urlopen``. The cycle tests use the isolated PostgreSQL
test schemas (``conftest.py``; skipped without Postgres).
"""

from __future__ import annotations

import io
import json
import logging
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

from sqlalchemy import select
from sqlalchemy.orm import Session

from ingestor import cli
from ingestor.models import Election, Ingestion, Party, Poll, PollResult, Pollster

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wikipedia_polls"
REVISION_RESPONSE = FIXTURES / "api_revision.json"
MISSING_RESPONSE = FIXTURES / "api_missing.json"
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_SUBDIR = Path("polls") / "wikipedia-en" / "2026-general"


def _fixture_revision() -> tuple[int, str]:
    payload = json.loads(REVISION_RESPONSE.read_bytes())
    revision = payload["query"]["pages"][0]["revisions"][0]
    return revision["revid"], revision["timestamp"]


REVID, TIMESTAMP = _fixture_revision()


class FakeOpener:
    """Stand-in for ``urllib.request.urlopen``: records calls, replays payloads."""

    def __init__(self, *payloads: bytes | Exception) -> None:
        self.payloads = payloads
        self.calls: list[tuple[Request, int]] = []

    def __call__(self, request: Request, timeout: int) -> io.BytesIO:
        self.calls.append((request, timeout))
        payload = self.payloads[min(len(self.calls) - 1, len(self.payloads) - 1)]
        if isinstance(payload, Exception):
            raise payload
        return io.BytesIO(payload)


def _snapshot(tmp_path: Path, revid: int, fixture: str = "load_small.wikitext") -> Path:
    """Copy a fixture into ``tmp_path`` as ``{revid}.wikitext``."""
    path = tmp_path / RAW_SUBDIR / f"{revid}.wikitext"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((FIXTURES / fixture).read_text(encoding="utf-8"), encoding="utf-8")
    return path


def _use_cli(db, tmp_path: Path, monkeypatch) -> None:
    """Point the CLI at the test factory and a temporary bronze root."""
    monkeypatch.setattr(cli, "SessionLocal", db)
    monkeypatch.setattr(cli, "configure_logging", lambda: None)
    monkeypatch.setattr(cli.settings, "raw_dir", tmp_path)


def _seed_election(db) -> int:
    """A national congress election after the polls' fieldwork."""
    with db() as session:
        election = Election(type="congress", date=date(2027, 5, 1))
        session.add(election)
        session.commit()
        return election.id


def _seed_pending_poll(db) -> int:
    """A manual poll without an election, pending the resolution pass."""
    with db() as session:
        pollster = Pollster(name="Manual", slug="manual")
        session.add(pollster)
        session.flush()
        poll = Poll(
            pollster_id=pollster.id,
            source="Manual/Test",
            election_type="congress",
            fieldwork_start=date(2026, 10, 11),
            fieldwork_end=date(2026, 10, 11),
            sample_size=1000,
            turnout=None,
            revision_id=1,
        )
        session.add(poll)
        session.commit()
        return poll.id


def _state(db) -> tuple:
    """Bronze rows plus the silver ids/counts that a no-news cycle must not touch."""
    with db() as session:
        return (
            len(list(session.scalars(select(Ingestion)))),
            _ids(session, Poll),
            _ids(session, PollResult),
            _ids(session, Pollster),
            _ids(session, Party),
        )


def _ids(session: Session, model) -> list[int]:
    return list(session.scalars(select(model.id).order_by(model.id)))


# --- Artifacts: docs and workflow (T1: R1-R5) -------------------------------


def test_docs_environment_schedule():  # R1, R2, R3
    text = (REPO_ROOT / ".agents" / "environment.md").read_text(encoding="utf-8")
    for needle in (
        "0 6,18 * * *",
        "crontab",
        "launchd",
        "fetch-polls",
        "ingest-polls",
        "data/polls-sync.log",
        "polls-sync.yml",
        "Exit code",
        "distinto de 0",
        "cd /Users/javier/Developer/1poller/ingestor",
        "/opt/homebrew/bin/uv",
        "docker-compose",
        "provisional",
        "despliegue",
        "} >>",
    ):
        assert needle in text


def test_workflow_skeleton():  # R4, R5
    text = (REPO_ROOT / ".github" / "workflows" / "polls-sync.yml").read_text(
        encoding="utf-8"
    )
    for needle in (
        "schedule:",
        "0 6,18 * * *",
        "workflow_dispatch",
        "placeholder",
        "fetch-polls",
        "ingest-polls",
        "cron/launchd",
    ):
        assert needle in text
    assert "secrets." not in text
    assert "DATABASE_URL" not in text
    assert "psql" not in text


# --- The "no news" path of fetch-polls (T4: R6, R7) -------------------------


def test_no_news_fetch_makes_one_api_call(tmp_path, monkeypatch):  # R6, R7
    path = _snapshot(tmp_path, REVID)
    before = path.read_bytes()
    opener = FakeOpener(REVISION_RESPONSE.read_bytes())
    monkeypatch.setattr("ingestor.polls.fetch.urlopen", opener)
    monkeypatch.setattr(cli, "configure_logging", lambda: None)
    monkeypatch.setattr(cli.settings, "raw_dir", tmp_path)

    assert cli.main(["fetch-polls"]) == 0

    assert len(opener.calls) == 1
    params = parse_qs(urlparse(opener.calls[0][0].full_url).query)
    assert params["action"] == ["query"]
    assert "oldid" not in params
    assert path.read_bytes() == before


# --- The full "no news" cycle (T5: R8, R9, R10) -----------------------------


def test_no_news_cycle_writes_nothing(db, tmp_path, monkeypatch):  # R8, R9, R10
    _snapshot(tmp_path, REVID)
    _use_cli(db, tmp_path, monkeypatch)
    assert cli.main(["ingest-polls"]) == 0

    election_id = _seed_election(db)
    pending_poll_id = _seed_pending_poll(db)
    before = _state(db)

    opener = FakeOpener(REVISION_RESPONSE.read_bytes())
    monkeypatch.setattr("ingestor.polls.fetch.urlopen", opener)

    assert cli.main(["fetch-polls"]) == 0
    assert cli.main(["ingest-polls"]) == 0

    assert len(opener.calls) == 1
    assert _state(db) == before
    with db() as session:
        polls = {poll.source: poll for poll in session.scalars(select(Poll))}
        assert session.get(Poll, pending_poll_id).election_id == election_id
        assert polls["Alpha/Medio"].election_id == election_id
        assert polls["CIS (Target Point)"].election_id is None


# --- Missing page fails the cycle (T6: R11) ---------------------------------


def test_missing_page_fails_cycle(tmp_path, monkeypatch, caplog):  # R11
    opener = FakeOpener(MISSING_RESPONSE.read_bytes())
    monkeypatch.setattr("ingestor.polls.fetch.urlopen", opener)
    monkeypatch.setattr(cli, "configure_logging", lambda: None)
    monkeypatch.setattr(cli.settings, "raw_dir", tmp_path)

    with caplog.at_level(logging.ERROR):
        assert cli.main(["fetch-polls"]) == 1

    assert "missing" in caplog.text
