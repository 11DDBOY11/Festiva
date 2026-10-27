"""Create full schema: vendor_directory, knowledge_chunks, budget_rules,
plan_versions, proposed_changes, event_vendors, expenses, tasks, guests.

Revision ID: 003_full_schema
Revises: 002_refresh_tokens
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003_full_schema"
down_revision: str | None = "002_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # --- vendor_directory ---
    op.create_table(
        "vendor_directory",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("area", sa.String(100), nullable=False),
        sa.Column("city", sa.String(100), nullable=False, server_default="Mangaluru"),
        sa.Column("capacity_min", sa.Integer(), nullable=True),
        sa.Column("capacity_max", sa.Integer(), nullable=True),
        sa.Column("price_low", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_high", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_unit", sa.String(30), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("verified_on", sa.Date(), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("contact", JSONB(), nullable=True),
    )
    op.create_index("ix_vendor_directory_category", "vendor_directory", ["category"])
    op.create_index("ix_vendor_directory_area", "vendor_directory", ["area"])
    op.create_index("ix_vendor_directory_city", "vendor_directory", ["city"])

    # --- knowledge_chunks ---
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("ref_id", sa.Uuid(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("embedding", Vector(768), nullable=True),
    )

    # --- budget_rules ---
    op.create_table(
        "budget_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("tier", sa.String(30), nullable=False, server_default="standard"),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("share_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("per_guest_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_amount", sa.Numeric(12, 2), nullable=True),
    )
    op.create_index("ix_budget_rules_event_type", "budget_rules", ["event_type"])
    op.create_index("ix_budget_rules_tier", "budget_rules", ["tier"])

    # --- plan_versions ---
    op.create_table(
        "plan_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("plan", JSONB(), nullable=False),
        sa.Column("created_by", sa.String(20), nullable=False, server_default="ai"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", "version", name="uq_plan_versions_event_version"),
    )
    op.create_index("ix_plan_versions_event_id", "plan_versions", ["event_id"])

    # --- proposed_changes ---
    op.create_table(
        "proposed_changes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("diff", JSONB(), nullable=False),
        sa.Column("budget_impact", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_proposed_changes_event_id", "proposed_changes", ["event_id"])

    # --- event_vendors ---
    op.create_table(
        "event_vendors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_id",
            sa.Uuid(),
            sa.ForeignKey("vendor_directory.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("custom_name", sa.String(255), nullable=True),
        sa.Column("quoted_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="shortlisted"),
    )
    op.create_index("ix_event_vendors_event_id", "event_vendors", ["event_id"])

    # --- expenses ---
    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column(
            "vendor_id",
            sa.Uuid(),
            sa.ForeignKey("vendor_directory.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_expenses_event_id", "expenses", ["event_id"])

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="todo"),
    )
    op.create_index("ix_tasks_event_id", "tasks", ["event_id"])

    # --- guests ---
    op.create_table(
        "guests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("rsvp", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("dietary_notes", sa.Text(), nullable=True),
        sa.Column("plus_ones", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_guests_event_id", "guests", ["event_id"])


def downgrade() -> None:
    op.drop_table("guests")
    op.drop_table("tasks")
    op.drop_table("expenses")
    op.drop_table("event_vendors")
    op.drop_table("proposed_changes")
    op.drop_table("plan_versions")
    op.drop_table("budget_rules")
    op.drop_table("knowledge_chunks")
    op.drop_table("vendor_directory")
