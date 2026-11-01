"""Election reload through the shared party resolver.

Integration in the throwaway test schemas (``db`` fixture, no ``data/raw`` and
no network) plus the document checks. The real reload, the orphan cleanup and
the R7-R10 state checks are the implementer's CLI/SQL run, documented in
``progress/impl_party_reload.md``.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sqlalchemy import func, select

from ingestor.elections.loaders.election import ingest_path
from ingestor.models import (
    AutonomousCommunity,
    Party,
    PartyElection,
    Province,
    Turnout,
    Vote,
)

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
