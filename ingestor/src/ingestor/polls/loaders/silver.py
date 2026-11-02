"""Silver loader for the Wikipedia polls snapshots: pollsters, parties and polls.

Contract (see docs/ingestor/ingesta.md, «Comportamiento de ingest-polls»):

- Silver: pollsters and parties are get-or-create; parties go through the
  shared resolver (catalogue → existing name → creation with a warning), and
  ``poll``/``poll_result`` are replaced in full, because silver reflects the
  last ingested snapshot (the revision history lives in bronze).
- Election resolution: every poll with a null ``election_id`` is linked to the
  first national election of its type after its fieldwork; it runs on every
  execution, also without new snapshots.
- Validations: every row needs a signature and two parties, ranges are
  checked, a percentage sum over the limit only warns (the page publishes no
  "others"); a failure rolls back and marks the file ``failed``.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker

from ingestor.errors import IngestError
from ingestor.models import Election, Party, Poll, PollResult, Pollster
from ingestor.parties import PartyResolver, load_catalog, slugify
from ingestor.polls.adapters.wikipedia_polls import ELECTION_TYPE, PollRow

logger = logging.getLogger(__name__)

MAX_SEATS = 350  # Congress size: a seat projection cannot exceed it
PCT_SUM_LIMIT = Decimal("100.5")


def load_polls(session: Session, rows: list[PollRow], revision_id: int) -> None:
    """Replace ``poll``/``poll_result`` with the snapshot rows (one transaction)."""
    _validate(rows, revision_id)
    pollster_ids = _resolve_pollsters(session, rows)
    party_ids = _resolve_parties(session, rows)

    session.execute(delete(PollResult))
    session.execute(delete(Poll))

    poll_rows = [
        {
            "pollster_id": pollster_ids[slugify(row.pollster_name)],
            "source": row.source,
            "media": row.media,
            "reestimator": row.reestimator,
            "election_type": ELECTION_TYPE,
            "election_id": None,
            "fieldwork_start": row.fieldwork_start,
            "fieldwork_end": row.fieldwork_end,
            "sample_size": row.sample_size,
            "turnout": row.turnout,
            "revision_id": revision_id,
        }
        for row in rows
    ]
    poll_ids = list(
        session.scalars(
            insert(Poll).returning(Poll.id, sort_by_parameter_order=True), poll_rows
        )
    )
    result_rows = [
        {
            "poll_id": poll_id,
            "party_id": party_ids[key],
            "pct": result.pct,
            "seats_min": result.seats_min,
            "seats_max": result.seats_max,
        }
        for row, poll_id in zip(rows, poll_ids, strict=True)
        for key, result in row.results.items()
    ]
    if result_rows:
        session.execute(insert(PollResult), result_rows)
    for row in rows:
        _pct_sum_warning(row, revision_id)


def resolve_poll_elections(session_factory: sessionmaker) -> int:
    """Link polls without an election to the first national one after them.

    Only polls with a null ``election_id`` are considered (idempotent), and
    only elections with no community/municipality and the same type; a poll
    without a candidate or without ``fieldwork_end`` stays null. Returns the
    number of polls linked.
    """
    with session_factory() as session:
        polls = list(session.scalars(select(Poll).where(Poll.election_id.is_(None))))
        national: dict[str, list[Election]] = {}
        linked = 0
        for poll in polls:
            if poll.fieldwork_end is None:
                continue
            if poll.election_type not in national:
                national[poll.election_type] = list(
                    session.scalars(
                        select(Election)
                        .where(
                            Election.type == poll.election_type,
                            Election.autonomous_community_ine_code.is_(None),
                            Election.municipality_id.is_(None),
                        )
                        .order_by(Election.date)
                    )
                )
            election = next(
                (
                    candidate
                    for candidate in national[poll.election_type]
                    if candidate.date > poll.fieldwork_end
                ),
                None,
            )
            if election is None:
                continue
            poll.election_id = election.id
            linked += 1
        if linked:
            session.commit()
    if linked:
        logger.info("linked %d polls to elections", linked)
    return linked


def _validate(rows: list[PollRow], revision_id: int) -> None:
    """Structural checks; a failure aborts before touching silver."""
    if not rows:
        raise IngestError(f"revision {revision_id}: no polls parsed")
    for row in rows:
        label = f"revision {revision_id}, {row.source or '?'}"
        if not row.source.strip() or not row.pollster_name.strip():
            raise IngestError(f"{label}: no signature")
        if len(row.results) < 2:
            raise IngestError(f"{label}: fewer than two parties with a value")
        if row.turnout is not None and not 0 <= row.turnout <= 100:
            raise IngestError(f"{label}: turnout out of range: {row.turnout}")
        for key, result in row.results.items():
            if result.pct is not None and not 0 <= result.pct <= 100:
                raise IngestError(
                    f"{label}: {key} percentage out of range: {result.pct}"
                )
            for seats in (result.seats_min, result.seats_max):
                if seats is not None and not 0 <= seats <= MAX_SEATS:
                    raise IngestError(f"{label}: {key} seats out of range: {seats}")
            if (
                result.seats_min is not None
                and result.seats_max is not None
                and result.seats_min > result.seats_max
            ):
                raise IngestError(
                    f"{label}: {key} seats out of range: "
                    f"{result.seats_min} > {result.seats_max}"
                )


def _resolve_pollsters(session: Session, rows: list[PollRow]) -> dict[str, int]:
    """Get or create the pollster of every row (slug -> id)."""
    slugs = {slugify(row.pollster_name) for row in rows}
    existing = {
        pollster.slug: pollster
        for pollster in session.scalars(
            select(Pollster).where(Pollster.slug.in_(slugs))
        )
    }
    for row in rows:
        slug = slugify(row.pollster_name)
        if slug not in existing:
            existing[slug] = Pollster(name=row.pollster_name, slug=slug)
            session.add(existing[slug])
    session.flush()
    return {slug: pollster.id for slug, pollster in existing.items()}


def _resolve_parties(session: Session, rows: list[PollRow]) -> dict[str, int]:
    """Resolve every result key (catalogue slug or raw label) to a party row."""
    keys = {key for row in rows for key in row.results}
    resolver = PartyResolver(session.scalars(select(Party)), load_catalog())
    parties = {key: resolver.resolve(key) for key in keys}
    for party in set(parties.values()):
        session.add(party)  # no-op when the row was already persistent
    session.flush()
    return {key: party.id for key, party in parties.items()}


def _pct_sum_warning(row: PollRow, revision_id: int) -> None:
    """Warn when a poll's percentages add up to more than the limit."""
    total = sum(
        (result.pct for result in row.results.values() if result.pct is not None),
        Decimal(0),
    )
    if total > PCT_SUM_LIMIT:
        logger.warning(
            "revision %s, %s: percentages add up to %s (limit %s)",
            revision_id,
            row.source,
            total,
            PCT_SUM_LIMIT,
        )
