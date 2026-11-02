"""Bronze registry: immutable source files and their ingestion status.

Every file read by a loader is recorded once in ``bronze.ingestion`` with its
sha256 and a status (``registered`` -> ``processed`` | ``failed``). The
registry is shared by the election and polls loaders and knows nothing about
either source format.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ingestor.models import Ingestion

_CHUNK = 1024 * 1024


def sha256(path: Path) -> str:
    """Hexadecimal sha256 of ``path``, read in 1 MiB chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def find_registered(session: Session, digests: Iterable[str]) -> dict[str, Ingestion]:
    """Existing bronze rows by sha256."""
    values = list(digests)
    if not values:
        return {}
    return {
        row.sha256: row
        for row in session.scalars(
            select(Ingestion).where(Ingestion.sha256.in_(values))
        )
    }


def register(
    session: Session,
    files: dict[Path, str],
    raw_dir: Path,
    source: str,
) -> None:
    """Add the given files to bronze (no commit), with paths relative to ``raw_dir``."""
    root = raw_dir.resolve()
    for path, digest in files.items():
        session.add(
            Ingestion(
                file_path=str(path.resolve().relative_to(root)),
                sha256=digest,
                size_bytes=path.stat().st_size,
                source=source,
                status="registered",
            )
        )


def mark(session: Session, digests: Iterable[str], status: str) -> None:
    """Set the status of the given bronze rows (no commit)."""
    session.execute(
        update(Ingestion)
        .where(Ingestion.sha256.in_(list(digests)))
        .values(status=status)
    )
