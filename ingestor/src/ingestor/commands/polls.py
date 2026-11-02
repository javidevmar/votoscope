"""``ingestor fetch-polls`` and ``ingestor ingest-polls``: polls snapshots."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from ingestor.polls.fetch import DEFAULT_PAGE, fetch_snapshot
from ingestor.polls.loaders.polls import ingest_polls_path
from ingestor.settings import Settings

logger = logging.getLogger(__name__)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    fetch = subparsers.add_parser(
        "fetch-polls",
        help="download the fixed-revision wikitext snapshot of the polls page",
    )
    fetch.add_argument(
        "--page",
        default=DEFAULT_PAGE,
        help="Wikipedia page title (default: 2026 general election)",
    )

    polls = subparsers.add_parser(
        "ingest-polls",
        help="ingest polls snapshots into silver (skips processed; --force reloads)",
    )
    polls.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=None,
        help="snapshot file or directory (default: RAW_DIR/polls)",
    )
    polls.add_argument(
        "--force",
        action="store_true",
        help="reload snapshots even if processed or older than the loaded revision",
    )


def run_fetch(args: argparse.Namespace, *, settings: Settings) -> int:
    fetch_snapshot(args.page, raw_dir=settings.raw_dir)
    return 0


def run_ingest(
    args: argparse.Namespace,
    *,
    session_factory: sessionmaker,
    settings: Settings,
) -> int:
    outcomes = ingest_polls_path(
        session_factory,
        args.path or settings.raw_dir / "polls",
        settings.raw_dir,
        force=args.force,
    )
    for outcome in outcomes:
        logger.info("%s: %s", outcome.file, outcome.status)
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0
