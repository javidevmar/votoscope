"""Wikipedia polls adapter: source rules for the opinion-polling page.

Consumes the generic wikitext lexer (``polls/parsers/wikitext.py``) and turns
the year tables of the ``Voting intention estimates`` section into ``PollRow``
records: firm, dates, sample, turnout and results per party. Source drift
degrades to a warning and a null value or a skipped row, never to an exception.

Party column labels resolve against the curated catalogue (``ingestor.parties``):
the key of a mapped column is its catalogue slug, the raw label otherwise.

Stdlib only (``re``, ``logging``, ``dataclasses``, ``datetime``, ``decimal``)
plus ``ingestor.parties``; no network or database access.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from ingestor.parties import Catalog, load_catalog
from ingestor.polls.parsers.wikitext import Cell, Row, Table, parse_tables

logger = logging.getLogger(__name__)

ELECTION_TYPE = "congress"
POLLS_SECTION = "Voting intention estimates"
FIXED_COLUMNS = (
    "Polling firm/Commissioner",
    "Fieldwork date",
    "Sample size",
    "Turnout",
)
FIRM_COLUMN, DATE_COLUMN, SAMPLE_COLUMN, TURNOUT_COLUMN = FIXED_COLUMNS
LEAD_COLUMN = "Lead"
RESULT_ROW_STYLE = "#EFEFEF"

_SECTION = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.MULTILINE)
_YEAR = re.compile(r"^(\d{4})(\s|$)")
_WIKILINK = re.compile(r"\[\[([^\]]*)\]\]")
_LINK_PARAM = re.compile(r"^link=(.*)$")

_NO_PCT = {"?", "<2.0", "–", ""}
_NO_SEATS = {"?", "–", ""}
_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
_DATE_SINGLE = re.compile(r"^(\d{1,2}) ([A-Z][a-z]{2})$")
_DATE_SAME_MONTH = re.compile(r"^(\d{1,2})–(\d{1,2}) ([A-Z][a-z]{2})$")
_DATE_RANGE = re.compile(r"^(\d{1,2}) ([A-Z][a-z]{2})–(\d{1,2}) ([A-Z][a-z]{2})$")


@dataclass(frozen=True)
class PollResultRow:
    """One party in one poll: percentage and seat projection."""

    pct: Decimal | None
    seats_min: int | None
    seats_max: int | None


@dataclass(frozen=True)
class PollRow:
    """One data row of a year table: firm, fieldwork, sample, turnout, results."""

    source: str
    pollster_name: str
    fieldwork_start: date | None
    fieldwork_end: date | None
    sample_size: int | None
    turnout: Decimal | None
    results: dict[str, PollResultRow]


@dataclass(frozen=True)
class _Plan:
    """Column roles by index: fixed label → column, column → party key.

    A party key is the catalogue slug of a labelled column or the raw label of
    an unknown one; the loader resolves its identity.
    """

    fixed: dict[str, int]
    parties: dict[int, str]


def _split_sections(text: str) -> list[tuple[int, str, str]]:
    """Level-tagged ``(level, title, body)`` sections, in page order.

    The body of a section ends at the next heading of the same or a higher
    level, so a level-4 section owns its level-5 subsections.
    """
    matches = list(_SECTION.finditer(text))
    sections: list[tuple[int, str, str]] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        end = len(text)
        for later in matches[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        sections.append((level, match.group(2), text[match.end() : end]))
    return sections


def poll_tables(wikitext: str) -> list[tuple[int, Table]]:
    """``(year, table)`` of every table in the year subsections, in page order."""
    body = next(
        (
            section_body
            for level, title, section_body in _split_sections(wikitext)
            if level == 4 and title == POLLS_SECTION
        ),
        None,
    )
    if body is None:
        logger.warning("%s section not found", POLLS_SECTION)
        return []
    tables: list[tuple[int, Table]] = []
    for level, title, section_body in _split_sections(body):
        year = _YEAR.match(title)
        if level == 5 and year:
            tables.extend(
                (int(year.group(1)), table) for table in parse_tables(section_body)
            )
    return tables


def parse_polls(wikitext: str, catalog: Catalog | None = None) -> list[PollRow]:
    """Polls of every year table of the page, in page order."""
    catalog = load_catalog() if catalog is None else catalog
    return [
        row
        for year, table in poll_tables(wikitext)
        for row in _read_table(table, year, catalog)
    ]


def parse_date(text: str, year: int) -> tuple[date | None, date | None]:
    """Fieldwork dates of a cell as ``(start, end)``; ``year`` comes from the section.

    A single day sets start and end to it (the source publishes the publication
    date when the fieldwork is unknown); a range crossing the year boundary
    subtracts one from the start.
    """
    text = text.strip()
    if text == "?":
        return None, None
    single = _DATE_SINGLE.match(text)
    same_month = _DATE_SAME_MONTH.match(text)
    months = _DATE_RANGE.match(text)
    try:
        if single and single.group(2) in _MONTHS:
            day = date(year, _MONTHS[single.group(2)], int(single.group(1)))
            return day, day
        if same_month and same_month.group(3) in _MONTHS:
            month = _MONTHS[same_month.group(3)]
            return (
                date(year, month, int(same_month.group(1))),
                date(year, month, int(same_month.group(2))),
            )
        if months and months.group(2) in _MONTHS and months.group(4) in _MONTHS:
            start_month = _MONTHS[months.group(2)]
            end_month = _MONTHS[months.group(4)]
            start_year = year - 1 if start_month > end_month else year
            return (
                date(start_year, start_month, int(months.group(1))),
                date(year, end_month, int(months.group(3))),
            )
    except ValueError:
        pass
    logger.warning("unparseable date: %s", text)
    return None, None


def _label(cell_text: str) -> str:
    """Header cell label: last wikilink parameter (``link=`` value when present)."""
    match = _WIKILINK.search(cell_text)
    if match is None:
        return cell_text.strip()
    label = match.group(1).split("|")[-1].strip()
    link = _LINK_PARAM.match(label)
    return link.group(1).strip() if link else label


def _column_plan(label_cells: list[Cell], catalog: Catalog) -> _Plan | None:
    """Column roles from the label row; None when the fixed labels are missing."""
    labels = [_label(cell.text) for cell in label_cells]
    if not set(FIXED_COLUMNS) <= set(labels):
        logger.warning("not a polls table: missing fixed header labels")
        return None
    fixed: dict[str, int] = {}
    parties: dict[int, str] = {}
    for index, label in enumerate(labels):
        if label in FIXED_COLUMNS:
            fixed[label] = index
        elif label == LEAD_COLUMN:
            continue
        else:
            entry = catalog.lookup(label)
            if entry is None:
                logger.warning("unknown party column: %s", label)
                parties[index] = label
            else:
                parties[index] = entry.slug
    return _Plan(fixed=fixed, parties=parties)


def _read_table(table: Table, year: int, catalog: Catalog) -> list[PollRow]:
    """Data rows of one table: headers, separators and results skipped.

    Cells are read by the plan (never by position); misaligned rows are skipped
    with a warning.
    """
    if not table.rows:
        return []
    header = table.rows[0].cells
    plan = _column_plan(header, catalog)
    if plan is None:
        return []
    rows: list[PollRow] = []
    for row in table.rows[1:]:
        if row.cells and row.cells[0].header:
            continue
        if RESULT_ROW_STYLE in row.attrs.get("style", ""):
            continue
        if len(row.cells) == 1 and "colspan" in row.cells[0].attrs:
            continue
        if len(row.cells) != len(header):
            logger.warning(
                "column count mismatch: %s != %s", len(row.cells), len(header)
            )
            continue
        rows.append(_read_row(row, plan, year))
    return rows


def _read_row(row: Row, plan: _Plan, year: int) -> PollRow:
    """One data row as a ``PollRow`` (firm, dates, sample, turnout, results)."""
    results: dict[str, PollResultRow] = {}
    for index, key in plan.parties.items():
        result = _parse_party_cell(row.cells[index].text)
        if result is not None:
            results[key] = result
    start, end = parse_date(row.cells[plan.fixed[DATE_COLUMN]].text, year)
    source = row.cells[plan.fixed[FIRM_COLUMN]].text
    return PollRow(
        source=source,
        pollster_name=_pollster_name(source),
        fieldwork_start=start,
        fieldwork_end=end,
        sample_size=_parse_sample(row.cells[plan.fixed[SAMPLE_COLUMN]].text),
        turnout=_parse_turnout(row.cells[plan.fixed[TURNOUT_COLUMN]].text),
        results=results,
    )


def _pollster_name(source: str) -> str:
    """Firm name of a signature: text before the first ``(`` or ``/``."""
    return re.split(r"[/(]", source, maxsplit=1)[0].strip()


def _parse_party_cell(text: str) -> PollResultRow | None:
    """Party cell as a result (``pct`` and/or seats), or None without values."""
    lines = text.split("\n")
    pct = _parse_pct(lines[0])
    seats_min, seats_max = _parse_seats(lines[1] if len(lines) > 1 else "")
    if pct is None and seats_min is None and seats_max is None:
        return None
    return PollResultRow(pct=pct, seats_min=seats_min, seats_max=seats_max)


def _parse_pct(text: str) -> Decimal | None:
    """First line of a party cell as a percentage (None for unknown forms)."""
    if text in _NO_PCT:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        logger.warning("unparseable pct: %s", text)
        return None


def _parse_seats(text: str) -> tuple[int | None, int | None]:
    """Seat projection as ``(min, max)`` (``N`` or ``N/M``; None for unknown)."""
    if text in _NO_SEATS:
        return None, None
    try:
        if "/" in text:
            start, end = text.split("/", 1)
            return int(start), int(end)
        seats = int(text)
        return seats, seats
    except ValueError:
        logger.warning("unparseable seats: %s", text)
        return None, None


def _parse_sample(text: str) -> int | None:
    """Sample size cell as an int (``1,000`` → 1000; None when unparseable)."""
    if text == "?":
        return None
    try:
        return int(text.replace(",", ""))
    except ValueError:
        logger.warning("unparseable sample size: %s", text)
        return None


def _parse_turnout(text: str) -> Decimal | None:
    """Turnout cell as a ``Decimal`` (None when unparseable)."""
    if text == "?":
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        logger.warning("unparseable turnout: %s", text)
        return None
