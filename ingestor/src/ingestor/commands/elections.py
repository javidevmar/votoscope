"""``ingestor ingest``: one election directory or a root with several."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from ingestor.elections.loaders.election import ingest_path
from ingestor.settings import Settings

logger = logging.getLogger(__name__)

RefreshGold = Callable[[sessionmaker], None]


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "ingest",
        help="ingest one election directory or a root with several (skips files already processed)",
    )
    parser.add_argument(
        "path", type=Path, help="election directory or root with several"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-ingest even if all files were already processed",
    )


def run(
    args: argparse.Namespace,
    *,
    session_factory: sessionmaker,
    settings: Settings,
    refresh_gold: RefreshGold,
) -> int:
    outcomes = ingest_path(
        session_factory, args.path, settings.raw_dir, force=args.force
    )
    # One refresh per run, outside the per-election loop: only when some
    # election actually wrote facts.
    if any(outcome.status == "processed" for outcome in outcomes):
        refresh_gold(session_factory)

    for outcome in outcomes:
        logger.info("%s: %s", outcome.directory, outcome.status)
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0
