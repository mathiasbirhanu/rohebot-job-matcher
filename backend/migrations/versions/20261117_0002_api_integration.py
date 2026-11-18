"""Add persistent sessions and application records.

Revision ID: 20261117_0002
Revises: 20261117_0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261117_0002"
down_revision = "20261117_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidate_profiles",
        sa.Column("profile_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("status", sa.String(length=30), server_default="Unverified", nullable=False),
    )
    op.add_column("employer_profiles", sa.Column("phone", sa.String(length=40)))
    op.add_column(
        "employer_profiles",
        sa.Column("status", sa.String(length=30), server_default="Pending OTP", nullable=False),
    )
    op.add_column(
        "employer_profiles",
        sa.Column("profile_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table(
        "account_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_account_verifications_user_id", "account_verifications", ["user_id"])
    op.create_table(
        "candidate_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("token_hash", sa.String(length=64), unique=True, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "candidate_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("owner_id", "category", "file_name", name="uq_candidate_documents_owner_category_name"),
    )
    op.create_index("ix_candidate_documents_owner_id", "candidate_documents", ["owner_id"])
    op.create_table(
        "application_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("resource", sa.String(length=40), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_application_records_resource", "application_records", ["resource"])
    op.create_index("ix_application_records_owner_id", "application_records", ["owner_id"])
    op.create_table(
        "email_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("link", sa.String(length=1000)),
        sa.Column("opened", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_outbox_recipient", "email_outbox", ["recipient"])
    op.create_table(
        "trainer_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=180), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("training_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("invitation_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("profile_created", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("phone", sa.String(length=40)),
        sa.Column("verify_token_hash", sa.String(length=64), unique=True),
        sa.Column("verify_expires_at", sa.DateTime(timezone=True)),
        sa.Column("invite_token_hash", sa.String(length=64), unique=True),
        sa.Column("invite_expires_at", sa.DateTime(timezone=True)),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trainer_registrations_email", "trainer_registrations", ["email"], unique=True)
    op.create_table(
        "trainer_qr_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("trainer_qr_settings")
    op.drop_index("ix_trainer_registrations_email", table_name="trainer_registrations")
    op.drop_table("trainer_registrations")
    op.drop_index("ix_email_outbox_recipient", table_name="email_outbox")
    op.drop_table("email_outbox")
    op.drop_index("ix_candidate_documents_owner_id", table_name="candidate_documents")
    op.drop_table("candidate_documents")
    op.drop_table("candidate_invitations")
    op.drop_index("ix_application_records_owner_id", table_name="application_records")
    op.drop_index("ix_application_records_resource", table_name="application_records")
    op.drop_table("application_records")
    op.drop_index("ix_account_verifications_user_id", table_name="account_verifications")
    op.drop_table("account_verifications")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_column("employer_profiles", "profile_data")
    op.drop_column("employer_profiles", "status")
    op.drop_column("employer_profiles", "phone")
    op.drop_column("candidate_profiles", "status")
    op.drop_column("candidate_profiles", "profile_data")
