"""Silver geography: load the INE gazetteer (CCAA, provinces, municipalities)."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from ingestor.errors import IngestError
from ingestor.models import AutonomousCommunity, Municipality, Province

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommunityRow:
    ine_code: str
    name: str


@dataclass(frozen=True)
class ProvinceRow:
    ine_code: str
    name: str
    autonomous_community_ine_code: str


@dataclass(frozen=True)
class MunicipalityRow:
    ine_code: str
    name: str
    province_ine_code: str


@dataclass(frozen=True)
class Geography:
    communities: list[CommunityRow]
    provinces: list[ProvinceRow]
    municipalities: list[MunicipalityRow]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise IngestError(
            f"missing gazetteer file {path}; see the INE section in .agents/data-sources.md"
        )
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_geography(ine_dir: Path) -> Geography:
    """Read the three INE CSVs (see .agents/data-sources.md for their source)."""
    return Geography(
        communities=[
            CommunityRow(row["ine_code"], row["name"])
            for row in _read_csv(ine_dir / "comunidades.csv")
        ],
        provinces=[
            ProvinceRow(
                row["ine_code"], row["name"], row["autonomous_community_ine_code"]
            )
            for row in _read_csv(ine_dir / "provincias.csv")
        ],
        municipalities=[
            MunicipalityRow(row["ine_code"], row["name"], row["province_ine_code"])
            for row in _read_csv(ine_dir / "municipios.csv")
        ],
    )


def load_geography(session_factory: sessionmaker, ine_dir: Path) -> Geography:
    """Idempotently upsert the gazetteer into silver (current names win)."""
    geography = read_geography(ine_dir)
    with session_factory() as session:
        if geography.communities:
            statement = insert(AutonomousCommunity).values(
                [
                    {"ine_code": row.ine_code, "name": row.name}
                    for row in geography.communities
                ]
            )
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[AutonomousCommunity.ine_code],
                    set_={"name": statement.excluded.name},
                )
            )
        if geography.provinces:
            statement = insert(Province).values(
                [
                    {
                        "ine_code": row.ine_code,
                        "name": row.name,
                        "autonomous_community_ine_code": row.autonomous_community_ine_code,
                    }
                    for row in geography.provinces
                ]
            )
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[Province.ine_code],
                    set_={
                        "name": statement.excluded.name,
                        "autonomous_community_ine_code": statement.excluded.autonomous_community_ine_code,
                    },
                )
            )
        if geography.municipalities:
            statement = insert(Municipality).values(
                [
                    {
                        "ine_code": row.ine_code,
                        "name": row.name,
                        "province_ine_code": row.province_ine_code,
                    }
                    for row in geography.municipalities
                ]
            )
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[Municipality.ine_code],
                    set_={
                        "name": statement.excluded.name,
                        "province_ine_code": statement.excluded.province_ine_code,
                    },
                )
            )
        session.commit()
    logger.info(
        "geography loaded: %d ccaa, %d provinces, %d municipalities",
        len(geography.communities),
        len(geography.provinces),
        len(geography.municipalities),
    )
    return geography
