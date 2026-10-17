"""File 02: identification of the election process."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ingestor.elections.parsers.common import integer, read_records, text


@dataclass(frozen=True)
class ProcessIdentification:
    process_code: str
    year: int
    month: int
    round_number: int
    scope_kind: str  # N = national, A = autonomic
    scope_code: str  # 99 for national
    election_date: date


def parse_record(record: str) -> ProcessIdentification:
    return ProcessIdentification(
        process_code=text(record, 0, 2),
        year=integer(record, 2, 6),
        month=integer(record, 6, 8),
        round_number=integer(record, 8, 9),
        scope_kind=text(record, 9, 10),
        scope_code=text(record, 10, 12),
        election_date=date(
            integer(record, 16, 20),  # year
            integer(record, 14, 16),  # month
            integer(record, 12, 14),  # day
        ),
    )


def parse(path: Path) -> list[ProcessIdentification]:
    return [parse_record(record) for record in read_records(path)]
