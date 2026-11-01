"""Shared test fixtures: isolated PostgreSQL test schemas.

The polls loader needs a real database (transactions, CHECK constraints,
foreign keys, NUMERIC), so tests run against ``settings.database_url`` with the
``bronze``/``silver`` schemas translated to throwaway test schemas: the
application schemas are never touched. Without a reachable Postgres the
database tests skip (CI provides the service).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from ingestor.gold import view_ddl
from ingestor.models import Base
from ingestor.settings import settings

TEST_SCHEMAS = {
    "bronze": "polls_test_bronze",
    "silver": "polls_test_silver",
    "gold": "polls_test_gold",
}

# The gold views are read-only: they are created from gold.view_ddl(), never
# by create_all, and cannot be emptied between tests.
BASE_TABLES = [
    table for table in Base.metadata.sorted_tables if not table.info.get("view")
]


def _drop_test_schemas(connection) -> None:
    for schema in TEST_SCHEMAS.values():
        connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))


@pytest.fixture(scope="session")
def polls_engine():
    """Engine whose ``bronze``/``silver``/``gold`` schemas point to the test schemas."""
    engine = create_engine(
        settings.database_url,
        execution_options={"schema_translate_map": TEST_SCHEMAS},
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        engine.dispose()
        pytest.skip("Postgres is not reachable (docker compose up -d --wait)")
    with engine.begin() as connection:
        _drop_test_schemas(connection)
        for schema in TEST_SCHEMAS.values():
            connection.execute(text(f"CREATE SCHEMA {schema}"))
    Base.metadata.create_all(engine, tables=BASE_TABLES)
    with engine.begin() as connection:
        for statement in view_ddl(
            gold_schema=TEST_SCHEMAS["gold"], silver_schema=TEST_SCHEMAS["silver"]
        ).values():
            connection.exec_driver_sql(statement)
    yield engine
    with engine.begin() as connection:
        _drop_test_schemas(connection)
    engine.dispose()


@pytest.fixture()
def db(polls_engine):
    """Session factory against the test schemas, emptied before each test."""
    factory = sessionmaker(bind=polls_engine, expire_on_commit=False)
    with factory() as session:
        for table in reversed(BASE_TABLES):
            session.execute(table.delete())
        session.commit()
    return factory
