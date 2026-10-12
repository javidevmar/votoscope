"""Parser tests over minimal real snippets (tests/fixtures)."""

from pathlib import Path

from ingestor.parsers import file02, file03, file05, file09, file10

FIXTURES = Path(__file__).parent / "fixtures" / "02202307"


def test_file02_identification():
    (identification,) = file02.parse(FIXTURES / "02022307.DAT")
    assert identification.process_code == "02"
    assert identification.scope_kind == "N"
    assert identification.scope_code == "99"
    assert identification.election_date.isoformat() == "2023-07-23"


def test_file03_candidacies():
    candidacies = {c.code: c for c in file03.parse(FIXTURES / "03022307.DAT")}
    psoe = candidacies["000002"]
    assert psoe.short_name == "PSOE"
    assert psoe.name == "PARTIDO SOCIALISTA OBRERO ESPAÑOL"
    assert psoe.national_head == "000002"


def test_file05_names():
    municipalities = {m.ine_code: m for m in file05.parse(FIXTURES / "05022307.DAT")}
    assert municipalities["04001"].name == "Abla"
    assert municipalities["04001"].district == "99"


def test_file09_stations():
    stations = {
        (s.municipality_code, s.section, s.station_code): s
        for s in file09.parse(FIXTURES / "09022307.DAT")
    }
    station = stations[("001", "1", "A")]
    assert (station.province_code, station.district) == ("04", "01")
    assert (
        station.census,
        station.blank_votes,
        station.null_votes,
        station.candidacy_votes,
    ) == (
        429,
        1,
        2,
        328,
    )
    cera = stations[("999", "0", "U")]
    assert (cera.district, cera.candidacy_votes) == ("09", 2772)


def test_file10_votes():
    votes = file10.parse(FIXTURES / "10022307.DAT")
    assert [(v.candidacy_code, v.votes) for v in votes] == [
        ("000001", 1),
        ("000002", 122),
    ]
