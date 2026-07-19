"""Add saved job searches, discovery catalog, provenance, and user actions.

Revision ID: 0006_job_discovery
Revises: 0005_source_evidence
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_job_discovery"
down_revision: Union[str, None] = "0005_source_evidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enable_owner_rls(table_name: str) -> None:
    op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
    op.execute(
        f'CREATE POLICY "{table_name}_owner_isolation" ON "{table_name}" '
        "USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid) "
        "WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)"
    )


def upgrade() -> None:
    op.create_table(
        "discovered_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(240), nullable=False),
        sa.Column("company_normalized", sa.String(240), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("title_normalized", sa.String(300), nullable=False),
        sa.Column("location", sa.String(400), nullable=True),
        sa.Column("location_normalized", sa.String(400), nullable=True),
        sa.Column("workplace_type", sa.String(20), nullable=True),
        sa.Column("employment_type", sa.String(40), nullable=True),
        sa.Column("seniority_level", sa.String(40), nullable=True),
        sa.Column("industry", sa.String(120), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(3), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("description_fingerprint", sa.String(64), nullable=False),
        sa.Column("deduplication_key", sa.String(64), nullable=False),
        sa.Column(
            "keywords",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("source_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('active', 'removed', 'error')",
            name="ck_discovered_jobs_verification_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_discovered_jobs_active_posted",
        "discovered_jobs",
        ["verification_status", "source_posted_at"],
    )
    op.create_index(
        "ix_discovered_jobs_deduplication_key",
        "discovered_jobs",
        ["deduplication_key"],
    )

    op.create_table(
        "job_source_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("discovered_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_name", sa.String(40), nullable=False),
        sa.Column("external_job_id", sa.String(240), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=False),
        sa.Column("source_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_verified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("raw_payload_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "verification_status IN ('active', 'removed', 'error')",
            name="ck_job_source_postings_verification_status",
        ),
        sa.ForeignKeyConstraint(
            ["discovered_job_id"], ["discovered_jobs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name", "external_job_id", name="uq_job_source_external_id"
        ),
    )
    op.create_index(
        "ix_job_source_postings_job", "job_source_postings", ["discovered_job_id"]
    )

    op.create_table(
        "job_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("target_titles", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "adjacent_titles",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "seniority_levels",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "employment_types",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "locations",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "workplace_types",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column(
            "salary_currency", sa.String(3), nullable=False, server_default="USD"
        ),
        sa.Column(
            "industries",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "required_keywords",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "excluded_keywords",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "excluded_companies",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("recency", sa.String(8), nullable=False, server_default="7d"),
        sa.Column(
            "notification_frequency",
            sa.String(12),
            nullable=False,
            server_default="off",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "recency IN ('24h', '7d', '14d', '30d', 'all')",
            name="ck_job_searches_recency",
        ),
        sa.CheckConstraint(
            "notification_frequency IN ('off', 'daily', 'weekly')",
            name="ck_job_searches_notification_frequency",
        ),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_job_searches_salary_range",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["resume_id", "user_id"],
            ["resumes.id", "resumes.user_id"],
            name="fk_job_searches_resume_owner",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_job_searches_id_user_id"),
    )
    op.create_index("ix_job_searches_user_id", "job_searches", ["user_id"])
    _enable_owner_rls("job_searches")

    op.create_table(
        "job_discovery_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("discovered_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "state IN ('saved', 'dismissed', 'duplicate', 'converted')",
            name="ck_job_discovery_actions_state",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["discovered_job_id"], ["discovered_jobs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            name="fk_job_discovery_actions_application_owner",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "discovered_job_id", name="uq_job_discovery_actions_user_job"
        ),
    )
    op.create_index(
        "ix_job_discovery_actions_user_id", "job_discovery_actions", ["user_id"]
    )
    op.create_index(
        "ix_job_discovery_actions_discovered_job_id",
        "job_discovery_actions",
        ["discovered_job_id"],
    )
    _enable_owner_rls("job_discovery_actions")


def downgrade() -> None:
    for table_name in ("job_discovery_actions", "job_searches"):
        op.execute(
            f'DROP POLICY IF EXISTS "{table_name}_owner_isolation" ON "{table_name}"'
        )
        op.execute(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY')
    op.drop_table("job_discovery_actions")
    op.drop_table("job_searches")
    op.drop_table("job_source_postings")
    op.drop_table("discovered_jobs")
