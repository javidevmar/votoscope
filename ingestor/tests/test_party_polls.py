"""Polls through the shared party catalogue: loader and source↔election match.

The adapter's column resolution is covered in ``test_wikipedia_polls.py``; the
loader tests run against the throwaway test schemas of ``conftest.py`` (no
network, no ``data/raw``).
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
    PollResult,
    Province,
)
from ingestor.parties import load_catalog
from ingestor.polls.loaders import polls as polls_loader
from ingestor.polls.loaders.polls import ingest_polls_path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "party_reload"
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_SUBDIR = Path("polls") / "wikipedia-en" / "2026-general"


def _seed_geography(db) -> None:
    """CCAA 01 + province 04 (Abla), as in the 02200806 fixture."""
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


def _write_snapshot(tmp_path: Path, revid: int, wikitext: str) -> Path:
    """A ``{revid}.wikitext`` snapshot under ``tmp_path``'s bronze layout."""
    path = tmp_path / RAW_SUBDIR / f"{revid}.wikitext"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(wikitext, encoding="utf-8")
    return path


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


# --- Loader through the catalogue (T3: R8, R9) ------------------------------


def test_loader_resolves_catalog_only_label(db, tmp_path, caplog):  # R8
    snapshot = _write_snapshot(
        tmp_path,
        200,
        _table(
            ("Alpha/Medio", "1 Oct", "1,000", "67.6", "30.0", "12.0"),
            parties=("PP", "C's"),
        ),
    )
    with caplog.at_level(logging.WARNING):
        (outcome,) = ingest_polls_path(db, snapshot, tmp_path)

    assert outcome.status == "processed"
    assert "unknown party column" not in caplog.text
    assert "unknown party label" not in caplog.text
    catalog = load_catalog()
    with db() as session:
        parties = {party.slug: party for party in session.scalars(select(Party))}
        assert set(parties) == {"pp", "cs"}
        assert parties["pp"].name == catalog.lookup("PP").name
        assert parties["cs"].name == catalog.lookup("C's").name


def test_loader_has_no_local_party_mapping():  # R9
    assert not hasattr(polls_loader, "_PARTY_NAMES")
    assert not hasattr(polls_loader, "_party_slug")


# --- Polls and elections share one party row (T5: R11, R12) -----------------


def test_poll_and_election_share_party_row(db, tmp_path, caplog):  # R11, R12
    _seed_geography(db)
    root = tmp_path / "congreso"
    shutil.copytree(FIXTURES / "02200806", root / "02200806")
    assert [outcome.status for outcome in ingest_path(db, root, tmp_path)] == [
        "processed"
    ]

    with caplog.at_level(logging.WARNING):
        (outcome,) = ingest_polls_path(
            db,
            _write_snapshot(
                tmp_path,
                200,
                _table(
                    ("Alpha/Medio", "1 Oct", "1,000", "67.6", "30.0", "11.0"),
                    parties=("PP", "BNG"),
                ),
            ),
            tmp_path,
        )

    assert outcome.status == "processed"
    assert "unknown party label" not in caplog.text
    with db() as session:
        bng = session.scalar(select(Party).where(Party.slug == "bng"))
        assert bng.name == "BNG"
        (candidacy,) = session.scalars(select(PartyElection))
        (result,) = session.scalars(
            select(PollResult).where(PollResult.party_id == bng.id)
        )
        assert candidacy.party_id == bng.id
        assert result.party_id == bng.id
        before = session.scalar(select(func.count()).select_from(Party))

    (outcome,) = ingest_polls_path(
        db,
        _write_snapshot(
            tmp_path,
            201,
            _table(
                ("Alpha/Medio", "1 Oct", "1,000", "67.6", "31.0", "11.0"),
                parties=("PP", "BNG"),
            ),
        ),
        tmp_path,
    )

    assert outcome.status == "processed"
    with db() as session:
        assert session.scalar(select(func.count()).select_from(Party)) == before


# --- Documentation (T6: R13, R14) -------------------------------------------


def _section(text: str, heading: str) -> str:
    """Body of the level-2 section that starts with ``heading``."""
    start = text.index(heading) + len(heading)
    body = text[start:]
    end = body.find("\n## ")
    return body if end == -1 else body[:end]


def test_docs_ingesta_polls_mapping():  # R13, R14
    text = (REPO_ROOT / "docs" / "ingestor" / "ingesta.md").read_text(encoding="utf-8")
    section = _section(text, "## Comportamiento de `ingest-polls`")
    assert "parties.py" in section
    assert "party_catalog.toml" in section
    assert "slugs del mapeo" not in text
