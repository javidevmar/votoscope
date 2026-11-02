"""Command line entrypoints: ``ingestor load-geography``, ``ingestor ingest``,
``ingestor fetch-polls``, ``ingestor ingest-polls`` and ``ingestor refresh-gold``.

Each subcommand lives in ``ingestor.commands``; this module only wires the
parser and injects the shared dependencies.
"""

from __future__ import annotations

import argparse
import logging

from ingestor.commands import elections, geography, gold, polls
from ingestor.db import SessionLocal
from ingestor.errors import IngestError
from ingestor.gold import refresh_gold
from ingestor.logging import configure_logging
from ingestor.settings import settings

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="ingestor", description="Votoscope ingestor")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (geography, elections, polls, gold):
        command.add_parser(subparsers)

    args = parser.parse_args(argv)
    try:
        if args.command == "load-geography":
            return geography.run(args, session_factory=SessionLocal, settings=settings)
        if args.command == "ingest":
            return elections.run(
                args,
                session_factory=SessionLocal,
                settings=settings,
                refresh_gold=refresh_gold,
            )
        if args.command == "fetch-polls":
            return polls.run_fetch(args, settings=settings)
        if args.command == "ingest-polls":
            return polls.run_ingest(
                args, session_factory=SessionLocal, settings=settings
            )
        if args.command == "refresh-gold":
            return gold.run(
                args, session_factory=SessionLocal, refresh_gold=refresh_gold
            )
    except IngestError as error:
        logger.error("%s", error)
        return 1
    raise AssertionError(f"unknown command: {args.command}")
