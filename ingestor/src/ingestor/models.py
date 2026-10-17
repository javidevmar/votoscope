"""Database schema definition.

Alembic migrations are generated from these models and are the source of
truth for the database: never run DDL by hand (see AGENTS.md).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

TableArgs = dict[str, Any] | tuple[Any, ...]


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------- bronze


class Ingestion(Base):
    """One row per source file ever ingested (bronze registry)."""

    __tablename__ = "ingestion"
    __table_args__: ClassVar[TableArgs] = {"schema": "bronze"}

    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(Text)  # relative to data/raw/
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    size_bytes: Mapped[int]
    source: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="registered")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# --------------------------------------------------------------------- silver


# Geography (INE codes; see the official municipality gazetteer).


class AutonomousCommunity(Base):
    """Autonomous community (``codigo_ccaa`` in the source files)."""

    __tablename__ = "autonomous_community"
    __table_args__: ClassVar[TableArgs] = {"schema": "silver"}

    ine_code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(Text)


class Province(Base):
    """Province (``codigo_provincia``): the constituency for Congreso."""

    __tablename__ = "province"
    __table_args__: ClassVar[TableArgs] = {"schema": "silver"}

    ine_code: Mapped[str] = mapped_column(String(2), primary_key=True)
    autonomous_community_ine_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("silver.autonomous_community.ine_code"), index=True
    )
    name: Mapped[str] = mapped_column(Text)


class Municipality(Base):
    """Municipality (``codigo_provincia`` + ``codigo_municipio`` = 5 digits).

    CERA (votes from Spaniards abroad) is stored as one pseudo municipality
    per province: INE code ``<province>999``, name "CERA".
    """

    __tablename__ = "municipality"
    __table_args__: ClassVar[TableArgs] = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ine_code: Mapped[str] = mapped_column(String(5), unique=True)
    province_ine_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("silver.province.ine_code"), index=True
    )
    name: Mapped[str | None] = mapped_column(
        Text
    )  # null if absent from INE and file 05


class PollingStation(Base):
    """Polling station (mesa), the finest published unit; election-agnostic.

    CERA pseudo stations live under the province's CERA municipality with
    district 09 (or the Senate electoral district), section 0000, code U.
    """

    __tablename__ = "polling_station"
    __table_args__: ClassVar[TableArgs] = (
        UniqueConstraint("municipality_id", "district", "section", "code"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_id: Mapped[int] = mapped_column(ForeignKey("silver.municipality.id"))
    district: Mapped[str] = mapped_column(String(2))
    section: Mapped[str] = mapped_column(String(4))
    code: Mapped[str] = mapped_column(String(1))


# Elections and candidacies.


class Election(Base):
    """An election process held in a place.

    ``autonomous_community_ine_code`` / ``municipality_id`` state where it is
    held: null for national elections (Congreso, Senado, Europeas), the
    community for regional ones, the municipality for municipal ones.
    """

    __tablename__ = "election"
    __table_args__: ClassVar[TableArgs] = (
        UniqueConstraint(
            "type",
            "date",
            "autonomous_community_ine_code",
            "municipality_id",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "num_nonnulls(autonomous_community_ine_code, municipality_id) <= 1",
            name="election_scope_at_most_one",
        ),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # congress | senate | regional | municipal | european
    type: Mapped[str] = mapped_column(String(20))
    date: Mapped[date] = mapped_column(Date)
    name: Mapped[str | None] = mapped_column(Text)
    autonomous_community_ine_code: Mapped[str | None] = mapped_column(
        String(2), ForeignKey("silver.autonomous_community.ine_code")
    )
    municipality_id: Mapped[int | None] = mapped_column(
        ForeignKey("silver.municipality.id")
    )


class Party(Base):
    """A party, at its nationally accumulated identity level.

    Provisionally one row per national candidacy head (source file 03);
    curated brands may come later.
    """

    __tablename__ = "party"
    __table_args__: ClassVar[TableArgs] = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    color: Mapped[str | None] = mapped_column(String(7))  # hex, e.g. #ff0000


class PartyElection(Base):
    """A candidacy: a party running in one election, as published in source.

    A party can have several candidacies in the same election (national
    branches), hence the surrogate id: votes reference the candidacy, not
    the party.
    """

    __tablename__ = "party_election"
    __table_args__: ClassVar[TableArgs] = (
        UniqueConstraint("election_id", "code"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("silver.election.id"))
    party_id: Mapped[int] = mapped_column(ForeignKey("silver.party.id"), index=True)
    code: Mapped[str] = mapped_column(String(6))  # source candidacy code
    short_name: Mapped[str] = mapped_column(String(50))  # siglas
    name: Mapped[str] = mapped_column(Text)  # denominacion


# Facts (one row per polling station x election).


class Turnout(Base):
    """Census and votes cast at one polling station in one election.

    Voters and valid votes are always derived from the facts:
    voters = sum(vote.votes) + blank_votes + null_votes.
    """

    __tablename__ = "turnout"
    __table_args__: ClassVar[TableArgs] = (
        UniqueConstraint("polling_station_id", "election_id"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polling_station_id: Mapped[int] = mapped_column(
        ForeignKey("silver.polling_station.id")
    )
    election_id: Mapped[int] = mapped_column(
        ForeignKey("silver.election.id"), index=True
    )
    census: Mapped[int]  # INE census
    blank_votes: Mapped[int]
    null_votes: Mapped[int]


class Vote(Base):
    """Votes obtained by one candidacy at one polling station."""

    __tablename__ = "vote"
    __table_args__: ClassVar[TableArgs] = (
        UniqueConstraint("polling_station_id", "party_election_id"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polling_station_id: Mapped[int] = mapped_column(
        ForeignKey("silver.polling_station.id")
    )
    party_election_id: Mapped[int] = mapped_column(
        ForeignKey("silver.party_election.id"), index=True
    )
    votes: Mapped[int]


# Polls (opinion polls from the Wikipedia snapshot).


class Pollster(Base):
    """Polling firm signing a poll (extracted from the source literal)."""

    __tablename__ = "pollster"
    __table_args__: ClassVar[TableArgs] = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(60), unique=True)


class Poll(Base):
    """One opinion poll from the Wikipedia snapshot."""

    __tablename__ = "poll"
    __table_args__: ClassVar[TableArgs] = (
        CheckConstraint("turnout >= 0 AND turnout <= 100", name="poll_turnout_range"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pollster_id: Mapped[int] = mapped_column(ForeignKey("silver.pollster.id"))
    source: Mapped[str] = mapped_column(Text)  # header literal
    election_type: Mapped[str] = mapped_column(String(20))  # congress | ...
    election_id: Mapped[int | None] = mapped_column(ForeignKey("silver.election.id"))
    fieldwork_start: Mapped[date | None] = mapped_column(Date)
    fieldwork_end: Mapped[date | None] = mapped_column(Date)
    sample_size: Mapped[int | None]
    turnout: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    revision_id: Mapped[int] = mapped_column(BigInteger)


class PollResult(Base):
    """Percentage and seat projection of one party in one poll."""

    __tablename__ = "poll_result"
    __table_args__: ClassVar[TableArgs] = (
        UniqueConstraint("poll_id", "party_id"),
        CheckConstraint("pct >= 0 AND pct <= 100", name="poll_result_pct_range"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("silver.poll.id"), index=True)
    party_id: Mapped[int] = mapped_column(ForeignKey("silver.party.id"), index=True)
    pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    seats_min: Mapped[int | None]
    seats_max: Mapped[int | None]
