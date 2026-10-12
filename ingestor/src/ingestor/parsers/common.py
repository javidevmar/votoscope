"""Shared helpers for the fixed-width source files."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


def read_records(path: Path) -> Iterator[str]:
    """Yield records decoded as latin-1 with trailing CR/LF stripped.

    The files are ANSI (Windows-1252); every record ends in CRLF or LF
    depending on the process (2023 uses CRLF for file 04).
    """
    with path.open("r", encoding="latin-1", newline="") as handle:
        for line in handle:
            yield line.rstrip("\r\n")


def text(record: str, start: int, end: int) -> str:
    """Return an alphanumeric field (left-aligned, space-padded)."""
    _check_length(record, end)
    return record[start:end].rstrip()


def integer(record: str, start: int, end: int) -> int:
    """Return a numeric field (right-aligned, zero-padded)."""
    _check_length(record, end)
    return int(record[start:end])


def _check_length(record: str, end: int) -> None:
    if len(record) < end:
        raise ValueError(f"record too short ({len(record)} < {end}): {record!r}")


@dataclass(frozen=True)
class StationRef:
    """Common header of files 09 and 10 (identifies a polling station)."""

    process_code: str
    year: int
    month: int
    round_number: int
    autonomous_community_code: str
    province_code: str
    municipality_code: str
    district: str
    section: str
    station_code: str

    @property
    def key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.autonomous_community_code,
            self.province_code,
            self.municipality_code,
            self.district,
            self.section,
            self.station_code,
        )


def parse_station_ref(record: str) -> StationRef:
    """Parse the 23-character header shared by files 09 and 10."""
    # Sections are published as three digits plus a trailing space, letter or
    # digit in recent processes, and as four digits before 1996; silver stores
    # them without leading zeros ("1", "5A") so a section is one row across
    # elections.
    section = text(record, 18, 22).strip().lstrip("0") or "0"
    return StationRef(
        process_code=text(record, 0, 2),
        year=integer(record, 2, 6),
        month=integer(record, 6, 8),
        round_number=integer(record, 8, 9),
        autonomous_community_code=text(record, 9, 11),
        province_code=text(record, 11, 13),
        municipality_code=text(record, 13, 16),
        district=text(record, 16, 18),
        section=section,
        station_code=text(record, 22, 23),
    )
