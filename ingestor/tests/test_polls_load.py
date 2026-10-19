"""``polls/loaders/polls.py`` and the ``ingest-polls`` command.

Real database in isolated test schemas (``conftest.py``); snapshots are copies
of the fixtures in ``fixtures/wikipedia_polls/`` or inline synthetic strings,
never network or ``refs/``.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ingestor import cli
from ingestor.errors import IngestError
from ingestor.models import (
    AutonomousCommunity,
    Election,
    Ingestion,
    Municipality,
    Party,
    Poll,
    PollResult,
    Pollster,
    Province,
)
from ingestor.parties import load_catalog
from ingestor.polls.adapters.wikipedia_polls import parse_polls
from ingestor.polls.loaders.polls import ingest_polls_path, resolve_poll_elections

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wikipedia_polls"
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_SUBDIR = Path("polls") / "wikipedia-en" / "2026-general"


def _write_snapshot(tmp_path: Path, revid: int, wikitext: str) -> Path:
    """A ``{revid}.wikitext`` snapshot under ``tmp_path``'s bronze layout."""
    path = tmp_path / RAW_SUBDIR / f"{revid}.wikitext"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(wikitext, encoding="utf-8")
    return path


def _snapshot(tmp_path: Path, revid: int, fixture: str = "load_small.wikitext") -> Path:
    """Copy a fixture into ``tmp_path`` as ``{revid}.wikitext``."""
    return _write_snapshot(
        tmp_path, revid, (FIXTURES / fixture).read_text(encoding="utf-8")
    )


# --- Test database (T1) -----------------------------------------------------


def test_database_fixture(db):  # test infra
    with db() as session:
        assert session.scalar(select(1)) == 1
        schemas = set(
            session.scalars(text("SELECT schema_name FROM information_schema.schemata"))
        )
    assert {"polls_test_bronze", "polls_test_silver"} <= schemas


# --- Fixtures and helper (T2) -----------------------------------------------


def test_load_fixtures_parse(tmp_path):  # test infra
    path = _snapshot(tmp_path, 200)
    assert path == tmp_path / RAW_SUBDIR / "200.wikitext"
    small = parse_polls(path.read_text(encoding="utf-8"))
    assert [row.pollster_name for row in small] == ["Alpha", "CIS"]
    assert (small[0].fieldwork_start, small[0].fieldwork_end) == (
        date(2026, 10, 1),
        date(2026, 10, 2),
    )
    assert (small[1].fieldwork_start, small[1].fieldwork_end) == (None, None)
    assert small[0].results["pp"].seats_min == 141
    assert small[1].results["pp"].seats_max == 137
    assert small[1].results["salf"].seats_min is None
    other = parse_polls(_snapshot(tmp_path, 100, "load_other.wikitext").read_text())
    assert [row.pollster_name for row in other] == ["Beta"]
    assert other[0].results["psoe"].pct == Decimal("28.4")


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


def _use_cli(db, tmp_path, monkeypatch) -> None:
    """Point the CLI at the test factory and a temporary bronze root."""
    monkeypatch.setattr(cli, "SessionLocal", db)
    monkeypatch.setattr(cli, "configure_logging", lambda: None)
    monkeypatch.setattr(cli.settings, "raw_dir", tmp_path)


def _ingest(
    db,
    tmp_path: Path,
    revid: int,
    fixture: str = "load_small.wikitext",
    force: bool = False,
):
    """Load a fixture snapshot into silver through the loader."""
    return ingest_polls_path(
        db, _snapshot(tmp_path, revid, fixture), tmp_path, force=force
    )


# --- Happy path: CLI registers and loads (T3: R1, R3-R8, R23, R25) ----------


def test_cli_registers_and_loads(db, tmp_path, monkeypatch):  # R1, R3-R8, R23, R25
    snapshot = _snapshot(tmp_path, 200)
    _use_cli(db, tmp_path, monkeypatch)

    assert cli.main(["ingest-polls", str(snapshot)]) == 0

    with db() as session:
        (ingestion,) = session.scalars(select(Ingestion))
        assert ingestion.file_path == str(RAW_SUBDIR / "200.wikitext")
        assert ingestion.sha256 == hashlib.sha256(snapshot.read_bytes()).hexdigest()
        assert ingestion.size_bytes == snapshot.stat().st_size
        assert ingestion.source == "wikipedia-en"
        assert ingestion.status == "processed"

        pollsters = {row.slug: row for row in session.scalars(select(Pollster))}
        assert set(pollsters) == {"alpha", "cis"}
        assert pollsters["alpha"].name == "Alpha"
        assert pollsters["cis"].name == "CIS"

        parties = {row.slug: row for row in session.scalars(select(Party))}
        assert set(parties) == {"pp", "psoe", "salf"}
        catalog = load_catalog()
        assert parties["salf"].name == "Se Acabó La Fiesta"
        assert parties["pp"].name == catalog.lookup("PP").name
        assert parties["psoe"].name == catalog.lookup("PSOE").name

        polls = {row.source: row for row in session.scalars(select(Poll))}
        assert set(polls) == {"Alpha/Medio", "CIS (Target Point)"}
        alpha, cis = polls["Alpha/Medio"], polls["CIS (Target Point)"]
        assert alpha.pollster_id == pollsters["alpha"].id
        assert alpha.election_type == "congress"
        assert alpha.election_id is None
        assert alpha.revision_id == 200
        assert (alpha.fieldwork_start, alpha.fieldwork_end) == (
            date(2026, 10, 1),
            date(2026, 10, 2),
        )
        assert alpha.sample_size == 1000
        assert alpha.turnout == Decimal("67.6")
        assert cis.pollster_id == pollsters["cis"].id
        assert cis.revision_id == 200
        assert (cis.fieldwork_start, cis.fieldwork_end) == (None, None)
        assert cis.sample_size is None
        assert cis.turnout is None

        alpha_results = _results(session, alpha.id)
        assert set(alpha_results) == {"pp", "psoe", "salf"}
        assert alpha_results["pp"].pct == Decimal("32.6")
        assert (alpha_results["pp"].seats_min, alpha_results["pp"].seats_max) == (
            141,
            141,
        )
        assert alpha_results["salf"].pct == Decimal("3.2")
        assert (alpha_results["salf"].seats_min, alpha_results["salf"].seats_max) == (
            0,
            0,
        )
        cis_results = _results(session, cis.id)
        assert (cis_results["pp"].seats_min, cis_results["pp"].seats_max) == (135, 137)
        assert cis_results["psoe"].pct == Decimal("29.5")
        assert (cis_results["salf"].seats_min, cis_results["salf"].seats_max) == (
            None,
            None,
        )


# --- Reuse and replacement (T5: R3, R4, R7) ---------------------------------


def test_existing_party_and_pollster_reused(db, tmp_path):  # R3, R4
    with db() as session:
        pollster = Pollster(name="Alpha Custom", slug="alpha")
        party = Party(name="Partido Popular Custom", slug="pp")
        session.add_all([pollster, party])
        session.commit()
        pollster_id, party_id = pollster.id, party.id

    _ingest(db, tmp_path, 200)

    with db() as session:
        pollsters = {row.slug: row for row in session.scalars(select(Pollster))}
        assert set(pollsters) == {"alpha", "cis"}
        assert pollsters["alpha"].id == pollster_id
        assert pollsters["alpha"].name == "Alpha Custom"
        parties = {row.slug: row for row in session.scalars(select(Party))}
        assert set(parties) == {"pp", "psoe", "salf"}
        assert parties["pp"].id == party_id
        assert parties["pp"].name == "Partido Popular Custom"


def test_replacement_deletes_previous_polls(db, tmp_path):  # R7
    _ingest(db, tmp_path, 200)
    _ingest(db, tmp_path, 300, "load_other.wikitext")

    with db() as session:
        polls = list(session.scalars(select(Poll)))
        assert [poll.source for poll in polls] == ["Beta/Medio"]
        assert polls[0].revision_id == 300
        results = list(session.scalars(select(PollResult)))
        assert {result.pct for result in results} == {
            Decimal("28.4"),
            Decimal("33.1"),
        }
        pollsters = {row.slug for row in session.scalars(select(Pollster))}
        assert pollsters == {"alpha", "cis", "beta"}
        parties = {row.slug for row in session.scalars(select(Party))}
        assert parties == {"pp", "psoe", "salf"}


# --- Revision guard (T7: R9, R10, R11) --------------------------------------


def test_skip_processed(db, tmp_path, monkeypatch, caplog):  # R9, R25
    _ingest(db, tmp_path, 200)
    with db() as session:
        before = [poll.id for poll in session.scalars(select(Poll).order_by(Poll.id))]

    _use_cli(db, tmp_path, monkeypatch)
    with caplog.at_level(logging.INFO):
        assert (
            cli.main(["ingest-polls", str(tmp_path / RAW_SUBDIR / "200.wikitext")]) == 0
        )
    assert "already processed" in caplog.text

    with db() as session:
        after = [poll.id for poll in session.scalars(select(Poll).order_by(Poll.id))]
        assert after == before
        assert len(list(session.scalars(select(Ingestion)))) == 1


def test_guard_ignores_older_revision(db, tmp_path, monkeypatch, caplog):  # R10, R25
    _ingest(db, tmp_path, 200)
    old = _snapshot(tmp_path, 100, "load_other.wikitext")

    _use_cli(db, tmp_path, monkeypatch)
    with caplog.at_level(logging.WARNING):
        assert cli.main(["ingest-polls", str(old)]) == 0
    assert "older than" in caplog.text

    with db() as session:
        polls = list(session.scalars(select(Poll)))
        assert [poll.revision_id for poll in polls] == [200, 200]
        assert [poll.source for poll in polls] == ["Alpha/Medio", "CIS (Target Point)"]
        assert len(list(session.scalars(select(Ingestion)))) == 1


def test_force_reloads_processed_and_older(db, tmp_path):  # R11
    _ingest(db, tmp_path, 200)
    (outcome,) = _ingest(db, tmp_path, 200, force=True)
    assert outcome.status == "processed"
    (outcome,) = _ingest(db, tmp_path, 100, "load_other.wikitext", force=True)
    assert outcome.status == "processed"

    with db() as session:
        polls = list(session.scalars(select(Poll)))
        assert [poll.revision_id for poll in polls] == [100]
        assert [poll.source for poll in polls] == ["Beta/Medio"]


# --- Election resolution (T9: R12-R16, R24) ---------------------------------


def _seed_geography(db) -> None:
    with db() as session:
        session.add(AutonomousCommunity(ine_code="01", name="Testland"))
        session.flush()
        session.add(
            Province(
                ine_code="01",
                autonomous_community_ine_code="01",
                name="Test Province",
            )
        )
        session.flush()
        session.add(
            Municipality(ine_code="01001", province_ine_code="01", name="Testville")
        )
        session.commit()


def _add_poll(
    session: Session, fieldwork_end: date | None, election_type: str = "congress"
) -> Poll:
    pollster = session.scalar(select(Pollster).where(Pollster.slug == "manual"))
    if pollster is None:
        pollster = Pollster(name="Manual", slug="manual")
        session.add(pollster)
        session.flush()
    poll = Poll(
        pollster_id=pollster.id,
        source="Manual/Test",
        election_type=election_type,
        fieldwork_start=fieldwork_end,
        fieldwork_end=fieldwork_end,
        sample_size=1000,
        turnout=None,
        revision_id=1,
    )
    session.add(poll)
    session.flush()
    return poll


def test_resolution_links_after_fieldwork(db):  # R12
    _seed_geography(db)
    with db() as session:
        municipality_id = session.scalar(select(Municipality.id))
        session.add_all(
            [
                Election(type="congress", date=date(2026, 10, 11)),  # same day
                Election(type="congress", date=date(2026, 11, 1)),  # first after
                Election(type="congress", date=date(2027, 5, 1)),
                Election(
                    type="congress",
                    date=date(2026, 10, 15),
                    autonomous_community_ine_code="01",
                ),
                Election(
                    type="congress",
                    date=date(2026, 10, 20),
                    municipality_id=municipality_id,
                ),
                Election(type="senate", date=date(2026, 10, 12)),
            ]
        )
        poll = _add_poll(session, date(2026, 10, 11))
        session.commit()
        poll_id = poll.id

    assert resolve_poll_elections(db) == 1

    with db() as session:
        expected = session.scalar(
            select(Election.id).where(Election.date == date(2026, 11, 1))
        )
        assert session.get(Poll, poll_id).election_id == expected


def test_resolution_leaves_unmatched_and_null_fieldwork(db):  # R13, R14
    _seed_geography(db)
    with db() as session:
        session.add(Election(type="congress", date=date(2027, 5, 1)))
        past = _add_poll(session, date(2028, 1, 1))
        unknown = _add_poll(session, None)
        session.commit()
        past_id, unknown_id = past.id, unknown.id

    assert resolve_poll_elections(db) == 0

    with db() as session:
        assert session.get(Poll, past_id).election_id is None
        assert session.get(Poll, unknown_id).election_id is None


def test_resolution_runs_without_pending_snapshots(
    db, tmp_path, monkeypatch
):  # R15, R24, R25
    _seed_geography(db)
    with db() as session:
        session.add(Election(type="congress", date=date(2027, 5, 1)))
        poll = _add_poll(session, date(2026, 10, 11))
        session.commit()
        poll_id = poll.id

    (tmp_path / "polls").mkdir()
    _use_cli(db, tmp_path, monkeypatch)
    assert cli.main(["ingest-polls"]) == 0

    with db() as session:
        assert session.get(Poll, poll_id).election_id is not None


def test_resolution_is_idempotent(db):  # R16
    _seed_geography(db)
    with db() as session:
        session.add(Election(type="congress", date=date(2027, 5, 1)))
        poll = _add_poll(session, date(2026, 10, 11))
        session.commit()
        poll_id = poll.id

    assert resolve_poll_elections(db) == 1
    with db() as session:
        linked = session.get(Poll, poll_id).election_id
        session.add(Election(type="congress", date=date(2026, 12, 1)))
        session.commit()

    assert resolve_poll_elections(db) == 0
    with db() as session:
        assert session.get(Poll, poll_id).election_id == linked


# --- Validations and failure (T11: R17-R22) ---------------------------------


def _table(*rows: tuple[str, ...], parties: tuple[str, ...] = ("PP", "PSOE")) -> str:
    """A minimal polls table (fixed columns + party columns) with the given rows."""
    header = (
        "====Voting intention estimates====\n"
        "=====2026=====\n"
        '{| class="wikitable"\n'
        "|-\n"
        "! Polling firm/Commissioner\n"
        "! Fieldwork date\n"
        "! Sample size\n"
        "! Turnout\n" + "".join(f"! {party}\n" for party in parties)
    )
    body = "".join("|-\n" + "".join(f"| {cell}\n" for cell in row) for row in rows)
    return header + body + "|}\n"


def _assert_failed(db, tmp_path, revid, wikitext, caplog, message) -> None:
    """Load a bad snapshot: failed outcome, message and failed bronze state."""
    bad = _write_snapshot(tmp_path, revid, wikitext)
    with caplog.at_level(logging.ERROR):
        (outcome,) = ingest_polls_path(db, bad, tmp_path)
    assert outcome.status == "failed"
    assert message in caplog.text
    with db() as session:
        statuses = [
            row.status
            for row in session.scalars(select(Ingestion))
            if row.file_path.endswith(f"{revid}.wikitext")
        ]
        assert statuses == ["failed"]


def _assert_silver_intact(db) -> None:
    """The previous good load (revision 200) is still the only silver content."""
    with db() as session:
        polls = list(session.scalars(select(Poll)))
        assert [poll.revision_id for poll in polls] == [200, 200]
        assert [poll.source for poll in polls] == ["Alpha/Medio", "CIS (Target Point)"]


def test_missing_signature_fails(db, tmp_path, caplog):  # R17, R22
    _ingest(db, tmp_path, 200)
    _assert_failed(
        db,
        tmp_path,
        300,
        _table(("", "1 Oct", "1,000", "67.6", "30.0", "28.0")),
        caplog,
        "no signature",
    )
    _assert_failed(
        db,
        tmp_path,
        301,
        _table(("/(Medio)", "1 Oct", "1,000", "67.6", "30.0", "28.0")),
        caplog,
        "no signature",
    )
    _assert_silver_intact(db)


def test_fewer_than_two_parties_fails(db, tmp_path, caplog):  # R18, R22
    _ingest(db, tmp_path, 200)
    _assert_failed(
        db,
        tmp_path,
        300,
        _table(("Alpha/Medio", "1 Oct", "1,000", "67.6", "30.0", "?")),
        caplog,
        "fewer than two parties",
    )
    _assert_silver_intact(db)


def test_pct_turnout_and_seats_out_of_range_fail(db, tmp_path, caplog):  # R19, R22
    _ingest(db, tmp_path, 200)
    _assert_failed(
        db,
        tmp_path,
        300,
        _table(("Alpha/Medio", "1 Oct", "1,000", "67.6", "150", "28.0")),
        caplog,
        "out of range",
    )
    _assert_failed(
        db,
        tmp_path,
        301,
        _table(
            (
                "Alpha/Medio",
                "1 Oct",
                "1,000",
                "67.6",
                "30.0<br/>{{font|size=75%|font=Verdana|text=400}}",
                "28.0",
            )
        ),
        caplog,
        "out of range",
    )
    _assert_failed(
        db,
        tmp_path,
        302,
        _table(
            (
                "Alpha/Medio",
                "1 Oct",
                "1,000",
                "67.6",
                "30.0<br/>{{font|size=75%|font=Verdana|text=200/100}}",
                "28.0",
            )
        ),
        caplog,
        "out of range",
    )
    _assert_failed(
        db,
        tmp_path,
        303,
        _table(("Alpha/Medio", "1 Oct", "1,000", "101", "30.0", "28.0")),
        caplog,
        "out of range",
    )
    _assert_silver_intact(db)


def test_pct_sum_warns_and_loads(db, tmp_path, caplog):  # R20
    _ingest(db, tmp_path, 200)
    with caplog.at_level(logging.WARNING):
        (outcome,) = ingest_polls_path(
            db,
            _write_snapshot(
                tmp_path,
                300,
                _table(("Alpha/Medio", "1 Oct", "1,000", "67.6", "60.0", "45.0")),
            ),
            tmp_path,
        )
    assert outcome.status == "processed"
    assert "percentages add up to" in caplog.text
    with db() as session:
        (poll,) = session.scalars(select(Poll))
        assert poll.revision_id == 300
        assert len(_results(session, poll.id)) == 2


def test_empty_snapshot_fails_and_keeps_silver(db, tmp_path, caplog):  # R21, R22
    _ingest(db, tmp_path, 200)
    _assert_failed(db, tmp_path, 300, "== Nothing to see ==\n", caplog, "no polls")
    _assert_silver_intact(db)


# --- Paths and exit codes (T13: R25-R28) ------------------------------------


def test_missing_path_raises(db, tmp_path):  # R26
    with pytest.raises(IngestError):
        ingest_polls_path(db, tmp_path / "nope", tmp_path)


def test_snapshot_outside_raw_dir_raises(db, tmp_path):  # R27
    snapshot = _snapshot(tmp_path, 200)
    with pytest.raises(IngestError):
        ingest_polls_path(db, snapshot, tmp_path / "raw")


def test_bad_snapshot_filename_raises(db, tmp_path):  # R28
    bad = tmp_path / RAW_SUBDIR / "notarevid.wikitext"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("irrelevant", encoding="utf-8")
    with pytest.raises(IngestError):
        ingest_polls_path(db, bad, tmp_path)


def test_cli_exit_codes(db, tmp_path, monkeypatch):  # R25
    _use_cli(db, tmp_path, monkeypatch)
    bad = _write_snapshot(tmp_path, 300, "== Nothing to see ==\n")
    assert cli.main(["ingest-polls", str(bad)]) == 1
    bad.unlink()
    assert cli.main(["ingest-polls"]) == 0


def test_directory_processes_in_revision_order(db, tmp_path):  # R23
    _snapshot(tmp_path, 99, "load_other.wikitext")
    _snapshot(tmp_path, 200)
    outcomes = ingest_polls_path(db, tmp_path / "polls", tmp_path)
    assert [(outcome.revision_id, outcome.status) for outcome in outcomes] == [
        (99, "processed"),
        (200, "processed"),
    ]
    with db() as session:
        polls = list(session.scalars(select(Poll)))
        assert [poll.revision_id for poll in polls] == [200, 200]


def test_cli_default_path_processes_recursively(db, tmp_path, monkeypatch):  # R24
    _snapshot(tmp_path, 200)
    _use_cli(db, tmp_path, monkeypatch)
    assert cli.main(["ingest-polls"]) == 0
    with db() as session:
        assert len(list(session.scalars(select(Poll)))) == 2


# --- Unknown party labels (R31) ---------------------------------------------


def test_unknown_label_creates_party_with_warning(db, tmp_path, caplog):  # R31
    with caplog.at_level(logging.WARNING):
        (outcome,) = ingest_polls_path(
            db,
            _write_snapshot(
                tmp_path,
                200,
                _table(
                    ("Alpha/Medio", "1 Oct", "1,000", "67.6", "30.0", "5.0"),
                    parties=("PP", "FA"),
                ),
            ),
            tmp_path,
        )
    assert outcome.status == "processed"
    assert "unknown party label" in caplog.text
    assert "FA" in caplog.text
    with db() as session:
        fa = session.scalar(select(Party).where(Party.slug == "fa"))
        assert fa.name == "FA"
        fa_id = fa.id
        (poll,) = session.scalars(select(Poll))
        assert _results(session, poll.id)["fa"].pct == Decimal("5.0")

    (outcome,) = ingest_polls_path(
        db,
        _write_snapshot(
            tmp_path,
            201,
            _table(
                ("Alpha/Medio", "1 Oct", "1,000", "67.6", "31.0", "5.0"),
                parties=("PP", "FA"),
            ),
        ),
        tmp_path,
    )
    assert outcome.status == "processed"
    with db() as session:
        (reused,) = session.scalars(select(Party).where(Party.slug == "fa"))
        assert reused.id == fa_id


# --- Documentation (T15: R29, R30) ------------------------------------------


def test_docs_ingesta():  # R29
    docs = (REPO_ROOT / "docs" / "ingestor" / "ingesta.md").read_text(encoding="utf-8")
    for needle in (
        "ingest-polls",
        "wikipedia-en",
        "revision_id",
        "failed",
        "pollster",
        "poll_result",
    ):
        assert needle in docs


def test_docs_ingestor_agents():  # R30
    docs = (REPO_ROOT / "ingestor" / "AGENTS.md").read_text(encoding="utf-8")
    assert "ingest-polls" in docs
    assert "polls.py" in docs
