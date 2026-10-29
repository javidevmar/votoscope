"""Gold layer: read-only views, contract documents and curated party colours.

Metadata and document checks run without a database. The behaviour checks use
the throwaway test schemas: ``conftest`` creates the six views there with the
same ``gold.view_ddl()`` statements the migration applies, so the tests
exercise the deployed SQL.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import (
    BigInteger,
    Date,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    inspect,
    select,
    text,
)
from sqlalchemy.exc import OperationalError

from ingestor.errors import IngestError
from ingestor.models import (
    AutonomousCommunity,
    Base,
    Election,
    Municipality,
    Party,
    PartyElection,
    Poll,
    PollingStation,
    PollResult,
    Pollster,
    Province,
    Turnout,
    Vote,
)
from ingestor.parties import PartyResolver, load_catalog
from ingestor.settings import settings

REPO_ROOT = Path(__file__).resolve().parents[2]

# Expected columns of every view, in order (the contract of the web frontend).
GOLD_VIEWS: dict[str, list[str]] = {
    "election_summary": [
        "election_id",
        "election_type",
        "election_date",
        "election_name",
        "census",
        "null_votes",
        "blank_votes",
        "candidature_votes",
        "valid_votes",
        "voters",
        "turnout_pct",
    ],
    "result_by_area": [
        "election_id",
        "level",
        "community_ine_code",
        "community_name",
        "province_ine_code",
        "province_name",
        "municipality_id",
        "municipality_ine_code",
        "municipality_name",
        "party_id",
        "party_slug",
        "party_name",
        "party_color",
        "votes",
        "pct",
    ],
    "result_by_station": [
        "election_id",
        "polling_station_id",
        "district",
        "section",
        "code",
        "municipality_id",
        "municipality_ine_code",
        "municipality_name",
        "province_ine_code",
        "province_name",
        "community_ine_code",
        "community_name",
        "party_id",
        "party_slug",
        "party_name",
        "party_color",
        "votes",
        "pct",
    ],
    "station_turnout": [
        "election_id",
        "polling_station_id",
        "district",
        "section",
        "code",
        "municipality_id",
        "municipality_ine_code",
        "municipality_name",
        "province_ine_code",
        "province_name",
        "community_ine_code",
        "community_name",
        "census",
        "null_votes",
        "blank_votes",
        "candidature_votes",
        "valid_votes",
        "voters",
        "turnout_pct",
    ],
    "poll_flat": [
        "poll_id",
        "pollster_id",
        "pollster_slug",
        "pollster_name",
        "source",
        "election_type",
        "election_id",
        "fieldwork_start",
        "fieldwork_end",
        "sample_size",
        "turnout",
        "revision_id",
        "party_id",
        "party_slug",
        "party_name",
        "party_color",
        "pct",
        "seats_min",
        "seats_max",
    ],
    "poll_trend": [
        "poll_id",
        "poll_date",
        "pollster_slug",
        "pollster_name",
        "source",
        "revision_id",
        "election_type",
        "election_id",
        "party_id",
        "party_slug",
        "party_name",
        "party_color",
        "pct",
        "seats_min",
        "seats_max",
    ],
}

# The bronze/silver schema of today: the feature adds no aggregates there (R12).
SILVER_TABLES: dict[str, list[str]] = {
    "bronze.ingestion": [
        "id",
        "file_path",
        "sha256",
        "size_bytes",
        "source",
        "status",
        "created_at",
    ],
    "silver.autonomous_community": ["ine_code", "name"],
    "silver.province": ["ine_code", "autonomous_community_ine_code", "name"],
    "silver.municipality": ["id", "ine_code", "province_ine_code", "name"],
    "silver.polling_station": ["id", "municipality_id", "district", "section", "code"],
    "silver.election": [
        "id",
        "type",
        "date",
        "name",
        "autonomous_community_ine_code",
        "municipality_id",
    ],
    "silver.party": ["id", "name", "slug", "color"],
    "silver.party_election": [
        "id",
        "election_id",
        "party_id",
        "code",
        "short_name",
        "name",
    ],
    "silver.turnout": [
        "id",
        "polling_station_id",
        "election_id",
        "census",
        "blank_votes",
        "null_votes",
    ],
    "silver.vote": ["id", "polling_station_id", "party_election_id", "votes"],
    "silver.pollster": ["id", "name", "slug"],
    "silver.poll": [
        "id",
        "pollster_id",
        "source",
        "election_type",
        "election_id",
        "fieldwork_start",
        "fieldwork_end",
        "sample_size",
        "turnout",
        "revision_id",
    ],
    "silver.poll_result": [
        "id",
        "poll_id",
        "party_id",
        "pct",
        "seats_min",
        "seats_max",
    ],
}


def _table(name: str):
    return Base.metadata.tables[f"gold.{name}"]


# --- Metadata: the gold views are declared in models.py (R1) ----------------


def test_models_declare_gold_views():  # R1
    for name, columns in GOLD_VIEWS.items():
        table = _table(name)
        assert table.schema == "gold"
        assert table.info.get("view") is True
        assert [column.name for column in table.columns] == columns
        assert not list(table.primary_key.columns), f"{name} has a primary key"
        assert not any(column.foreign_keys for column in table.columns)
        assert not table.indexes


def test_gold_view_types():  # R1
    summary = _table("election_summary")
    assert isinstance(summary.c.election_id.type, Integer)
    assert isinstance(summary.c.election_date.type, Date)
    assert isinstance(summary.c.census.type, BigInteger)
    assert isinstance(summary.c.turnout_pct.type, Numeric)

    area = _table("result_by_area")
    assert isinstance(area.c.level.type, Text)
    assert isinstance(area.c.community_ine_code.type, Text)
    assert isinstance(area.c.party_slug.type, String)
    assert area.c.party_slug.type.length == 60
    assert isinstance(area.c.party_color.type, String)
    assert area.c.party_color.type.length == 7
    assert isinstance(area.c.votes.type, BigInteger)
    assert isinstance(area.c.pct.type, Numeric)

    station = _table("result_by_station")
    assert isinstance(station.c.district.type, String)
    assert station.c.district.type.length == 2
    assert isinstance(station.c.municipality_ine_code.type, String)
    assert station.c.municipality_ine_code.type.length == 5

    turnout = _table("station_turnout")
    assert isinstance(turnout.c.census.type, Integer)
    assert isinstance(turnout.c.candidature_votes.type, BigInteger)

    flat = _table("poll_flat")
    assert isinstance(flat.c.turnout.type, Numeric)
    assert (flat.c.turnout.type.precision, flat.c.turnout.type.scale) == (5, 2)
    assert isinstance(flat.c.pct.type, Numeric)
    assert (flat.c.pct.type.precision, flat.c.pct.type.scale) == (5, 2)
    assert isinstance(flat.c.revision_id.type, BigInteger)
    assert flat.c.election_id.nullable

    trend = _table("poll_trend")
    assert isinstance(trend.c.poll_date.type, Date)


# --- The view SQL lives only in gold.py (R2) --------------------------------


def test_view_ddl_is_single_source():  # R2
    from ingestor.gold import view_ddl

    ddl = view_ddl()
    assert list(ddl) == list(GOLD_VIEWS)
    for name, statement in ddl.items():
        assert statement.startswith(f"CREATE VIEW gold.{name} AS"), name

    custom = view_ddl(gold_schema="gold_test", silver_schema="silver_test")
    assert list(custom) == list(ddl)
    for name, statement in custom.items():
        assert statement.startswith(f"CREATE VIEW gold_test.{name} AS"), name
        assert "silver_test." in statement
        assert " silver." not in statement
        assert "{gold}" not in statement
        assert "{silver}" not in statement


def test_migration_executes_view_ddl():  # R2, R3
    migrations = sorted(
        (REPO_ROOT / "ingestor" / "alembic" / "versions").glob("*gold_views.py")
    )
    assert len(migrations) == 1
    source = migrations[0].read_text(encoding="utf-8")
    assert "view_ddl" in source
    assert "CREATE SCHEMA IF NOT EXISTS gold" in source
    assert "CREATE VIEW" not in source


# --- No aggregates land in silver (R12) -------------------------------------


def test_silver_metadata_has_no_new_aggregates():  # R12
    actual = {
        name: [column.name for column in table.columns]
        for name, table in Base.metadata.tables.items()
        if not name.startswith("gold.")
    }
    assert actual == SILVER_TABLES


# --- Behaviour against the throwaway schemas (gold.view_ddl() SQL) ----------

E1 = date(2023, 7, 23)
E2 = date(2019, 11, 10)


def _seed(db) -> dict[str, int]:
    """One CCAA, one province, two municipalities and two elections.

    Election 1: PP (coloured) and PSOE in two stations of Abla plus a station
    in Olula with no votes. Election 2: turnout but no votes.
    """
    with db() as session:
        session.add(AutonomousCommunity(ine_code="01", name="Andalucía"))
        session.add(
            Province(ine_code="04", autonomous_community_ine_code="01", name="Almería")
        )
        session.flush()
        abla = Municipality(ine_code="04001", province_ine_code="04", name="Abla")
        olula = Municipality(ine_code="04002", province_ine_code="04", name="Olula")
        session.add_all([abla, olula])
        session.flush()
        stations = [
            PollingStation(
                municipality_id=abla.id, district="01", section="0001", code="A"
            ),
            PollingStation(
                municipality_id=abla.id, district="01", section="0002", code="A"
            ),
            PollingStation(
                municipality_id=olula.id, district="02", section="0001", code="B"
            ),
        ]
        session.add_all(stations)
        first = Election(type="congress", date=E1)
        second = Election(type="congress", date=E2)
        pp = Party(name="PP", slug="pp", color="#1d84ce")
        psoe = Party(name="PSOE", slug="psoe")
        session.add_all([first, second, pp, psoe])
        session.flush()
        candidacies = [
            PartyElection(
                election_id=first.id,
                party_id=pp.id,
                code="01",
                short_name="PP",
                name="PARTIDO POPULAR",
            ),
            PartyElection(
                election_id=first.id,
                party_id=psoe.id,
                code="02",
                short_name="PSOE",
                name="PARTIDO SOCIALISTA OBRERO ESPAÑOL",
            ),
        ]
        session.add_all(candidacies)
        session.flush()
        session.add_all(
            [
                Turnout(
                    polling_station_id=stations[0].id,
                    election_id=first.id,
                    census=100,
                    blank_votes=5,
                    null_votes=3,
                ),
                Turnout(
                    polling_station_id=stations[1].id,
                    election_id=first.id,
                    census=100,
                    blank_votes=2,
                    null_votes=1,
                ),
                Turnout(
                    polling_station_id=stations[2].id,
                    election_id=first.id,
                    census=10,
                    blank_votes=0,
                    null_votes=0,
                ),
                Turnout(
                    polling_station_id=stations[0].id,
                    election_id=second.id,
                    census=50,
                    blank_votes=0,
                    null_votes=0,
                ),
                Vote(
                    polling_station_id=stations[0].id,
                    party_election_id=candidacies[0].id,
                    votes=60,
                ),
                Vote(
                    polling_station_id=stations[0].id,
                    party_election_id=candidacies[1].id,
                    votes=40,
                ),
                Vote(
                    polling_station_id=stations[1].id,
                    party_election_id=candidacies[0].id,
                    votes=30,
                ),
                Vote(
                    polling_station_id=stations[1].id,
                    party_election_id=candidacies[1].id,
                    votes=20,
                ),
            ]
        )
        session.commit()
        return {
            "election": first.id,
            "election2": second.id,
            "abla": abla.id,
            "olula": olula.id,
            "station_a1": stations[0].id,
            "station_a2": stations[1].id,
            "station_b1": stations[2].id,
            "pp": pp.id,
            "psoe": psoe.id,
        }


def _rows(db, view: str, *where) -> list[dict]:
    table = _table(view)
    with db() as session:
        return list(session.execute(select(table).where(*where)).mappings())


def test_election_summary_aggregates(db):  # R5, R11
    ids = _seed(db)
    rows = _rows(db, "election_summary")

    assert len(rows) == 2
    summary = next(row for row in rows if row["election_id"] == ids["election"])
    assert summary["election_type"] == "congress"
    assert summary["election_date"] == E1
    assert summary["election_name"] is None
    assert summary["census"] == 210
    assert summary["null_votes"] == 4
    assert summary["blank_votes"] == 7
    assert summary["candidature_votes"] == 150
    assert summary["valid_votes"] == 157
    assert summary["voters"] == 161
    assert summary["turnout_pct"] == Decimal("76.67")

    empty = next(row for row in rows if row["election_id"] == ids["election2"])
    assert empty["candidature_votes"] == 0
    assert empty["valid_votes"] == 0
    assert empty["voters"] == 0
    assert empty["turnout_pct"] == Decimal("0.00")


def test_result_by_area_grain_and_levels(db):  # R6
    ids = _seed(db)
    rows = _rows(
        db, "result_by_area", _table("result_by_area").c.election_id == ids["election"]
    )

    keys = [
        (
            row["level"],
            row["community_ine_code"],
            row["province_ine_code"],
            row["municipality_id"],
            row["party_id"],
        )
        for row in rows
    ]
    assert len(keys) == len(set(keys)) == 8
    assert {row["level"] for row in rows} == {
        "national",
        "community",
        "province",
        "municipality",
    }

    national = [row for row in rows if row["level"] == "national"]
    assert len(national) == 2
    for row in national:
        assert row["community_ine_code"] is None
        assert row["community_name"] is None
        assert row["province_ine_code"] is None
        assert row["province_name"] is None
        assert row["municipality_id"] is None
        assert row["municipality_ine_code"] is None
        assert row["municipality_name"] is None

    community = [row for row in rows if row["level"] == "community"]
    assert len(community) == 2
    for row in community:
        assert row["community_ine_code"] == "01"
        assert row["community_name"] == "Andalucía"
        assert row["province_ine_code"] is None
        assert row["municipality_id"] is None

    province = [row for row in rows if row["level"] == "province"]
    assert len(province) == 2
    for row in province:
        assert row["community_ine_code"] == "01"
        assert row["province_ine_code"] == "04"
        assert row["province_name"] == "Almería"
        assert row["municipality_id"] is None
        assert row["municipality_ine_code"] is None

    municipality = [row for row in rows if row["level"] == "municipality"]
    assert len(municipality) == 2
    for row in municipality:
        assert row["community_ine_code"] == "01"
        assert row["province_ine_code"] == "04"
        assert row["municipality_id"] == ids["abla"]
        assert row["municipality_ine_code"] == "04001"
        assert row["municipality_name"] == "Abla"

    pp = next(row for row in national if row["party_slug"] == "pp")
    assert pp["party_id"] == ids["pp"]
    assert pp["party_name"] == "PP"
    assert pp["party_color"] == "#1d84ce"
    psoe = next(row for row in national if row["party_slug"] == "psoe")
    assert psoe["party_color"] is None


def test_result_by_area_pct_over_valid_votes(db):  # R6, R11
    ids = _seed(db)
    rows = _rows(
        db, "result_by_area", _table("result_by_area").c.election_id == ids["election"]
    )
    by_key = {(row["level"], row["party_slug"]): row for row in rows}

    # 90 / (150 + 7) = 57.32 and 60 / 157 = 38.22, at every level of the area.
    for level in ("national", "community", "province", "municipality"):
        assert by_key[(level, "pp")]["votes"] == 90
        assert by_key[(level, "pp")]["pct"] == Decimal("57.32")
        assert by_key[(level, "psoe")]["votes"] == 60
        assert by_key[(level, "psoe")]["pct"] == Decimal("38.22")

    # A row only exists for a party with votes, so the denominator cannot be 0
    # here: the NULL branch is guarded in the SQL with nullif.
    from ingestor.gold import view_ddl

    assert "nullif(" in view_ddl()["result_by_area"]


def test_result_by_station_identity_and_pct(db):  # R7
    ids = _seed(db)
    rows = _rows(
        db,
        "result_by_station",
        _table("result_by_station").c.election_id == ids["election"],
    )
    assert len(rows) == 4

    first = next(
        row
        for row in rows
        if row["polling_station_id"] == ids["station_a1"] and row["party_slug"] == "pp"
    )
    assert first["election_id"] == ids["election"]
    assert first["district"] == "01"
    assert first["section"] == "0001"
    assert first["code"] == "A"
    assert first["municipality_id"] == ids["abla"]
    assert first["municipality_ine_code"] == "04001"
    assert first["municipality_name"] == "Abla"
    assert first["province_ine_code"] == "04"
    assert first["province_name"] == "Almería"
    assert first["community_ine_code"] == "01"
    assert first["community_name"] == "Andalucía"
    assert first["party_color"] == "#1d84ce"
    assert first["votes"] == 60
    # 60 / (100 candidatures + 5 blanks) = 57.14
    assert first["pct"] == Decimal("57.14")

    second = next(
        row
        for row in rows
        if row["polling_station_id"] == ids["station_a2"]
        and row["party_slug"] == "psoe"
    )
    # 20 / (50 + 2) = 38.46
    assert second["votes"] == 20
    assert second["pct"] == Decimal("38.46")


def test_station_turnout_derived_voters(db):  # R8, R11
    ids = _seed(db)
    rows = _rows(
        db,
        "station_turnout",
        _table("station_turnout").c.election_id == ids["election"],
    )
    assert len(rows) == 3

    first = next(row for row in rows if row["polling_station_id"] == ids["station_a1"])
    assert first["district"] == "01"
    assert first["section"] == "0001"
    assert first["code"] == "A"
    assert first["municipality_ine_code"] == "04001"
    assert first["municipality_name"] == "Abla"
    assert first["province_ine_code"] == "04"
    assert first["province_name"] == "Almería"
    assert first["community_ine_code"] == "01"
    assert first["community_name"] == "Andalucía"
    assert first["census"] == 100
    assert first["null_votes"] == 3
    assert first["blank_votes"] == 5
    assert first["candidature_votes"] == 100
    assert first["valid_votes"] == 105
    assert first["voters"] == 108
    assert first["turnout_pct"] == Decimal("108.00")

    no_votes = next(
        row for row in rows if row["polling_station_id"] == ids["station_b1"]
    )
    assert no_votes["municipality_name"] == "Olula"
    assert no_votes["province_name"] == "Almería"
    assert no_votes["community_name"] == "Andalucía"
    assert no_votes["candidature_votes"] == 0
    assert no_votes["valid_votes"] == 0
    assert no_votes["voters"] == 0
    assert no_votes["turnout_pct"] == Decimal("0.00")


def _seed_polls(db, ids: dict[str, int]) -> dict[str, int]:
    with db() as session:
        pollster = Pollster(name="ElectoPanel", slug="electo-panel")
        session.add(pollster)
        session.flush()
        polls = [
            Poll(
                pollster_id=pollster.id,
                source="ElectoPanel/El Plural",
                election_type="congress",
                election_id=ids["election"],
                fieldwork_start=date(2026, 1, 1),
                fieldwork_end=date(2026, 1, 5),
                sample_size=1000,
                turnout=Decimal("70.00"),
                revision_id=10,
            ),
            Poll(
                pollster_id=pollster.id,
                source="ElectoPanel/El Plural",
                election_type="congress",
                election_id=None,
                fieldwork_start=date(2025, 12, 1),
                fieldwork_end=None,
                sample_size=None,
                turnout=None,
                revision_id=11,
            ),
            Poll(
                pollster_id=pollster.id,
                source="ElectoPanel/El Plural",
                election_type="congress",
                election_id=None,
                fieldwork_start=None,
                fieldwork_end=None,
                sample_size=None,
                turnout=None,
                revision_id=12,
            ),
        ]
        session.add_all(polls)
        session.flush()
        session.add_all(
            [
                # psoe first: the poll_trend tie-break (party_slug) has to put
                # pp before psoe despite the insertion order.
                PollResult(
                    poll_id=polls[0].id,
                    party_id=ids["psoe"],
                    pct=Decimal("25.00"),
                    seats_min=None,
                    seats_max=None,
                ),
                PollResult(
                    poll_id=polls[0].id,
                    party_id=ids["pp"],
                    pct=Decimal("30.50"),
                    seats_min=120,
                    seats_max=130,
                ),
                PollResult(
                    poll_id=polls[1].id,
                    party_id=ids["psoe"],
                    pct=None,
                    seats_min=90,
                    seats_max=100,
                ),
                PollResult(
                    poll_id=polls[2].id,
                    party_id=ids["pp"],
                    pct=Decimal("20.00"),
                    seats_min=None,
                    seats_max=None,
                ),
            ]
        )
        session.commit()
        return {
            "poll1": polls[0].id,
            "poll2": polls[1].id,
            "poll3": polls[2].id,
            "pollster": pollster.id,
        }


def test_poll_flat_shape_and_nulls(db):  # R9
    ids = _seed(db)
    polls = _seed_polls(db, ids)
    rows = _rows(db, "poll_flat")
    assert len(rows) == 4

    first = next(
        row
        for row in rows
        if row["poll_id"] == polls["poll1"] and row["party_slug"] == "pp"
    )
    assert first["pollster_id"] == polls["pollster"]
    assert first["pollster_slug"] == "electo-panel"
    assert first["pollster_name"] == "ElectoPanel"
    assert first["source"] == "ElectoPanel/El Plural"
    assert first["election_type"] == "congress"
    assert first["election_id"] == ids["election"]
    assert first["fieldwork_start"] == date(2026, 1, 1)
    assert first["fieldwork_end"] == date(2026, 1, 5)
    assert first["sample_size"] == 1000
    assert first["turnout"] == Decimal("70.00")
    assert first["revision_id"] == 10
    assert first["party_color"] == "#1d84ce"
    assert first["pct"] == Decimal("30.50")
    assert (first["seats_min"], first["seats_max"]) == (120, 130)

    # The view filters nothing: the source NULLs arrive as they are.
    missing = next(
        row
        for row in rows
        if row["poll_id"] == polls["poll2"] and row["party_slug"] == "psoe"
    )
    assert missing["election_id"] is None
    assert missing["fieldwork_end"] is None
    assert missing["sample_size"] is None
    assert missing["turnout"] is None
    assert missing["party_color"] is None
    assert missing["pct"] is None
    assert (missing["seats_min"], missing["seats_max"]) == (90, 100)

    no_pct = next(
        row
        for row in rows
        if row["poll_id"] == polls["poll3"] and row["party_slug"] == "pp"
    )
    assert no_pct["pct"] == Decimal("20.00")
    assert no_pct["seats_min"] is None
    assert no_pct["seats_max"] is None


def test_poll_trend_ordered_by_fieldwork(db):  # R10
    ids = _seed(db)
    polls = _seed_polls(db, ids)
    rows = _rows(db, "poll_trend")

    # poll_date = fieldwork_end, else fieldwork_start; ascending, NULLs last,
    # then poll_id and party_slug. poll1 has pp and psoe on the same date and
    # psoe was inserted first: only the party_slug tie-break puts pp first.
    assert [(row["poll_id"], row["poll_date"]) for row in rows] == [
        (polls["poll2"], date(2025, 12, 1)),
        (polls["poll1"], date(2026, 1, 5)),
        (polls["poll1"], date(2026, 1, 5)),
        (polls["poll3"], None),
    ]
    assert [row["party_slug"] for row in rows] == ["psoe", "pp", "psoe", "pp"]
    assert rows[0]["pollster_slug"] == "electo-panel"
    assert rows[1]["pct"] == Decimal("30.50")

    with db() as session:
        definition = session.scalar(
            text("SELECT pg_get_viewdef('polls_test_gold.poll_trend'::regclass)")
        )
    # The whole ordering is contractual, not just the presence of ORDER BY.
    normalized = " ".join(definition.lower().split()).rstrip(";")
    assert normalized.endswith(
        "order by coalesce(p.fieldwork_end, p.fieldwork_start), p.id, pt.slug"
    )


# --- Live database: the migrated views match models.py (R1, R3) -------------


def _real_engine():
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        engine.dispose()
        pytest.skip("Postgres is not reachable (docker compose up -d --wait)")
    return engine


def test_live_gold_views_match_models():  # R1, R3
    engine = _real_engine()
    try:
        inspector = inspect(engine)
        if "gold" not in inspector.get_schema_names():
            pytest.skip("gold schema missing (uv run alembic upgrade head)")
        existing = set(inspector.get_view_names(schema="gold"))
        missing = sorted(set(GOLD_VIEWS) - existing)
        if missing:
            pytest.skip(f"gold views missing: {missing} (uv run alembic upgrade head)")
        for name, columns in GOLD_VIEWS.items():
            reflected = [
                column["name"] for column in inspector.get_columns(name, schema="gold")
            ]
            assert reflected == columns, name

        summary = {
            column["name"]: column["type"]
            for column in inspector.get_columns("election_summary", schema="gold")
        }
        assert str(summary["census"]) == "BIGINT"
        assert isinstance(summary["turnout_pct"], Numeric)
        flat = {
            column["name"]: column["type"]
            for column in inspector.get_columns("poll_flat", schema="gold")
        }
        assert str(flat["revision_id"]) == "BIGINT"
        assert isinstance(flat["pct"], Numeric)
    finally:
        engine.dispose()


# --- Curated party colours from the catalogue (R18-R21) ---------------------

POLL_LABELS = {
    "PP": "pp",
    "PSOE": "psoe",
    "Vox": "vox",
    "Sumar": "sumar",
    "ERC": "erc",
    "Junts": "jxcat-junts",
    "EH Bildu": "eh-bildu",
    "PNV": "eaj-pnv",
    "BNG": "bng",
    "CCa": "cca",
    "UPN": "u-p-n",
    "Adelante Andalucía (2021)": "adelante-andalucia",
    "Podemos": "podemos",
    "SALF": "salf",
    "Aliança.cat": "alianca-cat",
}

COLOUR_CATALOG = """
[parties.pp]
name = "PP"
color = "#1d84ce"

[parties.psoe]
name = "PSOE"
"""


def _catalog(tmp_path: Path, text: str):
    path = tmp_path / "party_catalog.toml"
    path.write_text(text, encoding="utf-8")
    return load_catalog(path)


def test_catalog_parses_color(tmp_path: Path):  # R18
    catalog = _catalog(tmp_path, COLOUR_CATALOG)
    pp = catalog.lookup("PP")
    assert pp is not None
    assert pp.color == "#1d84ce"
    psoe = catalog.lookup("PSOE")
    assert psoe is not None
    assert psoe.color is None


@pytest.mark.parametrize(
    "color",
    ['"#12345"', '"red"', '"#12345g"', '"1d84ce"', '"#1234567"', "12", "[]"],
)
def test_catalog_rejects_invalid_color(tmp_path: Path, color: str):  # R19
    text = f'[parties.pp]\nname = "PP"\ncolor = {color}\n'
    with pytest.raises(IngestError) as error:
        _catalog(tmp_path, text)
    assert "'pp'" in str(error.value)
    assert "party_catalog.toml" in str(error.value)


def test_resolver_applies_color(tmp_path: Path):  # R20
    catalog = _catalog(tmp_path, COLOUR_CATALOG)
    existing = Party(id=1, name="PP", slug="pp", color="#000000")
    untouched = Party(id=2, name="PSOE", slug="psoe", color="#123456")
    resolver = PartyResolver((existing, untouched), catalog)

    assert resolver.resolve("P.P.").color == "#1d84ce"
    assert resolver.resolve("PSOE").color == "#123456"

    created = PartyResolver((), catalog).resolve("PP")
    assert created.color == "#1d84ce"


def test_catalog_poll_labels_have_colors():  # R21
    catalog = load_catalog()
    pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    for label, slug in POLL_LABELS.items():
        entry = catalog.lookup(label)
        assert entry is not None, label
        assert entry.slug == slug, label
        assert entry.color is not None, label
        assert pattern.fullmatch(entry.color), (label, entry.color)


def test_live_poll_brands_colored():  # R22
    engine = _real_engine()
    try:
        inspector = inspect(engine)
        if not inspector.has_table("party", schema="silver") or not inspector.has_table(
            "poll_result", schema="silver"
        ):
            pytest.skip(
                "silver party/poll_result missing (uv run alembic upgrade head)"
            )
        catalog = load_catalog()
        expected: dict[str, str | None] = {}
        for label in POLL_LABELS:
            entry = catalog.lookup(label)
            assert entry is not None, label
            expected[entry.slug] = entry.color
        with engine.connect() as connection:
            if not connection.scalar(text("SELECT count(*) FROM silver.poll_result")):
                pytest.skip("no polls loaded (uv run ingestor ingest-polls)")
            rows = connection.execute(
                text(
                    "SELECT DISTINCT p.slug, p.color FROM silver.party p "
                    "JOIN silver.poll_result pr ON pr.party_id = p.id"
                )
            ).all()
        actual = {slug: color for slug, color in rows}
        # Every brand with poll results is a catalogue ficha with its curated colour.
        assert actual
        for slug, color in actual.items():
            entry = catalog.lookup(slug)
            assert entry is not None, slug
            assert color == entry.color, slug
        # The fifteen poll labels are the ones the source publishes.
        assert set(expected) <= set(actual)
    finally:
        engine.dispose()


# --- ERD: the Gold page of docs/db/schema.drawio (R15) ----------------------

DRAWIO = REPO_ROOT / "docs" / "db" / "schema.drawio"


def _drawio_pages() -> dict[str, ET.Element]:
    root = ET.parse(DRAWIO).getroot()
    return {diagram.get("name"): diagram for diagram in root.findall("diagram")}


def _drawio_cells(page: ET.Element) -> list[ET.Element]:
    return page.findall(".//mxCell")


def _is_table(cell: ET.Element) -> bool:
    return "shape=table;" in (cell.get("style") or "")


def _descendants(cells: list[ET.Element], cell_id: str) -> list[ET.Element]:
    by_parent: dict[str, list[ET.Element]] = {}
    for cell in cells:
        by_parent.setdefault(cell.get("parent"), []).append(cell)
    out: list[ET.Element] = []
    stack = list(by_parent.get(cell_id, []))
    while stack:
        cell = stack.pop()
        out.append(cell)
        stack.extend(by_parent.get(cell.get("id"), []))
    return out


def test_drawio_gold_page():  # R15
    pages = _drawio_pages()
    assert set(pages) == {
        "Bronze",
        "Silver",
        "Bronze polls",
        "Silver polls",
        "Gold",
    }
    assert len(pages) == 5
    cells = _drawio_cells(pages["Gold"])

    titles = [
        cell.get("value") or ""
        for cell in cells
        if "text;" in (cell.get("style") or "")
    ]
    assert any("gold" in title.lower() for title in titles)

    for name, columns in GOLD_VIEWS.items():
        containers = [
            cell for cell in cells if _is_table(cell) and cell.get("value") == name
        ]
        assert len(containers) == 1, name
        properties = {
            (cell.get("value") or "").split()[0]
            for cell in _descendants(cells, containers[0].get("id"))
            if cell.get("value")
        }
        assert set(columns) <= properties, f"missing columns in {name}"

    # Views have no PK/FK: no constraint marker anywhere on the page.
    keys = [
        cell.get("value") or ""
        for cell in cells
        if "partialRectangle" in (cell.get("style") or "")
    ]
    assert not any(value.startswith(("PK", "FK")) for value in keys)


# --- Contract and environment documents (R13, R14, R16, R17) -----------------


def _doc(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_docs_gold_contract():  # R13
    text = _doc("docs", "db", "gold.md")
    for view in GOLD_VIEWS:
        assert f"`{view}`" in text, view
    for screen in (
        "Resultados — portada",
        "Resultados — nacional",
        "Resultados — mapa de CCAA",
        "Resultados — provincia",
        "Resultados — municipio",
        "Resultados — mesas del municipio",
        "Resultados — detalle de mesa",
        "Sondeos — tendencia",
        "Sondeos — tabla",
    ):
        assert screen in text, screen
    for token in (
        "Pantalla",
        "Vista(s)",
        "Filtro / orden",
        "level",
        "party_color",
        "turnout_pct",
        "no agrega",
        "solo lectura",
        "silver",
        "alembic upgrade head",
    ):
        assert token in text, token


def test_docs_environment_topology():  # R14
    text = _doc(".agents", "environment.md")
    for token in (
        "Topología de entornos",
        "sin staging",
        "docker-compose",
        "Vercel",
        "Neon",
        "GitHub Actions",
        "solo lectura",
        "DATABASE_URL",
        "alembic upgrade head",
    ):
        assert token in text, token


def test_docs_data_model_gold():  # R16
    text = _doc(".agents", "data-model.md")
    assert "una página por esquema y dominio" in text
    assert "(Bronze, Silver, Bronze polls, Silver polls, Gold)" in text
    assert "(vistas para el frontend, aún vacío)" not in text
    v2 = text.split("## Modelo v2 (vigente)")[1].split("## Fuera del MVP")[0]
    for view in GOLD_VIEWS:
        assert f"`gold.{view}`" in v2, view
    assert "`silver.party.color`" in v2 or "party.color" in v2
    assert "party_catalog.toml" in v2
    assert "resolver" in v2


def test_docs_ingesta_and_agents_gold():  # R17
    ingesta = _doc("docs", "ingestor", "ingesta.md")
    for token in (
        "## Esquema `gold`",
        "view_ddl",
        "alembic upgrade head",
        "election_summary",
        "result_by_area",
        "result_by_station",
        "station_turnout",
        "poll_flat",
        "poll_trend",
    ):
        assert token in ingesta, token

    agents = _doc("ingestor", "AGENTS.md")
    assert "gold.py" in agents
    assert "view_ddl" in agents
    assert "include_object" in agents
    assert "gold.election_summary" in agents
    assert "- Vistas `gold`." not in agents

    architecture = _doc(".agents", "architecture.md")
    assert "esquema `gold`" in architecture
    assert "docs/db/gold.md" in architecture

    web = _doc("web", "AGENTS.md")
    assert "docs/db/gold.md" in web
