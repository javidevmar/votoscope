"""web read-only role

Revision ID: 9f3c2a1b7d40
Revises: bcd8a7409aec
Create Date: 2026-10-29 23:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f3c2a1b7d40"
down_revision: str | Sequence[str] | None = "bcd8a7409aec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create votoscope_web with read-only access to the gold schema."""
    op.execute("CREATE ROLE votoscope_web LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE")
    op.execute("GRANT USAGE ON SCHEMA gold TO votoscope_web")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA gold TO votoscope_web")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA gold "
        "GRANT SELECT ON TABLES TO votoscope_web"
    )


def downgrade() -> None:
    """Revoke the grants and drop the role."""
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA gold "
        "REVOKE SELECT ON TABLES FROM votoscope_web"
    )
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA gold FROM votoscope_web")
    op.execute("REVOKE USAGE ON SCHEMA gold FROM votoscope_web")
    op.execute("DROP ROLE votoscope_web")
