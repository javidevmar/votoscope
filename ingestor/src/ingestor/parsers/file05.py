"""File 05: municipality totals (only used as a name source).

The MVP loads no aggregates: this parser exists so the loader can name
municipalities that no longer appear in the current INE gazetteer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ingestor.parsers.common import integer, read_records, text


@dataclass(frozen=True)
class MunicipalityTotals:
    process_code: str
    year: int
    month: int
    round_number: int
    autonomous_community_code: str
    province_code: str
    municipality_code: str
    district: str  # 99 = municipality total
    name: str

    @property
    def ine_code(self) -> str:
        return f"{self.province_code}{self.municipality_code}"


def parse_record(record: str) -> MunicipalityTotals:
    return MunicipalityTotals(
        process_code=text(record, 0, 2),
        year=integer(record, 2, 6),
        month=integer(record, 6, 8),
        round_number=integer(record, 8, 9),
        autonomous_community_code=text(record, 9, 11),
        province_code=text(record, 11, 13),
        municipality_code=text(record, 13, 16),
        district=text(record, 16, 18),
        name=text(record, 18, 118),
    )


def parse(path: Path) -> list[MunicipalityTotals]:
    return [parse_record(record) for record in read_records(path)]
