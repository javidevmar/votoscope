"""``ingestor refresh-gold``: refresh the gold materialized views."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from sqlalchemy.orm import sessionmaker

RefreshGold = Callable[..., None]


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "refresh-gold",
        help="refresh the gold materialized views (--concurrently avoids read locks)",
    )
    parser.add_argument(
        "--concurrently",
        action="store_true",
        help="refresh with REFRESH MATERIALIZED VIEW CONCURRENTLY",
    )


def run(
    args: argparse.Namespace,
    *,
    session_factory: sessionmaker,
    refresh_gold: RefreshGold,
) -> int:
    refresh_gold(session_factory, concurrently=args.concurrently)
    return 0
