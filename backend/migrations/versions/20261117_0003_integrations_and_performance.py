"""Add delivery state and query indexes for integrations.

Revision ID: 20261117_0003
Revises: 20261117_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20261117_0003"
down_revision = "20261117_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_outbox",
        sa.Column("delivery_status", sa.String(length=20), server_default="queued", nullable=False),
    )
    op.add_column(
        "email_outbox",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("email_outbox", sa.Column("last_error", sa.Text()))
    op.add_column("email_outbox", sa.Column("sent_at", sa.DateTime(timezone=True)))
    op.create_index("ix_email_outbox_created_at", "email_outbox", ["created_at"])
    op.create_index(
        "ix_candidate_profiles_search",
        "candidate_profiles",
        ["verified", "availability", "professional_category", "city"],
    )
    op.create_index(
        "ix_application_records_owner_resource_created_at",
        "application_records",
        ["owner_id", "resource", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_application_records_owner_resource_created_at", table_name="application_records")
    op.drop_index("ix_candidate_profiles_search", table_name="candidate_profiles")
    op.drop_index("ix_email_outbox_created_at", table_name="email_outbox")
    op.drop_column("email_outbox", "sent_at")
    op.drop_column("email_outbox", "last_error")
    op.drop_column("email_outbox", "attempt_count")
    op.drop_column("email_outbox", "delivery_status")
