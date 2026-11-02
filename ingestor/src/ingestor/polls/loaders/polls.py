"""Bronze loader for the Wikipedia polls snapshots: registry + revision guard.

Contract (see docs/ingestor/ingesta.md, «Comportamiento de ingest-polls»):

- Bronze: the snapshot is registered in ``bronze.ingestion`` with its sha256
  (source ``wikipedia-en``); a snapshot already ``processed`` is skipped.
- Revision guard: a snapshot older than ``max(poll.revision_id)`` is ignored
  with a warning unless ``force``.
- Silver: ``ingestor.polls.loaders.silver`` replaces ``poll``/``poll_result``
  and links polls to elections in the same run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from ingestor.bronze import find_registered, mark, register, sha256
from ingestor.errors import IngestError
from ingestor.models import Poll
from ingestor.polls import SOURCE
from ingestor.polls.adapters.wikipedia_polls import parse_polls
from ingestor.polls.loaders.silver import load_polls, resolve_poll_elections

logger = logging.getLogger(__name__)


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
        registered = find_registered(session, [digest]).get(digest)
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
            register(session, {path: digest}, raw_dir, SOURCE)
            session.commit()

    rows = parse_polls(path.read_text(encoding="utf-8"))
    try:
        with session_factory() as session:
            load_polls(session, rows, revision_id)
            session.commit()
    except Exception:
        with session_factory() as session:
            mark(session, [digest], "failed")
            session.commit()
        raise

    with session_factory() as session:
        mark(session, [digest], "processed")
        session.commit()
    logger.info("%s: processed revision %s (%d polls)", path, revision_id, len(rows))
    return PollsOutcome(path, "processed", revision_id)


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
