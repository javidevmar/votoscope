"""Generic wikitext table lexer.

Tokenises ``{|…|}`` blocks, ``|-`` rows and ``|``/``!`` cells. Source-agnostic:
the Wikipedia-specific rules (sections and tables per year, headers, dates,
parties) live in the adapters.

Stdlib only (``re``, ``logging``, ``dataclasses``); pure functions, no network
or disk access.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_REF_SELF_CLOSING = re.compile(r"<ref\b[^>]*/>")
_REF_PAIR = re.compile(r"<ref\b[^>]*>.*?</ref>", re.DOTALL)
_EFN = re.compile(r"\{\{\s*efn\b")
_SMALLER = re.compile(r"\{\{\s*smaller\b")
_FONT = re.compile(r"\{\{\s*font\b")
_FONT_TEXT = re.compile(r"\|text=([^|]*)")
_BR = re.compile(r"<br\s*/?>")
_BOLD = re.compile(r"'''")


@dataclass(frozen=True)
class Cell:
    """One table cell: cleaned text, ``!`` header flag and its attributes."""

    text: str
    header: bool
    attrs: dict[str, str]


@dataclass(frozen=True)
class Row:
    """One table row: cells left to right and ``|-`` line attributes."""

    cells: list[Cell]
    attrs: dict[str, str]


@dataclass(frozen=True)
class Table:
    """One ``{|…|}`` block: rows in order and ``{|`` line attributes."""

    rows: list[Row]
    attrs: dict[str, str]


def clean(text: str) -> str:
    """Clean cell text: references, footnotes, markup and surrounding spaces.

    Rules are applied until a fixed point (substitutions can expose nested
    constructions); a truncated template is left as is, without raising.
    """
    while True:
        cleaned = _clean_once(text)
        if cleaned == text:
            return text.strip()
        text = cleaned


def parse_tables(wikitext: str) -> list[Table]:
    """Tokenise every ``{|…|}`` block of ``wikitext`` into a table, in order."""
    tables: list[Table] = []
    table_attrs: dict[str, str] = {}
    rows: list[Row] = []
    row: Row | None = None
    inside = False

    def close_row() -> None:
        nonlocal row
        if row is not None:
            rows.append(row)
            row = None

    for line in wikitext.splitlines():
        stripped = line.strip()
        if not inside:
            if stripped.startswith("{|"):
                inside = True
                table_attrs = _parse_attrs(stripped[2:])
                rows = []
                row = None
            continue
        if stripped == "|}":
            close_row()
            tables.append(Table(rows=_expand_rowspans(rows), attrs=table_attrs))
            inside = False
        elif stripped.startswith("|-"):
            close_row()
            row = Row(cells=[], attrs=_parse_attrs(stripped[2:]))
        elif stripped.startswith(("|", "!")):
            if row is None:
                row = Row(cells=[], attrs={})
            prefix, value = _split_cell(stripped[1:])
            row.cells.append(
                Cell(
                    text=clean(value),
                    header=stripped[0] == "!",
                    attrs=_parse_attrs(prefix),
                )
            )
        # any other line inside a table is ignored
    if inside:
        logger.warning("unterminated table at end of input")
        close_row()
        tables.append(Table(rows=_expand_rowspans(rows), attrs=table_attrs))
    return tables


def _parse_attrs(prefix: str) -> dict[str, str]:
    """Quoted ``key="value"`` pairs of an attribute prefix (templates ignored)."""
    return {key: value for key, value in _ATTR.findall(prefix)}


def _clean_once(text: str) -> str:
    """One pass of the cleaning rules, in order."""
    text = _REF_SELF_CLOSING.sub("", text)
    text = _REF_PAIR.sub("", text)
    text = _strip_template(text, _EFN)
    text = _BR.sub("\n", text)
    text = _BOLD.sub("", text)
    text = _unwrap_smaller(text)
    return _unwrap_font(text)


def _strip_template(text: str, pattern: re.Pattern[str]) -> str:
    """Remove every ``pattern`` template, closing at its balanced ``}}``."""
    while True:
        match = pattern.search(text)
        if not match:
            return text
        end = _find_balanced(text, match.start())
        if end is None:
            return text
        text = text[: match.start()] + text[end + 2 :]


def _unwrap_smaller(text: str) -> str:
    """Replace ``{{smaller|X}}`` with ``X``."""
    while True:
        match = _SMALLER.search(text)
        if not match:
            return text
        end = _find_balanced(text, match.start())
        if end is None:
            return text
        body = text[match.start() + 2 : end]
        _, separator, content = body.partition("|")
        if not separator:
            return text
        text = text[: match.start()] + content + text[end + 2 :]


def _unwrap_font(text: str) -> str:
    """Replace ``{{font|…|text=X}}`` with ``X`` (empty when ``text=`` is empty)."""
    while True:
        match = _FONT.search(text)
        if not match:
            return text
        end = _find_balanced(text, match.start())
        if end is None:
            return text
        body = text[match.start() + 2 : end]
        value = _FONT_TEXT.search(body)
        if value is None:
            return text
        text = text[: match.start()] + value.group(1) + text[end + 2 :]


def _find_balanced(text: str, start: int) -> int | None:
    """Index of the ``}}`` closing the ``{{`` at ``start`` (None if unclosed)."""
    depth = 0
    index = start
    while index < len(text) - 1:
        pair = text[index : index + 2]
        if pair == "{{":
            depth += 1
            index += 2
        elif pair == "}}":
            depth -= 1
            index += 2
            if depth == 0:
                return index - 2
        else:
            index += 1
    return None


def _expand_rowspans(rows: list[Row]) -> list[Row]:
    """Repeat rowspan cells into the following rows to keep columns aligned.

    A cell with ``rowspan="N"`` (N ≥ 2) is emitted again, at the same column,
    in the next N−1 rows.
    """
    pending: dict[int, tuple[int, Cell]] = {}
    expanded: list[Row] = []
    for row in rows:
        future: dict[int, tuple[int, Cell]] = {}
        cells: list[Cell] = []
        queue = list(row.cells)
        next_cell = 0
        column = 0
        while next_cell < len(queue) or pending:
            if column in pending:
                left, cell = pending[column]
                cells.append(cell)
                if left > 1:
                    pending[column] = (left - 1, cell)
                else:
                    del pending[column]
            elif next_cell < len(queue):
                cell = queue[next_cell]
                next_cell += 1
                cells.append(cell)
                span = _rowspan(cell)
                if span > 1:
                    future[column] = (span - 1, cell)
            else:
                # Row exhausted: emit the spans still ahead of this column,
                # in ascending order (the header ``Lead`` case).
                for pending_column in sorted(c for c in pending if c > column):
                    left, cell = pending[pending_column]
                    cells.append(cell)
                    if left > 1:
                        pending[pending_column] = (left - 1, cell)
                    else:
                        del pending[pending_column]
                break
            column += 1
        expanded.append(Row(cells=cells, attrs=row.attrs))
        pending = {**pending, **future}
    return expanded


def _rowspan(cell: Cell) -> int:
    """``rowspan`` attribute of a cell as an int (1 when absent or invalid)."""
    try:
        return int(cell.attrs.get("rowspan", "1"))
    except ValueError:
        return 1


def _split_cell(content: str) -> tuple[str, str]:
    """Split cell content into ``(attrs, value)`` at the first top-level ``|``.

    Pipes inside ``{{…}}``, ``[[…]]`` and ``<…>`` tags are not separators.
    """
    braces = 0
    brackets = 0
    index = 0
    while index < len(content):
        pair = content[index : index + 2]
        if pair == "{{":
            braces += 1
            index += 2
        elif pair == "}}":
            braces = max(braces - 1, 0)
            index += 2
        elif pair == "[[":
            brackets += 1
            index += 2
        elif pair == "]]":
            brackets = max(brackets - 1, 0)
            index += 2
        elif content[index] == "<":
            tag_end = content.find(">", index + 1)
            index = len(content) if tag_end == -1 else tag_end + 1
        elif content[index] == "|" and not braces and not brackets:
            return content[:index], content[index + 1 :]
        else:
            index += 1
    return "", content
