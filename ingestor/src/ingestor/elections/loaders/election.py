"""Bronze loader: discover, register and track one election's source files.

Contract (see docs/ingestor/ingesta.md, «Comportamiento de ingest»):

- Bronze: every file read is registered in ``bronze.ingestion`` with its
  sha256; a file already registered is not re-registered.
- Status: ``registered`` -> ``processed`` | ``failed``; a directory whose
  files are all ``processed`` is skipped unless ``force``.
- Silver: ``ingestor.elections.loaders.silver`` loads the facts in the same
  run; if it fails, the files are marked ``failed``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from ingestor.bronze import find_registered, mark, register, sha256
from ingestor.elections.adapters import CongresoAdapter, adapter_for_directory
from ingestor.elections.loaders.silver import load_election
from ingestor.elections.parsers import file02
from ingestor.errors import IngestError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestOutcome:
    directory: Path
    status: str  # processed | skipped | failed
    election: str


def ingest_path(
    session_factory: sessionmaker,
    path: Path,
    raw_dir: Path,
    force: bool = False,
) -> list[IngestOutcome]:
    """Ingest one election directory, or every election under a root."""
    if not path.exists():
        raise IngestError(f"path does not exist: {path}")
    if any(path.glob("*.DAT")):
        directories = [path]
    else:
        directories = sorted(
            child
            for child in path.iterdir()
            if child.is_dir() and any(child.glob("*.DAT"))
        )
    if not directories:
        raise IngestError(f"no election directories with .DAT files under {path}")

    outcomes: list[IngestOutcome] = []
    for directory in directories:
        try:
            adapter = adapter_for_directory(directory)
            outcomes.append(
                ingest_directory(session_factory, adapter, directory, raw_dir, force)
            )
        except IngestError as error:
            logger.error("%s: %s", directory, error)
            outcomes.append(IngestOutcome(directory, "failed", "-"))
    return outcomes


def ingest_directory(
    session_factory: sessionmaker,
    adapter: CongresoAdapter,
    directory: Path,
    raw_dir: Path,
    force: bool = False,
) -> IngestOutcome:
    """Register and load one election directory into silver."""
    files = adapter.find_files(directory)
    missing = [kind for kind in adapter.required_file_kinds if kind not in files]
    if missing:
        raise IngestError(f"{directory}: missing required files: {', '.join(missing)}")
    raw_root = raw_dir.resolve()
    for path in files.values():
        if not path.resolve().is_relative_to(raw_root):
            raise IngestError(f"{path} is outside the bronze directory {raw_dir}")

    identifications = file02.parse(files["02"])
    if not identifications:
        raise IngestError(f"{files['02']}: no identification record")
    if len(identifications) > 1:
        logger.warning(
            "%s: %d identification records, using the first",
            files["02"],
            len(identifications),
        )
    identification = identifications[0]
    label = f"{adapter.election_type} {identification.election_date.isoformat()}"

    digests = {kind: sha256(path) for kind, path in files.items()}
    with session_factory() as session:
        registered = find_registered(session, digests.values())
    already_processed = all(
        digest in registered and registered[digest].status == "processed"
        for digest in digests.values()
    )
    if already_processed and not force:
        logger.info("%s: skipped (%s already processed)", directory, label)
        return IngestOutcome(directory, "skipped", label)

    new_files = {
        path: digests[kind]
        for kind, path in files.items()
        if digests[kind] not in registered
    }
    if new_files:
        with session_factory() as session:
            register(session, new_files, raw_root, adapter.source)
            session.commit()

    try:
        with session_factory() as session:
            load_election(session, adapter, files, identification)
            session.commit()
    except Exception:
        with session_factory() as session:
            mark(session, digests.values(), "failed")
            session.commit()
        raise

    with session_factory() as session:
        mark(session, digests.values(), "processed")
        session.commit()
    logger.info("%s: processed %s (%d files)", directory, label, len(files))
    return IngestOutcome(directory, "processed", label)
