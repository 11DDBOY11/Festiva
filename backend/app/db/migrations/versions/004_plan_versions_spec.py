"""Align plan_versions to exact spec, ensure event and change versioning, add vendor sample flag.

Revision ID: 004_plan_versions_spec
Revises: 003_full_schema
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_plan_versions_spec"
down_revision: str | None = "003_full_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop any legacy view columns from plan_versions if present
    op.execute("ALTER TABLE plan_versions DROP COLUMN IF EXISTS budget_breakdown;")
    op.execute("ALTER TABLE plan_versions DROP COLUMN IF EXISTS timeline;")
    op.execute("ALTER TABLE plan_versions DROP COLUMN IF EXISTS vendor_allocations;")
    op.execute("ALTER TABLE plan_versions DROP COLUMN IF EXISTS status;")

    # 2. Ensure created_by is TEXT
    op.alter_column(
        "plan_versions",
        "created_by",
        existing_type=sa.String(length=20),
        type_=sa.Text(),
        existing_nullable=False,
        existing_server_default="ai",
    )

    # 3. Add sample flag to vendor_directory if not exists
    op.execute(
        "ALTER TABLE vendor_directory ADD COLUMN IF NOT EXISTS "
        "sample BOOLEAN NOT NULL DEFAULT TRUE;"
    )

    # 4. Ensure events.current_version and proposed_changes.base_version exist
    op.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS current_version INTEGER DEFAULT 1;")
    op.execute(
        "ALTER TABLE proposed_changes ADD COLUMN IF NOT EXISTS "
        "base_version INTEGER DEFAULT 1 NOT NULL;"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE vendor_directory DROP COLUMN IF EXISTS sample;")
