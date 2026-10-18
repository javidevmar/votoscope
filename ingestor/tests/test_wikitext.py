"""``polls/parsers/wikitext.py``: generic wikitext table lexer (no network).

Synthetic wikitext strings only: one construction per test, plus a realistic
combined cell at the end (see specs/007_polls_lexer/design.md).
"""

import ast
import logging
import sys
from pathlib import Path

from ingestor.polls.parsers.wikitext import Cell, clean, parse_tables

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "ingestor"
    / "polls"
    / "parsers"
    / "wikitext.py"
)
REPO_ROOT = Path(__file__).resolve().parents[2]

# --- Synthetic wikitext samples (one construction each) ---------------------

TWO_TABLES = (
    "== Voting intention estimates ==\n"
    "Intro paragraph outside any table.\n"
    '{| class="wikitable"\n'
    "|-\n"
    "| A\n"
    "|}\n"
    "Text between the two tables.\n"
    '{| class="wikitable"\n'
    "|-\n"
    "| B\n"
    "| C\n"
    "|}\n"
    "Trailing text outside any table.\n"
)

TABLE_ATTRS = (
    '{| class="wikitable sortable" style="text-align:center;font-size:90%"\n'
    "|-\n"
    "| A\n"
    "|}\n"
)

CLOSING_LINE = '{| class="wikitable"\n|-\n| A\n|}\n| outside the table\n'

ROW_MARKERS = (
    '{| class="wikitable"\n| Before any marker\n|-\n| Second\n|-\n| Third\n|}\n'
)

CELL_MARKERS = (
    '{| class="wikitable"\n! Header one\n! Header two\n|-\n| Data one\n| Data two\n|}\n'
)

ROW_ATTRS = '{| class="wikitable"\n|- style="height:42px;"\n| A\n|}\n'

SPLIT_ROWSPAN = '{| class="wikitable"\n|-\n| rowspan="3" | 1–4 Sep\n|}\n'
SPLIT_STYLE = '{| class="wikitable"\n|-\n| style="background:#d0f0c0" | 8.5\n|}\n'
SPLIT_TEMPLATE = '{| class="wikitable"\n|-\n| {{Party shading/PP}} | 31.9\n|}\n'
SPLIT_LINK = (
    '{| class="wikitable"\n'
    "|-\n"
    "| [[File:People's Party (Spain) logo.svg|link=People's Party (Spain)|PP]]\n"
    "|}\n"
)
SPLIT_QUESTION = '{| class="wikitable"\n|-\n| ?\n|}\n'

ROWSPAN_DATA = (
    '{| class="wikitable"\n'
    "|-\n"
    '| rowspan="2" | 30 Sep–2 Oct\n'
    '| rowspan="2" | 1,000\n'
    "| 31.9\n"
    "|-\n"
    "| 27.5\n"
    "|}\n"
)

ROWSPAN_HEADER = (
    '{| class="wikitable"\n'
    "|-\n"
    '! rowspan="2" | Polling firm/Commissioner\n'
    '! rowspan="2" | Fieldwork date\n'
    "! PP\n"
    "! PSOE\n"
    "! Others\n"
    '! rowspan="2" | Lead\n'
    "|-\n"
    "! {{party color|People's Party (Spain)}} | PP\n"
    "! {{party color|Spanish Socialist Workers' Party}} | PSOE\n"
    "|}\n"
)

ROWSPAN_THREE = (
    '{| class="wikitable"\n'
    "|-\n"
    '| rowspan="3" | CIS\n'
    "| 1,000\n"
    "| 31.9\n"
    "|-\n"
    "| 27.5\n"
    "|-\n"
    "| 26.1\n"
    "|}\n"
)

ROWSPAN_ONE = '{| class="wikitable"\n|-\n| rowspan="1" | A\n| B\n|-\n| C\n|}\n'

EFN_ONLY_CELL = (
    '{| class="wikitable"\n|-\n| {{efn|Includes separate figures for Compromís}}\n|}\n'
)

PARTY_CELL = (
    '{| class="wikitable"\n'
    "|-\n"
    "| {{Party shading/PP}} | '''31.9'''<br/>"
    '{{font|size=75%|font=Verdana|text=139}}<ref name="a"/>\n'
    "|}\n"
)

UNTERMINATED = '{| class="wikitable"\n|-\n| A\n| B\n'


def _only_cell(wikitext: str) -> Cell:
    """The single cell of a single-row, single-cell table."""
    (table,) = parse_tables(wikitext)
    (row,) = table.rows
    (cell,) = row.cells
    return cell


def _texts(table) -> list[list[str]]:
    return [[cell.text for cell in row.cells] for row in table.rows]


def test_parse_tables_one_per_block():  # R1, R19
    tables = parse_tables(TWO_TABLES)
    assert len(tables) == 2
    assert _texts(tables[0]) == [["A"]]
    assert _texts(tables[1]) == [["B", "C"]]


def test_text_outside_blocks_ignored():  # R19
    assert parse_tables("== Voting intention estimates ==\nJust prose.\n") == []


def test_table_attrs_from_opening_line():  # R2
    (table,) = parse_tables(TABLE_ATTRS)
    assert table.attrs == {
        "class": "wikitable sortable",
        "style": "text-align:center;font-size:90%",
    }


def test_closing_line_not_in_rows():  # R3
    (table,) = parse_tables(CLOSING_LINE)
    assert _texts(table) == [["A"]]


def test_rows_split_on_row_marker():  # R4
    (table,) = parse_tables(ROW_MARKERS)
    assert _texts(table) == [["Before any marker"], ["Second"], ["Third"]]


def test_cell_markers():  # R5
    header_row, data_row = parse_tables(CELL_MARKERS)[0].rows
    assert [cell.header for cell in header_row.cells] == [True, True]
    assert [cell.header for cell in data_row.cells] == [False, False]
    assert [cell.text for cell in header_row.cells] == ["Header one", "Header two"]
    assert [cell.text for cell in data_row.cells] == ["Data one", "Data two"]


def test_cell_attr_value_split():  # R6
    assert _only_cell(SPLIT_ROWSPAN).attrs == {"rowspan": "3"}
    assert _only_cell(SPLIT_ROWSPAN).text == "1–4 Sep"
    assert _only_cell(SPLIT_STYLE).attrs == {"style": "background:#d0f0c0"}
    assert _only_cell(SPLIT_STYLE).text == "8.5"
    assert _only_cell(SPLIT_TEMPLATE).attrs == {}
    assert _only_cell(SPLIT_TEMPLATE).text == "31.9"
    assert _only_cell(SPLIT_LINK).attrs == {}
    assert _only_cell(SPLIT_LINK).text == (
        "[[File:People's Party (Spain) logo.svg|link=People's Party (Spain)|PP]]"
    )
    assert _only_cell(SPLIT_QUESTION).attrs == {}
    assert _only_cell(SPLIT_QUESTION).text == "?"


def test_row_attrs_dict():  # R7
    (row,) = parse_tables(ROW_ATTRS)[0].rows
    assert row.attrs == {"style": "height:42px;"}


def test_rowspan_data_rows():  # R8
    first, second = parse_tables(ROWSPAN_DATA)[0].rows
    assert [cell.text for cell in first.cells] == ["30 Sep–2 Oct", "1,000", "31.9"]
    assert [cell.text for cell in second.cells] == ["30 Sep–2 Oct", "1,000", "27.5"]
    assert second.cells[0] == first.cells[0]


def test_rowspan_header_rows():  # R8
    first, second = parse_tables(ROWSPAN_HEADER)[0].rows
    assert [cell.text for cell in first.cells] == [
        "Polling firm/Commissioner",
        "Fieldwork date",
        "PP",
        "PSOE",
        "Others",
        "Lead",
    ]
    assert [cell.text for cell in second.cells] == [
        "Polling firm/Commissioner",
        "Fieldwork date",
        "PP",
        "PSOE",
        "",
        "Lead",
    ]
    assert second.cells[5] is first.cells[5]


def test_rowspan_three_rows():  # R8
    rows = parse_tables(ROWSPAN_THREE)[0].rows
    assert [cell.text for cell in rows[0].cells] == ["CIS", "1,000", "31.9"]
    assert [cell.text for cell in rows[1].cells] == ["CIS", "27.5"]
    assert [cell.text for cell in rows[2].cells] == ["CIS", "26.1"]


def test_rowspan_one_is_noop():  # R8
    rows = parse_tables(ROWSPAN_ONE)[0].rows
    assert [cell.text for cell in rows[0].cells] == ["A", "B"]
    assert [cell.text for cell in rows[1].cells] == ["C"]


def test_refs_removed():  # R9
    assert clean("A<ref>nota</ref>C") == "AC"
    assert clean('A<ref name="a">nota con {{cite web|url=x}}</ref>C') == "AC"
    assert clean('A<ref name="a"/>C') == "AC"


def test_efn_removed():  # R10
    assert clean("A{{efn|nota}}C") == "AC"
    assert clean('A{{efn|name="n"|nota con [[enlace|texto]]}}C') == "AC"
    assert clean('A{{efn|name="n"}}C') == "AC"
    assert _only_cell(EFN_ONLY_CELL).text == ""


def test_bold_removed():  # R11
    assert clean("'''31.9'''") == "31.9"


def test_smaller_unwrapped():  # R12
    assert clean("CIS {{smaller|(Target Point)}}") == "CIS (Target Point)"


def test_font_unwrapped():  # R13
    assert clean("{{font|size=75%|font=Verdana|text=139}}") == "139"
    assert clean("{{font|size=75%|text=135/137}}") == "135/137"
    assert clean("{{font|size=75%|text=(152)}}") == "(152)"
    assert clean("{{font|size=75%|text=?}}") == "?"
    assert clean("{{font|size=75%|text=}}") == ""


def test_br_variants_to_newline():  # R14
    assert clean("A<br>B") == "A\nB"
    assert clean("A<br/>B") == "A\nB"
    assert clean("A<br />B") == "A\nB"


def test_text_stripped():  # R15
    assert clean("  8.5  ") == "8.5"
    assert _only_cell('{| class="wikitable"\n|-\n| 8.5\n|}\n').text == "8.5"


def test_realistic_party_cell():  # R6, R9, R11, R13, R14
    cell = _only_cell(PARTY_CELL)
    assert cell.attrs == {}
    assert cell.text == "31.9\n139"


def test_unterminated_table_warns(caplog):  # R18
    with caplog.at_level(logging.WARNING):
        tables = parse_tables(UNTERMINATED)
    (table,) = tables
    assert _texts(table) == [["A", "B"]]
    assert "unterminated" in caplog.text


def test_module_is_stdlib_only():  # R16
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= sys.stdlib_module_names


def test_module_has_no_io():  # R17
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "urlopen" not in source
    assert "socket" not in source
    assert "requests" not in source
    assert "open(" not in source


def test_docs_ingestor_agents():  # R20
    text = (REPO_ROOT / "ingestor" / "AGENTS.md").read_text(encoding="utf-8")
    assert "wikitext.py" in text
    assert "lexer genérico" in text
