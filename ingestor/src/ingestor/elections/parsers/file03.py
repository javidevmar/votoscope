"""File 03: candidacies (siglas, denomination and accumulation heads)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ingestor.elections.parsers.common import integer, read_records, text


@dataclass(frozen=True)
class Candidacy:
    process_code: str
    year: int
    month: int
    code: str
    short_name: str  # siglas
    name: str  # denominación
    provincial_head: str
    regional_head: str
    national_head: str


def parse_record(record: str) -> Candidacy:
    return Candidacy(
        process_code=text(record, 0, 2),
        year=integer(record, 2, 6),
        month=integer(record, 6, 8),
        code=text(record, 8, 14),
        short_name=text(record, 14, 64),
        name=text(record, 64, 214),
        provincial_head=text(record, 214, 220),
        regional_head=text(record, 220, 226),
        national_head=text(record, 226, 232),
    )


def parse(path: Path) -> list[Candidacy]:
    return [parse_record(record) for record in read_records(path)]
