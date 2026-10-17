"""``polls/adapters/wikipedia_polls.py``: Wikipedia polls source rules (no network).

Real cuts of revision 1380713440 (captured 2026-10-17 with ``fetch-polls``) plus
synthetic cases; robustness cases are inline strings (see
specs/008_polls_adapter/design.md).
"""

import ast
import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from ingestor.polls.adapters.wikipedia_polls import (
    ELECTION_TYPE,
    PARTY_COLUMNS,
    PollResultRow,
    parse_date,
    parse_polls,
    poll_tables,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wikipedia_polls"
REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "ingestor"
    / "polls"
    / "adapters"
    / "wikipedia_polls.py"
)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- Scope: year subsections of ``Voting intention estimates`` (R2, R25) ----


def test_poll_tables_scope():  # R2
    tables = poll_tables(_fixture("synthetic_out_of_scope.wikitext"))
    assert [year for year, _ in tables] == [2026]
    [(_, table)] = tables
    assert table.rows[1].cells[0].text == "Alpha/Medio"


def test_poll_tables_years():  # R2
    assert [year for year, _ in poll_tables(_fixture("real_2023_tail.wikitext"))] == [
        2023
    ]
    assert [year for year, _ in poll_tables(_fixture("synthetic_dates.wikitext"))] == [
        2026
    ]


def test_poll_tables_all_subsections_and_tables():  # R2
    wikitext = (
        "====Voting intention estimates====\n"
        "=====2026 (after FA)=====\n"
        '{| class="wikitable"\n|-\n| A\n|}\n'
        "=====2026 (before FA)=====\n"
        '{| class="wikitable"\n|-\n| B\n|}\n'
        '{| class="wikitable"\n|-\n| C\n|}\n'
    )
    tables = poll_tables(wikitext)
    assert [year for year, _ in tables] == [2026, 2026, 2026]
    assert [table.rows[0].cells[0].text for _, table in tables] == ["A", "B", "C"]


def test_missing_section_warns_and_empty(caplog):  # R25
    wikitext = '== Other section ==\n{| class="wikitable"\n|-\n| A\n|}\n'
    with caplog.at_level(logging.WARNING):
        tables = poll_tables(wikitext)
    assert tables == []
    assert "section not found" in caplog.text


# --- Column plan: labels, never positions (R3-R9, R26) ----------------------

PARTY_LABELS = {
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


def test_party_columns_mapping():  # R6, R7
    assert {
        label: column.slug for label, column in PARTY_COLUMNS.items()
    } == PARTY_LABELS
    assert len({column.slug for column in PARTY_COLUMNS.values()}) == 15
    assert PARTY_COLUMNS["SALF"].name == "Se Acabó La Fiesta"
    assert PARTY_COLUMNS["Aliança.cat"].name == "Aliança Catalana"


def test_synthetic_columns_mapping():  # R5, R6, R7
    (row,) = parse_polls(_fixture("synthetic_columns.wikitext"))
    assert list(row.results) == [
        "vox",
        "pp",
        "salf",
        "alianca-cat",
        "adelante-andalucia",
        "FA",
    ]
    assert row.results["pp"].pct == Decimal("33.0")
    assert row.results["vox"].pct == Decimal("18.0")
    assert row.results["salf"].pct == Decimal("4.0")
    assert row.results["alianca-cat"].pct == Decimal("2.0")
    assert row.results["adelante-andalucia"].pct == Decimal("1.0")


def test_fixed_columns_by_label():  # R4
    (row,) = parse_polls(_fixture("synthetic_columns.wikitext"))
    assert row.source == "Alpha/Medio"
    assert row.sample_size == 1000
    assert row.turnout == Decimal("67.6")


def test_unknown_column_warns_and_kept(caplog):  # R8
    with caplog.at_level(logging.WARNING):
        (row,) = parse_polls(_fixture("synthetic_columns.wikitext"))
    assert "unknown party column" in caplog.text
    assert "FA" in caplog.text
    assert row.results["FA"].pct == Decimal("5.0")


def test_lead_column_ignored_without_warning(caplog):  # R9
    with caplog.at_level(logging.WARNING):
        (row,) = parse_polls(_fixture("synthetic_columns.wikitext"))
        parse_polls(_fixture("real_2026_head.wikitext"))
    assert "Lead" not in caplog.text
    assert Decimal("15.0") not in {result.pct for result in row.results.values()}


def test_color_header_row_ignored(caplog):  # R3
    with caplog.at_level(logging.WARNING):
        rows = parse_polls(_fixture("real_2026_head.wikitext"))
    assert "unknown party column" not in caplog.text
    assert rows[0].source == "SocioMétrica/El Español"


def test_election_type():  # R26
    assert ELECTION_TYPE == "congress"


# --- Data rows and results (R1, R10-R14, R20) -------------------------------


def test_party_cells():  # R12, R13, R14
    first, second = parse_polls(_fixture("synthetic_cells.wikitext"))
    assert list(first.results) == ["pp", "psoe", "erc"]
    assert first.results["pp"] == PollResultRow(Decimal("32.6"), 135, 137)
    assert first.results["psoe"] == PollResultRow(None, 0, 0)
    assert first.results["erc"] == PollResultRow(Decimal("2.9"), None, None)
    assert list(second.results) == ["pp", "psoe"]
    assert second.results["pp"] == PollResultRow(Decimal("22.2"), None, None)
    assert second.results["psoe"] == PollResultRow(None, 7, 7)


def test_real_head_first_rows():  # R1, R2, R5, R12, R13, R14, R18, R19, R20
    rows = parse_polls(_fixture("real_2026_head.wikitext"))
    assert len(rows) == 14
    socio, target = rows[0], rows[1]
    assert socio.source == "SocioMétrica/El Español"
    assert (socio.fieldwork_start, socio.fieldwork_end) == (
        date(2026, 10, 10),
        date(2026, 10, 11),
    )
    assert socio.sample_size == 1000
    assert socio.turnout is None
    assert socio.results["pp"] == PollResultRow(Decimal("32.6"), 141, 141)
    assert socio.results["sumar"] == PollResultRow(Decimal("5.8"), 8, 8)
    assert "alianca-cat" not in socio.results
    assert target.source == "Target Point/El Debate"
    assert (target.fieldwork_start, target.fieldwork_end) == (
        date(2026, 10, 6),
        date(2026, 10, 9),
    )
    assert target.sample_size == 1002
    assert target.turnout == Decimal("67.6")
    assert target.results["pp"] == PollResultRow(Decimal("32.0"), 135, 137)
    assert target.results["psoe"] == PollResultRow(Decimal("25.9"), 103, 105)
    assert target.results["erc"] == PollResultRow(None, 8, 10)
    dym = next(row for row in rows if row.source.startswith("DYM"))
    assert dym.sample_size == 1011
    assert dym.turnout is None
    assert dym.results["pp"] == PollResultRow(Decimal("34.0"), 139, 143)
    assert dym.results["sumar"] == PollResultRow(Decimal("3.6"), 3, 5)


def test_real_2023_tail_skips(caplog):  # R10, R11
    with caplog.at_level(logging.WARNING):
        (row,) = parse_polls(_fixture("real_2023_tail.wikitext"))
    assert row.source == "EM-Analytics/Electomanía"
    assert row.sample_size == 1517
    assert row.turnout is None
    assert row.results["pp"] == PollResultRow(Decimal("31.8"), 129, 129)
    assert not caplog.records


# --- Dates (R15-R17, R22) ---------------------------------------------------


def test_parse_date_matrix(caplog):  # R15, R16, R17, R22
    assert parse_date("5 Oct", 2026) == (date(2026, 10, 5), date(2026, 10, 5))
    assert parse_date("10–11 Oct", 2026) == (date(2026, 10, 10), date(2026, 10, 11))
    assert parse_date("29 Sep–1 Oct", 2026) == (date(2026, 9, 29), date(2026, 10, 1))
    assert parse_date("29 Dec–5 Jan", 2026) == (date(2025, 12, 29), date(2026, 1, 5))
    assert parse_date("31 Dec–3 Jan", 2026) == (date(2025, 12, 31), date(2026, 1, 3))
    assert parse_date("?", 2026) == (None, None)
    with caplog.at_level(logging.WARNING):
        assert parse_date("garbage", 2026) == (None, None)
    assert "unparseable date" in caplog.text


def test_synthetic_dates():  # R15, R16, R17, R18, R19
    crossing, single, unknown = parse_polls(_fixture("synthetic_dates.wikitext"))
    assert (crossing.fieldwork_start, crossing.fieldwork_end) == (
        date(2025, 12, 29),
        date(2026, 1, 5),
    )
    assert crossing.sample_size == 1000
    assert crossing.turnout is None
    assert (single.fieldwork_start, single.fieldwork_end) == (
        date(2026, 10, 5),
        date(2026, 10, 5),
    )
    assert single.sample_size is None
    assert single.turnout == Decimal("67.6")
    assert (unknown.fieldwork_start, unknown.fieldwork_end) == (None, None)
    assert unknown.sample_size == 800
    assert unknown.turnout == Decimal(66)


# --- Numbers: sample and turnout (R18, R19) ---------------------------------


def test_sample_and_turnout():  # R18, R19
    crossing, single, unknown = parse_polls(_fixture("synthetic_dates.wikitext"))
    assert [row.sample_size for row in (crossing, single, unknown)] == [1000, None, 800]
    assert [row.turnout for row in (crossing, single, unknown)] == [
        None,
        Decimal("67.6"),
        Decimal(66),
    ]


# --- Firm and CIS re-estimates (R20, R21) -----------------------------------

POLLSTER_TABLE = (
    "====Voting intention estimates====\n"
    "=====2026=====\n"
    '{| class="wikitable"\n'
    "|-\n"
    "! Polling firm/Commissioner\n"
    "! Fieldwork date\n"
    "! Sample size\n"
    "! Turnout\n"
    "! PP\n"
    "|-\n"
    "| SocioMétrica/El Español\n"
    "| 5 Oct\n"
    "| 1,000\n"
    "|?\n"
    "| 30.0\n"
    "|-\n"
    "| CIS (Target Point)\n"
    "| 6 Oct\n"
    "| 1,000\n"
    "|?\n"
    "| 31.0\n"
    "|-\n"
    "| More in Common\n"
    "| 7 Oct\n"
    "| 1,000\n"
    "|?\n"
    "| 32.0\n"
    "|}\n"
)


def test_pollster_name_extraction():  # R21
    rows = parse_polls(POLLSTER_TABLE)
    assert [row.source for row in rows] == [
        "SocioMétrica/El Español",
        "CIS (Target Point)",
        "More in Common",
    ]
    assert [row.pollster_name for row in rows] == [
        "SocioMétrica",
        "CIS",
        "More in Common",
    ]


# --- Robustness: drift degrades to a warning (R22-R24) ----------------------

GARBAGE_TABLE = (
    "====Voting intention estimates====\n"
    "=====2026=====\n"
    '{| class="wikitable"\n'
    "|-\n"
    "! Polling firm/Commissioner\n"
    "! Fieldwork date\n"
    "! Sample size\n"
    "! Turnout\n"
    "! PP\n"
    "|-\n"
    "| Alpha/Medio\n"
    "| ??\n"
    "| 1.000\n"
    "| abc\n"
    "| abc\n"
    "|}\n"
)

MISMATCH_TABLE = (
    "====Voting intention estimates====\n"
    "=====2026=====\n"
    '{| class="wikitable"\n'
    "|-\n"
    "! Polling firm/Commissioner\n"
    "! Fieldwork date\n"
    "! Sample size\n"
    "! Turnout\n"
    "! PP\n"
    "! PSOE\n"
    "|-\n"
    "| Alpha/Medio\n"
    "| 5 Oct\n"
    "| 1,000\n"
    "| 67.6\n"
    "| 30.0\n"
    "| 28.0\n"
    "|-\n"
    "| Beta/Medio\n"
    "| 6 Oct\n"
    "| 800\n"
    "|}\n"
)

NO_LABELS_TABLE = (
    "====Voting intention estimates====\n"
    "=====2026=====\n"
    '{| class="wikitable"\n'
    "|-\n"
    "! Party\n"
    "! Votes\n"
    "|-\n"
    "| PP\n"
    "| 30\n"
    "|}\n"
)


def test_garbage_cells_warn_and_null(caplog):  # R22
    with caplog.at_level(logging.WARNING):
        (row,) = parse_polls(GARBAGE_TABLE)
    for warning in (
        "unparseable date",
        "unparseable sample size",
        "unparseable turnout",
        "unparseable pct",
    ):
        assert warning in caplog.text
    assert (row.fieldwork_start, row.fieldwork_end) == (None, None)
    assert row.sample_size is None
    assert row.turnout is None
    assert row.results == {}


def test_row_mismatch_warns_and_skips(caplog):  # R23
    with caplog.at_level(logging.WARNING):
        rows = parse_polls(MISMATCH_TABLE)
    assert [row.source for row in rows] == ["Alpha/Medio"]
    assert "column count mismatch" in caplog.text


def test_table_without_fixed_labels_warns_and_skips(caplog):  # R24
    with caplog.at_level(logging.WARNING):
        rows = parse_polls(NO_LABELS_TABLE)
    assert rows == []
    assert "not a polls table" in caplog.text


# --- Contract, purity, fixtures and docs (R26-R29) --------------------------


def test_fixtures_present():  # R28
    for name in (
        "real_2026_head.wikitext",
        "real_2023_tail.wikitext",
        "synthetic_dates.wikitext",
        "synthetic_cells.wikitext",
        "synthetic_columns.wikitext",
        "synthetic_out_of_scope.wikitext",
    ):
        assert (FIXTURES / name).is_file()


def test_module_is_stdlib_only_and_pure():  # R27
    source = MODULE_PATH.read_text(encoding="utf-8")
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    assert {module.split(".")[0] for module in modules} <= sys.stdlib_module_names | {
        "ingestor"
    }
    assert {module for module in modules if module.startswith("ingestor")} == {
        "ingestor.polls.parsers.wikitext"
    }
    for banned in (
        "urlopen",
        "socket",
        "requests",
        "httpx",
        "open(",
        "sqlalchemy",
        "SessionLocal",
    ):
        assert banned not in source


def test_docs_ingestor_agents():  # R29
    text = (REPO_ROOT / "ingestor" / "AGENTS.md").read_text(encoding="utf-8")
    assert "wikipedia_polls.py" in text
    assert "sondeos" in text


def test_real_cis_block():  # R16, R20
    rows = parse_polls(_fixture("real_2026_head.wikitext"))
    opina, ateneo, cis = rows[-3:]
    assert [row.source for row in rows[-3:]] == [
        "CIS (Opina 360)",
        "CIS (Ateneo del Dato)",
        "CIS",
    ]
    for row in (opina, ateneo, cis):
        assert (row.fieldwork_start, row.fieldwork_end) == (
            date(2026, 10, 1),
            date(2026, 10, 6),
        )
        assert row.sample_size == 5025
    assert opina.results["pp"] == PollResultRow(Decimal("28.0"), 119, 119)
    assert opina.results["psoe"] == PollResultRow(Decimal("28.0"), 118, 118)
    assert cis.results["psoe"] == PollResultRow(Decimal("34.0"), None, None)
    assert [row.pollster_name for row in (opina, ateneo, cis)] == ["CIS", "CIS", "CIS"]
