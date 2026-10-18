"""Silver loader for the Wikipedia polls snapshots: bronze registry + facts.

Contract (see docs/ingestor/ingesta.md, «Comportamiento de ingest-polls»):

- Bronze: the snapshot is registered in ``bronze.ingestion`` with its sha256
  (source ``wikipedia-en``); a snapshot already ``processed`` is skipped.
- Revision guard: a snapshot older than ``max(poll.revision_id)`` is ignored
  with a warning unless ``force``.
- Silver: pollsters and parties are get-or-create; ``poll``/``poll_result``
  are replaced in full, because silver reflects the last ingested snapshot
  (the revision history lives in bronze).
- Election resolution: every poll with a null ``election_id`` is linked to the
  first national election of its type after its fieldwork; it runs on every
  execution, also without new snapshots.
- Validations: every row needs a signature and two parties, ranges are
  checked, a percentage sum over the limit only warns (the page publishes no
  "others"); a failure rolls back and marks the file ``failed``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session, sessionmaker

from ingestor.elections.loaders.election import sha256, slugify
from ingestor.errors import IngestError
from ingestor.models import Election, Ingestion, Party, Poll, PollResult, Pollster
from ingestor.polls.adapters.wikipedia_polls import (
    ELECTION_TYPE,
    PARTY_COLUMNS,
    PollRow,
    parse_polls,
)
from ingestor.polls.fetch import SOURCE

logger = logging.getLogger(__name__)

MAX_SEATS = 350  # Congress size: a seat projection cannot exceed it
PCT_SUM_LIMIT = Decimal("100.5")
_PARTY_NAMES = {column.slug: column.name for column in PARTY_COLUMNS.values()}


@dataclass(frozen=True)
class PollsOutcome:
    """Result of one snapshot: its file, status (processed|skipped|failed) and revision."""

    file: Path
    status: str
    revision_id: int


def ingest_polls_path(
    session_factory: sessionmaker,
    path: Path,
    raw_dir: Path,
    force: bool = False,
) -> list[PollsOutcome]:
    """Ingest one snapshot file, or every ``.wikitext`` under a directory.

    The election resolution runs first, before deciding what is pending; a
    snapshot error does not abort the remaining files (same as elections).
    """
    if not path.exists():
        raise IngestError(f"path does not exist: {path}")
    resolve_poll_elections(session_factory)
    outcomes: list[PollsOutcome] = []
    for file in _snapshot_files(path, raw_dir):
        try:
            outcomes.append(ingest_snapshot(session_factory, file, raw_dir, force))
        except IngestError as error:
            logger.error("%s: %s", file, error)
            outcomes.append(PollsOutcome(file, "failed", _revision_id(file)))
    return outcomes


def ingest_snapshot(
    session_factory: sessionmaker,
    path: Path,
    raw_dir: Path,
    force: bool = False,
) -> PollsOutcome:
    """Register and load one snapshot into silver, with the revision guard."""
    revision_id = _revision_id(path)
    digest = sha256(path)
    with session_factory() as session:
        registered = session.scalar(select(Ingestion).where(Ingestion.sha256 == digest))
        max_revision = session.scalar(select(func.max(Poll.revision_id)))
    if registered is not None and registered.status == "processed" and not force:
        logger.info("%s: skipped (already processed)", path)
        return PollsOutcome(path, "skipped", revision_id)
    if max_revision is not None and revision_id < max_revision and not force:
        logger.warning(
            "snapshot revision %s is older than the loaded revision %s; "
            "ignored (use --force)",
            revision_id,
            max_revision,
        )
        return PollsOutcome(path, "skipped", revision_id)

    if registered is None:
        with session_factory() as session:
            session.add(
                Ingestion(
                    file_path=str(path.resolve().relative_to(raw_dir.resolve())),
                    sha256=digest,
                    size_bytes=path.stat().st_size,
                    source=SOURCE,
                    status="registered",
                )
            )
            session.commit()

    rows = parse_polls(path.read_text(encoding="utf-8"))
    try:
        with session_factory() as session:
            load_polls(session, rows, revision_id)
            session.commit()
    except Exception:
        with session_factory() as session:
            session.execute(
                update(Ingestion)
                .where(Ingestion.sha256 == digest)
                .values(status="failed")
            )
            session.commit()
        raise

    with session_factory() as session:
        session.execute(
            update(Ingestion)
            .where(Ingestion.sha256 == digest)
            .values(status="processed")
        )
        session.commit()
    logger.info("%s: processed revision %s (%d polls)", path, revision_id, len(rows))
    return PollsOutcome(path, "processed", revision_id)


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
    poll_ids = list(session.scalars(insert(Poll).returning(Poll.id), poll_rows))
    result_rows = [
        {
            "poll_id": poll_id,
            "party_id": party_ids[_party_slug(key)],
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


def _snapshot_files(path: Path, raw_dir: Path) -> list[Path]:
    """Snapshot files of ``path`` (a file or a directory), oldest revision first.

    Processing 100 before 101 avoids the guard marking 100 as "older" once 101
    has been loaded.
    """
    files = [path] if path.is_file() else sorted(path.rglob("*.wikitext"))
    raw_root = raw_dir.resolve()
    for file in files:
        if not file.resolve().is_relative_to(raw_root):
            raise IngestError(f"{file} is outside the bronze directory {raw_dir}")
    return sorted(files, key=_revision_id)


def _revision_id(path: Path) -> int:
    """Revision id of a snapshot name (``{revid}.wikitext``), else an error."""
    if path.suffix != ".wikitext" or not path.stem.isdigit():
        raise IngestError(f"snapshot name must be <revision id>.wikitext: {path}")
    return int(path.stem)


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


def _party_slug(key: str) -> str:
    """Result key as a party slug: mapped slugs as is, raw labels slugified."""
    return key if key in _PARTY_NAMES else slugify(key)


def _resolve_parties(session: Session, rows: list[PollRow]) -> dict[str, int]:
    """Get or create the party of every result key (slug -> id).

    A raw label of an unknown column (adapter R8) is provisionally registered
    under its slugified label, with a warning; the party catalogue will cure it.
    """
    keys = {key for row in rows for key in row.results}
    names: dict[str, str] = {}
    for key in keys:
        if key in _PARTY_NAMES:
            names[key] = _PARTY_NAMES[key]
        else:
            logger.warning("unknown party label: %s -> %s", key, slugify(key))
            names[slugify(key)] = key
    existing = {
        party.slug: party
        for party in session.scalars(select(Party).where(Party.slug.in_(names)))
    }
    for slug, name in names.items():
        if slug not in existing:
            existing[slug] = Party(name=name, slug=slug)
            session.add(existing[slug])
    session.flush()
    return {slug: party.id for slug, party in existing.items()}


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
