"""Silver loader for one election: candidacies, geography links and facts.

Contract (see docs/ingestor/ingesta.md, «Comportamiento de ingest»):

- Re-ingest: when any file of an election is new, that election's facts
  (``vote``, ``turnout``) and candidacies (``party_election``) are deleted
  and reloaded from the current files, all in one transaction.
- Validations: candidacies in 10 must exist in 03, stations in 10 must exist
  in 09, and votes in 10 must add up to the "votos a candidaturas" field of
  09 per station. The last check is downgraded to a warning in the processes
  where the ministry's own files disagree (adapter policy).
"""

from __future__ import annotations

import collections
import logging
from pathlib import Path

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from ingestor.elections.adapters import CongresoAdapter
from ingestor.elections.parsers import file03, file05, file09, file10
from ingestor.elections.parsers.file02 import ProcessIdentification
from ingestor.errors import IngestError
from ingestor.models import (
    Election,
    Municipality,
    Party,
    PartyElection,
    PollingStation,
    Province,
    Turnout,
    Vote,
)
from ingestor.parties import PartyResolver, load_catalog

logger = logging.getLogger(__name__)

_INSERT_CHUNK = 20_000  # rows per bulk insert batch


def load_election(
    session: Session,
    adapter: CongresoAdapter,
    files: dict[str, Path],
    identification: ProcessIdentification,
) -> None:
    election = _get_or_create_election(session, adapter, identification)
    _delete_election_facts(session, election)

    candidacies = file03.parse(files["03"])
    known_codes = {candidacy.code for candidacy in candidacies}
    if len(known_codes) != len(candidacies):
        raise IngestError(f"{files['03']}: duplicate candidacy codes")
    candidacy_by_code = {candidacy.code: candidacy for candidacy in candidacies}
    parties = _resolve_parties(session, candidacies, candidacy_by_code)
    party_election_by_code: dict[str, PartyElection] = {}
    for candidacy in candidacies:
        party_election = PartyElection(
            election_id=election.id,
            party_id=parties[candidacy.national_head].id,
            code=candidacy.code,
            short_name=candidacy.short_name,
            name=candidacy.name,
        )
        session.add(party_election)
        party_election_by_code[candidacy.code] = party_election
    session.flush()

    province_codes = set(session.scalars(select(Province.ine_code)))
    municipalities = {
        row.ine_code: row for row in session.scalars(select(Municipality))
    }
    name_hints = _name_hints(files.get("05"))

    station_rows = [
        row for row in file09.parse(files["09"]) if not adapter.skip_aggregate(row)
    ]
    for row in station_rows:
        _resolve_municipality(
            session,
            municipalities,
            province_codes,
            name_hints,
            row.province_code,
            row.municipality_code,
        )
    session.flush()

    station_ids = _station_ids(session, station_rows, municipalities)
    session.flush()

    published_totals: dict[tuple, int] = {}
    turnout_rows: list[dict] = []
    for row in station_rows:
        key = _station_key(row, municipalities)
        published_totals[key] = row.candidacy_votes
        turnout_rows.append(
            {
                "polling_station_id": station_ids[key],
                "election_id": election.id,
                "census": row.census,
                "blank_votes": row.blank_votes,
                "null_votes": row.null_votes,
            }
        )
    session.execute(insert(Turnout), turnout_rows)

    loaded_totals: collections.Counter[tuple] = collections.Counter()
    unknown_codes: set[str] = set()
    unknown_stations: set[tuple] = set()
    vote_rows: list[dict] = []
    for row in file10.parse(files["10"]):
        if adapter.skip_aggregate(row):
            continue
        code = adapter.normalize_candidacy_code(row.candidacy_code, known_codes)
        if code not in party_election_by_code:
            unknown_codes.add(row.candidacy_code)
            continue
        key = _station_key(row, municipalities)
        if key not in station_ids:
            unknown_stations.add(key)
            continue
        loaded_totals[key] += row.votes
        if row.votes:  # zero-vote rows add no fact
            vote_rows.append(
                {
                    "polling_station_id": station_ids[key],
                    "party_election_id": party_election_by_code[code].id,
                    "votes": row.votes,
                }
            )
            if len(vote_rows) >= _INSERT_CHUNK:
                session.execute(insert(Vote), vote_rows)
                vote_rows.clear()
    if vote_rows:
        session.execute(insert(Vote), vote_rows)
    if unknown_codes:
        raise IngestError(
            f"{files['10']}: candidacies not in 03: {sorted(unknown_codes)[:5]}"
        )
    if unknown_stations:
        raise IngestError(
            f"{files['10']}: stations not in 09: {sorted(unknown_stations)[:5]}"
        )

    mismatches = [
        (key, published, loaded_totals.get(key, 0))
        for key, published in published_totals.items()
        if loaded_totals.get(key, 0) != published
    ]
    if mismatches:
        net = sum(published - loaded for _, published, loaded in mismatches)
        summary = (
            f"{len(mismatches)} stations where sum(votes in 10) != candidaturas in 09 "
            f"(net {net:+d} votes)"
        )
        if adapter.strict_station_totals(identification.year):
            raise IngestError(f"{summary}; examples: {mismatches[:5]}")
        logger.warning(
            "%s %s: %s (known source inconsistency, ignored)",
            adapter.election_type,
            identification.election_date,
            summary,
        )
        logger.debug("mismatching stations: %s", mismatches[:50])


def _get_or_create_election(
    session: Session, adapter: CongresoAdapter, identification: ProcessIdentification
) -> Election:
    election = session.scalar(
        select(Election).where(
            Election.type == adapter.election_type,
            Election.date == identification.election_date,
            Election.autonomous_community_ine_code.is_(None),
            Election.municipality_id.is_(None),
        )
    )
    if election is None:
        election = Election(
            type=adapter.election_type, date=identification.election_date
        )
        session.add(election)
        session.flush()
    return election


def _delete_election_facts(session: Session, election: Election) -> None:
    party_election_ids = select(PartyElection.id).where(
        PartyElection.election_id == election.id
    )
    session.execute(delete(Vote).where(Vote.party_election_id.in_(party_election_ids)))
    session.execute(delete(Turnout).where(Turnout.election_id == election.id))
    session.execute(
        delete(PartyElection).where(PartyElection.election_id == election.id)
    )


def _resolve_parties(
    session: Session,
    candidacies: list[file03.Candidacy],
    candidacy_by_code: dict[str, file03.Candidacy],
) -> dict[str, Party]:
    """Group candidacies by national head through the shared party resolver."""
    heads: dict[str, file03.Candidacy] = {}
    for candidacy in candidacies:
        heads.setdefault(
            candidacy.national_head,
            candidacy_by_code.get(candidacy.national_head, candidacy),
        )

    resolver = PartyResolver(session.scalars(select(Party)), load_catalog())
    parties: dict[str, Party] = {}
    for head_code, head in heads.items():
        label = head.short_name or head.name or f"party-{head_code}"
        party = resolver.resolve(label, code=head_code)
        session.add(party)  # no-op if the row was already persistent
        parties[head_code] = party
    session.flush()
    return parties


def _resolve_municipality(
    session: Session,
    index: dict[str, Municipality],
    province_codes: set[str],
    name_hints: dict[str, str],
    province_code: str,
    municipality_code: str,
) -> Municipality:
    ine_code = f"{province_code}{municipality_code}"
    municipality = index.get(ine_code)
    if municipality is not None:
        return municipality
    if province_code not in province_codes:
        raise IngestError(
            f"province {province_code} is not in silver.province; run load-geography first"
        )
    if municipality_code == "999":
        name = "CERA"
    else:
        name = name_hints.get(ine_code)
        if name:
            logger.warning(
                "municipality %s not in the gazetteer; named from the election's file 05: %s",
                ine_code,
                name,
            )
        else:
            logger.warning(
                "municipality %s not in the gazetteer nor in file 05; loaded without a name",
                ine_code,
            )
    municipality = Municipality(
        ine_code=ine_code, province_ine_code=province_code, name=name
    )
    session.add(municipality)
    session.flush()
    index[ine_code] = municipality
    return municipality


def _station_key(row, municipalities: dict[str, Municipality]) -> tuple:
    municipality = municipalities.get(f"{row.province_code}{row.municipality_code}")
    return (
        municipality.id if municipality else None,
        row.district,
        row.section,
        row.station_code,
    )


def _station_ids(
    session: Session,
    station_rows: list[file09.StationData],
    municipalities: dict[str, Municipality],
) -> dict[tuple, int]:
    """Get or create the polling stations of these rows; return key -> id."""
    station_ids: dict[tuple, int] = {}
    municipality_ids = {_station_key(row, municipalities)[0] for row in station_rows}
    existing = session.scalars(
        select(PollingStation).where(
            PollingStation.municipality_id.in_(municipality_ids)
        )
    )
    for station in existing:
        station_ids[
            (station.municipality_id, station.district, station.section, station.code)
        ] = station.id

    new_stations: list[tuple[tuple, PollingStation]] = []
    pending: set[tuple] = set()
    for row in station_rows:
        key = _station_key(row, municipalities)
        if key in station_ids or key in pending:
            continue
        station = PollingStation(
            municipality_id=key[0],
            district=row.district,
            section=row.section,
            code=row.station_code,
        )
        session.add(station)
        new_stations.append((key, station))
        pending.add(key)
    session.flush()
    for key, station in new_stations:
        station_ids[key] = station.id
    return station_ids


def _name_hints(path: Path | None) -> dict[str, str]:
    """Municipality names as published in file 05 of this election."""
    if path is None:
        return {}
    return {
        row.ine_code: row.name
        for row in file05.parse(path)
        if row.district == "99" and row.name
    }
