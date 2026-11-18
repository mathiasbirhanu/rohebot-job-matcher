"""Create the initial job-matching schema.

Revision ID: 20261117_0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261117_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('candidate', 'employer', 'admin')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "candidate_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=180), nullable=False),
        sa.Column("phone", sa.String(length=40)),
        sa.Column("professional_category", sa.String(length=120)),
        sa.Column("qualification_level", sa.String(length=120)),
        sa.Column("years_of_experience", sa.Integer(), server_default="0", nullable=False),
        sa.Column("professional_summary", sa.Text()),
        sa.Column("skills", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("city", sa.String(length=120)),
        sa.Column("availability", sa.String(length=40), server_default="Not Available", nullable=False),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "employer_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_name", sa.String(length=180), nullable=False),
        sa.Column("organization_type", sa.String(length=80)),
        sa.Column("city", sa.String(length=120)),
        sa.Column("website", sa.String(length=255)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("employment_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'published', 'closed')", name="ck_jobs_status"),
        sa.ForeignKeyConstraint(["employer_id"], ["employer_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_employer_id", "jobs", ["employer_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "job_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="submitted", nullable=False),
        sa.Column("cover_letter", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('submitted', 'reviewing', 'interview', 'offered', 'rejected', 'withdrawn')",
            name="ck_applications_status",
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_applications_job_candidate"),
    )
    op.create_index("ix_job_applications_job_id", "job_applications", ["job_id"])
    op.create_index("ix_job_applications_candidate_id", "job_applications", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_job_applications_candidate_id", table_name="job_applications")
    op.drop_index("ix_job_applications_job_id", table_name="job_applications")
    op.drop_table("job_applications")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_employer_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("employer_profiles")
    op.drop_table("candidate_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
