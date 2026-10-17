"""File 10: votes per candidacy and polling station (and CERA)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ingestor.elections.parsers.common import (
    StationRef,
    integer,
    parse_station_ref,
    read_records,
    text,
)


@dataclass(frozen=True)
class StationVotes(StationRef):
    candidacy_code: str
    votes: int


def parse_record(record: str) -> StationVotes:
    ref = parse_station_ref(record)
    return StationVotes(
        **vars(ref),
        candidacy_code=text(record, 23, 29),
        votes=integer(record, 29, 36),
    )


def parse(path: Path) -> list[StationVotes]:
    return [parse_record(record) for record in read_records(path)]
