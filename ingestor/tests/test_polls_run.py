"""Real load of the polls page: snapshot, silver state and run documents.

The state tests are read-only (SELECT): they check the local bronze snapshot
and the real ``silver``/``bronze`` schemas. They skip without a snapshot or a
reachable Postgres (CI has neither ``data/raw/`` nor the service); the real
load is the implementer's CLI run, documented in ``docs/ingestor/polls-run.md``.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ingestor.models import Ingestion, Party, Poll, PollResult
from ingestor.polls.adapters.wikipedia_polls import (
    RESULT_ROW_STYLE,
    parse_polls,
    poll_tables,
)
from ingestor.settings import settings

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_SUBDIR = Path("polls") / "wikipedia-en" / "2026-general"


def _newest_snapshot() -> tuple[int, Path]:
    """Newest ``{revid}.wikitext`` under ``RAW_DIR/polls/...``; skip if none."""
    directory = settings.raw_dir / RAW_SUBDIR
    snapshots = sorted(directory.glob("*.wikitext"), key=lambda path: int(path.stem))
    if not snapshots:
        pytest.skip("no polls snapshot in data/raw/ (local run only)")
    path = snapshots[-1]
    return int(path.stem), path


def _real_session() -> Session:
    """Session over ``settings.database_url``; skip when Postgres is down."""
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        engine.dispose()
        pytest.skip("Postgres is not reachable (docker compose up -d --wait)")
    return Session(engine)


def _results(session: Session, poll_id: int) -> dict[str, PollResult]:
    """Results of one poll, keyed by party slug."""
    return {
        party.slug: result
        for result, party in session.execute(
            select(PollResult, Party)
            .join(Party, PollResult.party_id == Party.id)
            .where(PollResult.poll_id == poll_id)
        )
    }


# --- Snapshot and bronze (T1: R1, R2) ---------------------------------------


def test_snapshot_present_and_registered_processed():  # R1, R2
    revision_id, path = _newest_snapshot()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    with _real_session() as session:
        ingestion = session.scalar(select(Ingestion).where(Ingestion.sha256 == digest))
        assert ingestion is not None

    assert revision_id > 0
    assert ingestion.status == "processed"
    assert ingestion.source == "wikipedia-en"
    assert ingestion.file_path == str(RAW_SUBDIR / f"{revision_id}.wikitext")
    assert ingestion.file_path == str(path.relative_to(settings.raw_dir))


# --- Silver mirrors the snapshot (T1: R3, R4) -------------------------------


def test_silver_matches_snapshot_parse():  # R3, R4
    revision_id, path = _newest_snapshot()
    rows = parse_polls(path.read_text(encoding="utf-8"))

    with _real_session() as session:
        polls = list(
            session.scalars(
                select(Poll).where(Poll.revision_id == revision_id).order_by(Poll.id)
            )
        )
        assert len(polls) == len(rows)

        results_count = session.scalar(
            select(func.count())
            .select_from(PollResult)
            .join(Poll, PollResult.poll_id == Poll.id)
            .where(Poll.revision_id == revision_id)
        )
        assert results_count == sum(len(row.results) for row in rows)

        for poll, row in zip((polls[0], polls[-1]), (rows[0], rows[-1]), strict=True):
            assert poll.source == row.source
            assert poll.fieldwork_start == row.fieldwork_start
            assert poll.fieldwork_end == row.fieldwork_end
            assert poll.sample_size == row.sample_size
            assert poll.turnout == row.turnout

        slug = next(iter(rows[0].results))
        expected = rows[0].results[slug]
        result = _results(session, polls[0].id)[slug]
        assert result.pct == expected.pct
        assert (result.seats_min, result.seats_max) == (
            expected.seats_min,
            expected.seats_max,
        )


# --- Every year table and the campaign start (T1: R5, R6) -------------------


def test_silver_covers_year_tables_and_range():  # R5, R6
    revision_id, path = _newest_snapshot()
    table_years = {year for year, _ in poll_tables(path.read_text(encoding="utf-8"))}
    assert {2023, 2024, 2025, 2026} <= table_years

    with _real_session() as session:
        end_years = set(
            session.scalars(
                select(func.extract("year", Poll.fieldwork_end)).where(
                    Poll.revision_id == revision_id, Poll.fieldwork_end.is_not(None)
                )
            )
        )
        earliest = session.scalar(
            select(func.min(Poll.fieldwork_start)).where(
                Poll.revision_id == revision_id
            )
        )

    assert {2023, 2024, 2025, 2026} <= {int(year) for year in end_years}
    assert date(2023, 7, 23) <= earliest <= date(2023, 8, 31)


# --- Completeness arithmetic (T1: R7) ---------------------------------------


def test_completeness_arithmetic_no_lost_rows():  # R7
    revision_id, path = _newest_snapshot()
    tables = poll_tables(path.read_text(encoding="utf-8"))
    rows = parse_polls(path.read_text(encoding="utf-8"))

    declared = sum(len(table.rows) for _, table in tables)
    skipped = 0
    for _, table in tables:
        for row in table.rows:
            if any(cell.header for cell in row.cells):
                skipped += 1  # two header rows per table
            elif RESULT_ROW_STYLE in row.attrs.get("style", ""):
                skipped += 1  # election result row
            elif len(row.cells) == 1 and "colspan" in row.cells[0].attrs:
                skipped += 1  # separator row
    assert declared == len(rows) + skipped

    with _real_session() as session:
        loaded = session.scalar(
            select(func.count())
            .select_from(Poll)
            .where(Poll.revision_id == revision_id)
        )
    assert loaded == len(rows)


# --- Run report (T3: R7-R11) -----------------------------------------------


def _report() -> str:
    return (REPO_ROOT / "docs" / "ingestor" / "polls-run.md").read_text(
        encoding="utf-8"
    )


def test_docs_polls_run_completeness():  # R7, R8, R9, R10
    text = _report()
    for needle in (
        "fetch-polls",
        "ingest-polls",
        "Completitud",
        "584",
        "cabecera",
        "separadora",
        "resultado",
        "Lead",
        "Fuera de alcance",
        "FA",
        "66–67",  # U+2013: the adapter warning literal
        "select count(*)",
        "silver.poll",
        "silver.poll_result",
        "bronze.ingestion",
        "revision_id",
        "oldid=",
    ):
        assert needle in text


def test_docs_polls_run_cotejo():  # R11
    section = _report().split("## Cotejo", 1)[1].split("\n## ", 1)[0]
    rows = [
        line
        for line in section.splitlines()
        if line.startswith("|") and "%" in line and "escañ" in line
    ]
    assert len(rows) >= 5


# --- Source section (T5: R12-R15) ------------------------------------------


def _data_sources() -> str:
    return (REPO_ROOT / ".agents" / "data-sources.md").read_text(encoding="utf-8")


def test_docs_data_sources():  # R12, R15
    text = _data_sources()
    for needle in (
        "Sondeos (Wikipedia)",
        "Opinion polling for the 2026 Spanish general election",
        "wikitext",
        "{revid}.wikitext",
        "data/raw/polls/wikipedia-en/2026-general/",
        "fetch-polls",
        "ingest-polls",
        "polls-run.md",
        "../docs/ingestor/polls-run.md",
        "CC BY-SA",
        "oldid=",
    ):
        assert needle in text
    # the relative link from .agents/ must not climb out of the repo
    assert "../../docs/ingestor/polls-run.md" not in text


def test_docs_data_sources_quirks():  # R13, R14
    text = _data_sources()
    for needle in (
        "rowspan",
        "CIS",
        "cabecera",
        "2026 (after FA)",
        "separador",
        "resultado",
        "Lead",
        "cruce de año",
        "<2.0",
        "fecha de publicación",
        "participación",
    ):
        assert needle in text
