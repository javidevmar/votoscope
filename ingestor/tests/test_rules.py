"""Adapter and helper rules (no database, no network)."""

from pathlib import Path

import pytest

from ingestor.adapters.congreso import CongresoAdapter
from ingestor.errors import IngestError
from ingestor.loaders.election import slugify
from ingestor.loaders.geography import read_geography
from ingestor.parsers.common import parse_station_ref

adapter = CongresoAdapter()


def test_2015_cera_candidacy_codes_are_rewritten():
    known = {"000010", "000066"}
    assert adapter.normalize_candidacy_code("900066", known) == "000066"
    assert adapter.normalize_candidacy_code("000010", known) == "000010"


def test_unknown_9_code_is_not_rewritten():
    assert adapter.normalize_candidacy_code("900066", {"123456"}) == "900066"


def test_cera_aggregates_are_skipped():
    national = parse_station_ref("0220230719999999090000U")
    province = parse_station_ref("0220230710149999090000U")
    assert adapter.skip_aggregate(national)
    assert not adapter.skip_aggregate(province)


def test_station_total_check_is_relaxed_only_for_known_years():
    assert not adapter.strict_station_totals(2015)
    assert adapter.strict_station_totals(2023)


def test_slugify():
    assert slugify("C's") == "c-s"
    assert slugify("MÁS PAÍS") == "mas-pais"
    assert slugify("  ") == ""


def test_read_geography(tmp_path: Path):
    (tmp_path / "comunidades.csv").write_text(
        "ine_code,name\n01,Andalucía\n", encoding="utf-8"
    )
    (tmp_path / "provincias.csv").write_text(
        "ine_code,name,autonomous_community_ine_code\n04,Almería,01\n", encoding="utf-8"
    )
    (tmp_path / "municipios.csv").write_text(
        "ine_code,name,province_ine_code\n04001,Abla,04\n", encoding="utf-8"
    )
    geography = read_geography(tmp_path)
    assert geography.communities[0].name == "Andalucía"
    assert geography.provinces[0].autonomous_community_ine_code == "01"
    assert geography.municipalities[0].ine_code == "04001"


def test_read_geography_missing_file(tmp_path: Path):
    with pytest.raises(IngestError):
        read_geography(tmp_path)
