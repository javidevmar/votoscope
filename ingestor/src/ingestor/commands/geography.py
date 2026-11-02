"""``ingestor load-geography``: INE gazetteer -> silver."""

from __future__ import annotations

import argparse

from sqlalchemy.orm import sessionmaker

from ingestor.elections.loaders.geography import load_geography
from ingestor.settings import Settings


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    subparsers.add_parser(
        "load-geography",
        help="load the INE gazetteer (CCAA, provinces, municipalities) into silver",
    )


def run(
    args: argparse.Namespace,
    *,
    session_factory: sessionmaker,
    settings: Settings,
) -> int:
    load_geography(session_factory, settings.ine_dir)
    return 0
