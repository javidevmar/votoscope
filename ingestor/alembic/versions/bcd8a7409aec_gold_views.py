"""gold views

Revision ID: bcd8a7409aec
Revises: 368c5831061d
Create Date: 2026-10-29 22:29:38.965423

"""

from collections.abc import Sequence

from alembic import op

from ingestor.gold import view_ddl

# revision identifiers, used by Alembic.
revision: str = "bcd8a7409aec"
down_revision: str | Sequence[str] | None = "368c5831061d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the gold schema and its read-only views."""
    op.execute("CREATE SCHEMA IF NOT EXISTS gold")
    for statement in view_ddl().values():
        op.execute(statement)


def downgrade() -> None:
    """Drop the gold views and the schema."""
    for name in reversed(list(view_ddl())):
        op.execute(f"DROP VIEW IF EXISTS gold.{name}")
    op.execute("DROP SCHEMA IF EXISTS gold")
