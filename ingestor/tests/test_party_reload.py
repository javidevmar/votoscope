"""Election reload through the shared party resolver.

Two blocks: integration in the throwaway test schemas (``db`` fixture, no
``data/raw`` and no network) and read-only checks of the real local ``silver``
state (they skip without Postgres or local data). The real reload and the
orphan cleanup are the implementer's CLI/SQL run, documented in
``progress/impl_party_reload.md``.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ingestor.elections.loaders.election import ingest_path
from ingestor.models import (
    AutonomousCommunity,
    Party,
    PartyElection,
    Province,
    Turnout,
    Vote,
)
from ingestor.settings import settings

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "party_reload"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _seed_geography(db) -> None:
    """CCAA 01 + province 04 (Abla), as in the 02202307 fixture."""
    with db() as session:
        session.add(AutonomousCommunity(ine_code="01", name="Andalucía"))
        session.flush()
        session.add(
            Province(
                ine_code="04",
                autonomous_community_ine_code="01",
                name="Almería",
            )
        )
        session.commit()


def _copy_fixtures(tmp_path: Path, *codes: str) -> Path:
    """Copy ``fixtures/party_reload/<code>/`` to the bronze root; return it."""
    root = tmp_path / "congreso"
    for code in codes:
        shutil.copytree(FIXTURES / code, root / code)
    return root


def _real_session() -> Session:
    """Session over ``settings.database_url``; skip when Postgres is down or empty."""
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            has_party_table = inspect(connection).has_table("party", schema="silver")
    except OperationalError:
        engine.dispose()
        pytest.skip("Postgres is not reachable (docker compose up -d --wait)")
    if not has_party_table:
        engine.dispose()
        pytest.skip("silver schema is not created (alembic upgrade head)")
    session = Session(engine)
    if session.scalar(select(func.count()).select_from(Party)) == 0:
        session.close()
        engine.dispose()
        pytest.skip("silver has no local data (local run only)")
    return session


# --- Resolver integration (T2: R1-R6) ---------------------------------------


def test_two_processes_one_party(db, tmp_path, caplog):  # R1, R2, R3
    _seed_geography(db)
    root = _copy_fixtures(tmp_path, "02200806", "02201905")

    with caplog.at_level(logging.WARNING):
        outcomes = ingest_path(db, root, tmp_path)

    assert [outcome.status for outcome in outcomes] == ["processed", "processed"]
    with db() as session:
        parties = list(session.scalars(select(Party)))
        assert [(party.slug, party.name) for party in parties] == [("bng", "BNG")]
        candidacies = list(session.scalars(select(PartyElection)))
        assert len(candidacies) == 2
        assert {candidacy.party_id for candidacy in candidacies} == {parties[0].id}
        assert {candidacy.short_name for candidacy in candidacies} == {
            "B.N.G.",
            "BNG",
        }
    assert "unknown party label" not in caplog.text


def test_unknown_head_label_warns(db, tmp_path, caplog):  # R4
    _seed_geography(db)
    root = _copy_fixtures(tmp_path, "02202601")

    with caplog.at_level(logging.WARNING):
        outcomes = ingest_path(db, root, tmp_path)

    assert [outcome.status for outcome in outcomes] == ["processed"]
    with db() as session:
        (party,) = list(session.scalars(select(Party)))
        assert party.name == "PARTIDO SIN FICHA"
        assert party.slug == "partido-sin-ficha"
    assert "unknown party label: PARTIDO SIN FICHA -> partido-sin-ficha" in caplog.text


def test_force_reload_preserves_facts(db, tmp_path):  # R5, R6
    _seed_geography(db)
    root = _copy_fixtures(tmp_path, "02200806", "02201905")
    ingest_path(db, root, tmp_path)
    with db() as session:
        party_id = session.scalar(select(Party.id))
        counts = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (PartyElection, Vote, Turnout)
        )

    outcomes = ingest_path(db, root, tmp_path, force=True)

    assert [outcome.status for outcome in outcomes] == ["processed", "processed"]
    with db() as session:
        assert session.scalar(select(func.count()).select_from(Party)) == 1
        assert session.scalar(select(Party.id)) == party_id
        assert (
            tuple(
                session.scalar(select(func.count()).select_from(model))
                for model in (PartyElection, Vote, Turnout)
            )
            == counts
        )


# --- Real silver state, read-only (T4: R7-R10) ------------------------------


def test_state_covers_13_processes():  # R7
    with _real_session() as session:
        covered = session.scalar(
            text(
                """
                SELECT count(*) FROM (
                    SELECT e.id
                    FROM silver.election e
                    JOIN silver.party_election pe ON pe.election_id = e.id
                    JOIN silver.vote v ON v.party_election_id = pe.id
                    WHERE e.type = 'congress'
                      AND e.autonomous_community_ine_code IS NULL
                      AND e.municipality_id IS NULL
                    GROUP BY e.id
                ) AS covered
                """
            )
        )
    assert covered == 13


def test_state_no_punctuation_groups():  # R8
    with _real_session() as session:
        groups = session.execute(
            text(
                """
                SELECT array_agg(slug) AS slugs, count(*)
                FROM silver.party
                GROUP BY upper(regexp_replace(name, '[^a-zA-Z0-9]', '', 'g'))
                HAVING count(*) > 1
                """
            )
        ).all()
    assert groups == []


def test_state_key_brands_single_row():  # R9
    with _real_session() as session:
        rows = session.execute(
            text(
                """
                SELECT p.slug, p.name, count(DISTINCT pe.election_id) AS procesos
                FROM silver.party p
                JOIN silver.party_election pe ON pe.party_id = p.id
                WHERE upper(regexp_replace(p.name, '[^a-zA-Z0-9]', '', 'g'))
                      IN ('BNG', 'UPL', 'FIA', 'CS', 'PP', 'PSOE', 'IU')
                GROUP BY p.id ORDER BY p.slug
                """
            )
        ).all()
    assert len(rows) == 7
    assert {row.name.upper() for row in rows} == {
        "BNG",
        "UPL",
        "FIA",
        "CS",
        "PP",
        "PSOE",
        "IU",
    }
    assert all(row.procesos >= 1 for row in rows)


def test_state_no_orphan_parties():  # R10
    with _real_session() as session:
        orphans = session.scalar(
            text(
                """
                SELECT count(*) FROM silver.party p
                WHERE NOT EXISTS (
                        SELECT 1 FROM silver.party_election pe
                        WHERE pe.party_id = p.id)
                  AND NOT EXISTS (
                        SELECT 1 FROM silver.poll_result pr
                        WHERE pr.party_id = p.id)
                """
            )
        )
    assert orphans == 0


# --- Documents (T7: R11-R15) ------------------------------------------------


def _doc(*parts: str) -> str:
    return (REPO_ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_docs_data_model():  # R11, R12
    text = _doc(".agents", "data-model.md")
    assert "parties.py" in text
    assert "party_catalog.toml" in text
    assert "provisional" not in text.lower()


def test_docs_ingesta():  # R13, R14
    text = _doc("docs", "ingestor", "ingesta.md")
    assert "parties.py" in text
    assert "party_catalog.toml" in text
    assert "provisional" not in text.lower()


def test_docs_ingestor_agents():  # R15
    text = _doc("ingestor", "AGENTS.md")
    assert "parties.py" in text
    assert "party_catalog.toml" in text
