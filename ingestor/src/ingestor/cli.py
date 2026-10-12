"""Command line entrypoints: ``ingestor load-geography`` and ``ingestor ingest``."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ingestor.db import SessionLocal
from ingestor.errors import IngestError
from ingestor.loaders.election import ingest_path
from ingestor.loaders.geography import load_geography
from ingestor.logging import configure_logging
from ingestor.settings import settings

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="ingestor", description="Votoscope ingestor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "load-geography",
        help="load the INE gazetteer (CCAA, provinces, municipalities) into silver",
    )

    ingest = subparsers.add_parser(
        "ingest",
        help="ingest one election directory or a root with several (skips files already processed)",
    )
    ingest.add_argument(
        "path", type=Path, help="election directory or root with several"
    )
    ingest.add_argument(
        "--force",
        action="store_true",
        help="re-ingest even if all files were already processed",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "load-geography":
            load_geography(SessionLocal, settings.ine_dir)
            return 0
        outcomes = ingest_path(
            SessionLocal, args.path, settings.raw_dir, force=args.force
        )
    except IngestError as error:
        logger.error("%s", error)
        return 1

    for outcome in outcomes:
        logger.info("%s: %s", outcome.directory, outcome.status)
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0
