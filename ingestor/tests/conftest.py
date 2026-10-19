"""Shared test fixtures: a session-scoped throwaway PostgreSQL database.

The polls loader needs a real database (transactions, CHECK constraints,
foreign keys, NUMERIC), so tests run against a temporary database
(``votoscope_test_<pid>``) created from ``settings.database_url``. Only the
maintenance database (``postgres``) and the temporary one are used: the
application database and its schemas are never touched. Without a reachable
Postgres the database tests skip (CI provides the service).
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from ingestor.models import Base
from ingestor.settings import settings


def _temp_database_url() -> URL:
    """URL of this session's throwaway database, next to the configured one."""
    url = make_url(settings.database_url)
    return url.set(database=f"votoscope_test_{os.getpid()}")


def _drop_database(engine, database: str) -> None:
    with engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))


@pytest.fixture(scope="session")
def polls_engine():
    """Engine on a fresh temporary database with the real ``bronze``/``silver``."""
    url = _temp_database_url()
    database = url.database
    maintenance = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        with maintenance.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        maintenance.dispose()
        pytest.skip("Postgres is not reachable (docker compose up -d --wait)")

    try:
        _drop_database(maintenance, database)
        with maintenance.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        maintenance.dispose()

    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE SCHEMA bronze"))
            connection.execute(text("CREATE SCHEMA silver"))
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        cleanup = create_engine(
            url.set(database="postgres"), isolation_level="AUTOCOMMIT"
        )
        try:
            _drop_database(cleanup, database)
        finally:
            cleanup.dispose()


@pytest.fixture()
def db(polls_engine):
    """Session factory against the temporary database, emptied before each test."""
    factory = sessionmaker(bind=polls_engine, expire_on_commit=False)
    with factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    return factory
