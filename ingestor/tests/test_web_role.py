"""Read-only web role: migration source and live grants.

The source test is hermetic (reads the migration file). The live tests check
the real ``votoscope_web`` role against ``settings.database_url`` and skip
without a reachable Postgres, the ``gold`` schema or the applied migration.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from ingestor.settings import settings

ROLE = "votoscope_web"
VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _migration_source() -> str:
    pattern = "*_web_readonly_role.py"
    migrations = sorted(VERSIONS_DIR.glob(pattern))
    assert len(migrations) == 1, f"expected one {pattern} migration"
    return migrations[0].read_text()


def _real_connection():
    """Connection over ``settings.database_url``; skip when Postgres is down."""
    engine = create_engine(settings.database_url)
    try:
        connection = engine.connect()
        connection.execute(text("SELECT 1"))
    except OperationalError:
        engine.dispose()
        pytest.skip("Postgres is not reachable (docker compose up -d --wait)")
    return engine, connection


@pytest.fixture(scope="module")
def db():
    engine, connection = _real_connection()
    role = connection.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": ROLE}
    ).scalar()
    views = connection.execute(
        text("SELECT to_regclass('gold.election_summary')")
    ).scalar()
    if not views:
        connection.close()
        engine.dispose()
        pytest.skip("gold views are not migrated (uv run alembic upgrade head)")
    if not role:
        connection.close()
        engine.dispose()
        pytest.skip("votoscope_web does not exist (uv run alembic upgrade head)")
    yield connection
    connection.close()
    engine.dispose()


# --- Migration source (hermetic) -------------------------------------------


def test_migration_source_has_no_credentials():  # R9
    source = _migration_source()

    assert "PASSWORD" not in source.upper()
    assert "postgresql://" not in source
    assert "postgres://" not in source


def test_migration_creates_and_drops_the_role():  # R5, R9
    source = _migration_source()

    assert "CREATE ROLE votoscope_web LOGIN" in source
    assert "ALTER DEFAULT PRIVILEGES" in source
    assert "DROP ROLE votoscope_web" in source


# --- Live role and grants ---------------------------------------------------


def test_role_is_login_without_admin_attributes(db):  # R5
    row = db.execute(
        text(
            "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname = :role"
        ),
        {"role": ROLE},
    ).one()

    assert row.rolcanlogin is True
    assert row.rolsuper is False
    assert row.rolcreatedb is False
    assert row.rolcreaterole is False


def test_role_has_usage_and_select_on_every_gold_view(db):  # R6
    assert db.execute(
        text("SELECT has_schema_privilege(:role, 'gold', 'USAGE')"), {"role": ROLE}
    ).scalar()

    missing = db.execute(
        text(
            "SELECT c.relname FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'gold' AND c.relkind = 'v' "
            "AND NOT has_table_privilege(:role, c.oid, 'SELECT')"
        ),
        {"role": ROLE},
    ).scalars()
    assert list(missing) == []


def test_default_privileges_grant_select_on_future_gold_relations(db):  # R7
    grants = db.execute(
        text(
            "SELECT count(*) FROM pg_default_acl d "
            "JOIN pg_namespace n ON n.oid = d.defaclnamespace "
            "JOIN pg_roles owner ON owner.oid = d.defaclrole "
            "CROSS JOIN LATERAL aclexplode(d.defaclacl) acl "
            "JOIN pg_roles grantee ON grantee.oid = acl.grantee "
            "WHERE n.nspname = 'gold' AND d.defaclobjtype = 'r' "
            "AND owner.rolname = current_user "
            "AND grantee.rolname = :role "
            "AND acl.privilege_type = 'SELECT'"
        ),
        {"role": ROLE},
    ).scalar()
    assert grants


def test_role_cannot_read_silver_or_bronze(db):  # R8
    for schema in ("silver", "bronze"):
        assert not db.execute(
            text("SELECT has_schema_privilege(:role, :schema, 'USAGE')"),
            {"role": ROLE, "schema": schema},
        ).scalar(), f"{ROLE} must not have USAGE on {schema}"

        tables = db.execute(
            text(
                "SELECT count(*) FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = :schema AND c.relkind IN ('r', 'p', 'v', 'm') "
                "AND has_table_privilege(:role, c.oid, 'SELECT')"
            ),
            {"role": ROLE, "schema": schema},
        ).scalar()
        assert tables == 0, f"{ROLE} must not SELECT from {schema}"


def test_role_cannot_write_or_create_in_gold(db):  # R8
    assert not db.execute(
        text("SELECT has_schema_privilege(:role, 'gold', 'CREATE')"), {"role": ROLE}
    ).scalar()

    for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
        count = db.execute(
            text(
                "SELECT count(*) FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'gold' AND c.relkind = 'v' "
                "AND has_table_privilege(:role, c.oid, :privilege)"
            ),
            {"role": ROLE, "privilege": privilege},
        ).scalar()
        assert count == 0, f"{ROLE} must not have {privilege} on gold"
