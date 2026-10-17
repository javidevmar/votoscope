"""File 09: census, blank and null votes per polling station (and CERA)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ingestor.elections.parsers.common import (
    StationRef,
    integer,
    parse_station_ref,
    read_records,
)


@dataclass(frozen=True)
class StationData(StationRef):
    census: int
    blank_votes: int
    null_votes: int
    candidacy_votes: int  # published total, used for validation only


def parse_record(record: str) -> StationData:
    ref = parse_station_ref(record)
    return StationData(
        **vars(ref),
        census=integer(record, 23, 30),
        blank_votes=integer(record, 65, 72),
        null_votes=integer(record, 72, 79),
        candidacy_votes=integer(record, 79, 86),
    )


def parse(path: Path) -> list[StationData]:
    return [parse_record(record) for record in read_records(path)]
