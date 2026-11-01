"""Silver polls model: metadata checks (no database, no network)."""

import xml.etree.ElementTree as ET
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from ingestor.models import Base

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAWIO = REPO_ROOT / "docs" / "db" / "schema.drawio"
DATA_MODEL = REPO_ROOT / ".agents" / "data-model.md"

pollster = Base.metadata.tables["silver.pollster"]
poll = Base.metadata.tables["silver.poll"]
poll_result = Base.metadata.tables["silver.poll_result"]


def _unique(table, columns: list[str]) -> bool:
    return any(
        isinstance(constraint, UniqueConstraint)
        and [column.name for column in constraint.columns] == columns
        for constraint in table.constraints
    )


def _check(table, name: str) -> str:
    constraint = next(
        c
        for c in table.constraints
        if isinstance(c, CheckConstraint) and c.name == name
    )
    return str(constraint.sqltext).lower()


def _fk_target(column) -> str:
    return next(iter(column.foreign_keys)).target_fullname


def test_pollster_pk_name_and_unique_slug():  # R1
    assert [c.name for c in pollster.primary_key.columns] == ["id"]
    assert isinstance(pollster.c.name.type, Text)
    assert not pollster.c.name.nullable
    assert isinstance(pollster.c.slug.type, String)
    assert pollster.c.slug.type.length == 60
    assert _unique(pollster, ["slug"])


def test_poll_pk_and_required_pollster_fk():  # R2
    assert [c.name for c in poll.primary_key.columns] == ["id"]
    assert not poll.c.pollster_id.nullable
    assert _fk_target(poll.c.pollster_id) == "silver.pollster.id"


def test_poll_source_election_type_and_revision():  # R3
    assert isinstance(poll.c.source.type, Text)
    assert not poll.c.source.nullable
    assert isinstance(poll.c.election_type.type, String)
    assert poll.c.election_type.type.length == 20
    assert not poll.c.election_type.nullable
    assert isinstance(poll.c.revision_id.type, BigInteger)
    assert not poll.c.revision_id.nullable


def test_poll_election_fk_is_nullable():  # R4
    assert poll.c.election_id.nullable
    assert _fk_target(poll.c.election_id) == "silver.election.id"


def test_poll_fieldwork_and_sample_are_nullable():  # R5
    assert isinstance(poll.c.fieldwork_start.type, Date)
    assert poll.c.fieldwork_start.nullable
    assert isinstance(poll.c.fieldwork_end.type, Date)
    assert poll.c.fieldwork_end.nullable
    assert isinstance(poll.c.sample_size.type, Integer)
    assert poll.c.sample_size.nullable


def test_poll_turnout_is_numeric_with_range_check():  # R6
    turnout = poll.c.turnout
    assert isinstance(turnout.type, Numeric)
    assert (turnout.type.precision, turnout.type.scale) == (5, 2)
    assert turnout.nullable
    sqltext = _check(poll, "poll_turnout_range")
    assert "turnout >= 0" in sqltext
    assert "turnout <= 100" in sqltext


def test_poll_result_fks_are_indexed():  # R7
    assert [c.name for c in poll_result.primary_key.columns] == ["id"]
    assert _fk_target(poll_result.c.poll_id) == "silver.poll.id"
    assert poll_result.c.poll_id.index
    assert _fk_target(poll_result.c.party_id) == "silver.party.id"
    assert poll_result.c.party_id.index


def test_poll_result_pct_is_numeric_with_range_check():  # R8
    pct = poll_result.c.pct
    assert isinstance(pct.type, Numeric)
    assert (pct.type.precision, pct.type.scale) == (5, 2)
    assert pct.nullable
    sqltext = _check(poll_result, "poll_result_pct_range")
    assert "pct >= 0" in sqltext
    assert "pct <= 100" in sqltext


def test_poll_result_seats_are_nullable_ints():  # R9
    assert isinstance(poll_result.c.seats_min.type, Integer)
    assert poll_result.c.seats_min.nullable
    assert isinstance(poll_result.c.seats_max.type, Integer)
    assert poll_result.c.seats_max.nullable


def test_poll_result_unique_poll_and_party():  # R10
    assert _unique(poll_result, ["poll_id", "party_id"])


# --- Documentation sync: ERD (docs/db/schema.drawio) and data-model.md ---


def _pages() -> dict[str, ET.Element]:
    root = ET.parse(DRAWIO).getroot()
    return {diagram.get("name"): diagram for diagram in root.findall("diagram")}


def _cells(page: ET.Element) -> list[ET.Element]:
    return page.findall(".//mxCell")


def _is_table(cell: ET.Element) -> bool:
    return "shape=table;" in (cell.get("style") or "")


def _is_dimmed(cell: ET.Element) -> bool:
    style = cell.get("style") or ""
    return "opacity=" in style or "#f5f5f5" in style


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


def test_drawio_has_a_page_per_schema_and_domain():  # R13, R14
    assert {"Bronze", "Silver", "Bronze polls", "Silver polls", "Gold"} <= set(_pages())


def test_silver_polls_page_has_complete_tables():  # R13
    cells = _cells(_pages()["Silver polls"])
    expected = {
        "pollster": ["id", "name", "slug"],
        "poll": [
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
        "poll_result": ["id", "poll_id", "party_id", "pct", "seats_min", "seats_max"],
    }
    for table, columns in expected.items():
        containers = [c for c in cells if _is_table(c) and c.get("value") == table]
        assert containers, f"missing table {table}"
        properties = {
            (c.get("value") or "").split()[0]
            for c in _descendants(cells, containers[0].get("id"))
            if c.get("value")
        }
        assert set(columns) <= properties, f"missing columns in {table}"


def test_silver_polls_page_dimms_party_and_election():  # R13
    cells = _cells(_pages()["Silver polls"])
    for name in ("party", "election"):
        boxes = [c for c in cells if _is_table(c) and c.get("value") == name]
        assert boxes, f"missing reference box {name}"
        assert all(_is_dimmed(c) for c in boxes), f"{name} is not dimmed"


def test_bronze_polls_page_shows_snapshot_flow():  # R14
    cells = _cells(_pages()["Bronze polls"])
    snapshots = [c for c in cells if "data/raw/polls/" in (c.get("value") or "")]
    assert snapshots, "missing snapshot file node"
    ingestions = [c for c in cells if "ingestion" in (c.get("value") or "")]
    assert ingestions, "missing ingestion reference box"
    assert all(_is_dimmed(c) for c in ingestions), "ingestion is not dimmed"
    # The flow arrow is a shape, not an edge: the skill validator only allows
    # entityRelationEdgeStyle edges between table row anchors.
    arrows = [c for c in cells if "shape=step" in (c.get("style") or "")]
    assert arrows, "missing flow arrow from snapshot to ingestion"


def test_data_model_documents_page_per_schema_and_domain():  # R15
    text = DATA_MODEL.read_text(encoding="utf-8")
    assert "una página por esquema y dominio" in text
    assert "(Bronze, Silver, Bronze polls, Silver polls, Gold)" in text


def test_data_model_v2_describes_polls_tables():  # R15
    text = DATA_MODEL.read_text(encoding="utf-8")
    v2 = text.split("## Modelo v2 (vigente)")[1].split("## Fuera del MVP")[0]
    for table in ("pollster", "poll", "poll_result"):
        assert f"`silver.{table}`" in v2
