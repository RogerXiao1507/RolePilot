"""Add structured resume sources, versions, and evidence ingestion state.

Revision ID: 0005_source_evidence
Revises: 0004_resume_library
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_source_evidence"
down_revision: Union[str, None] = "0004_resume_library"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column(
            "structured_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("resumes", sa.Column("source_fingerprint", sa.String(64), nullable=True))
    op.add_column(
        "resumes",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "resumes", sa.Column("object_storage_key", sa.String(512), nullable=True)
    )
    op.execute(
        "UPDATE resumes SET source_fingerprint = md5(extracted_text) || md5(file_name || extracted_text)"
    )
    op.alter_column("resumes", "source_fingerprint", nullable=False)

    op.create_table(
        "resume_source_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(32), nullable=False),
        sa.Column("item_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(240), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_user_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["resume_id", "user_id"],
            ["resumes.id", "resumes.user_id"],
            name="fk_resume_source_items_resume_owner",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_resume_source_items_id_user_id"),
    )
    op.create_index("ix_resume_source_items_user_id", "resume_source_items", ["user_id"])
    op.create_index("ix_resume_source_items_resume_id", "resume_source_items", ["resume_id"])
    op.execute(
        """
        INSERT INTO resume_source_items (
            id, user_id, resume_id, source_version, section, item_type,
            title, content, ordinal, source_metadata, is_user_verified, is_active
        )
        SELECT (
            substr(md5(resume.id::text || resume.user_id::text), 1, 8) || '-' ||
            substr(md5(resume.id::text || resume.user_id::text), 9, 4) || '-4' ||
            substr(md5(resume.id::text || resume.user_id::text), 14, 3) || '-8' ||
            substr(md5(resume.id::text || resume.user_id::text), 18, 3) || '-' ||
            substr(md5(resume.id::text || resume.user_id::text), 21, 12)
        )::uuid,
            resume.user_id,
            resume.id,
            resume.version,
            'other',
            'document',
            resume.label,
            resume.extracted_text,
            0,
            '{"fallback":"raw_extracted_text"}'::jsonb,
            true,
            true
        FROM resumes AS resume
        """
    )
    op.execute('ALTER TABLE "resume_source_items" ENABLE ROW LEVEL SECURITY')
    op.execute(
        'CREATE POLICY "resume_source_items_owner_isolation" ON "resume_source_items" '
        "USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid) "
        "WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)"
    )

    op.add_column("project_evidence", sa.Column("outcome", sa.Text(), nullable=True))
    op.add_column("project_evidence", sa.Column("start_date", sa.String(40), nullable=True))
    op.add_column("project_evidence", sa.Column("end_date", sa.String(40), nullable=True))
    op.add_column(
        "project_evidence",
        sa.Column(
            "links",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.add_column(
        "project_evidence",
        sa.Column(
            "verified_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "project_evidence",
        sa.Column(
            "ai_suggested_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "project_evidence",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "project_evidence", sa.Column("content_fingerprint", sa.String(64), nullable=True)
    )
    op.add_column(
        "project_evidence",
        sa.Column(
            "ingestion_status",
            sa.String(20),
            nullable=False,
            server_default="ready",
        ),
    )
    op.add_column("project_evidence", sa.Column("ingestion_error", sa.Text(), nullable=True))
    op.add_column(
        "project_evidence",
        sa.Column("resume_source_item_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "project_evidence",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        """
        UPDATE project_evidence
        SET content_fingerprint = md5(title || category || description)
                                || md5(COALESCE(array_to_string(skills, ','), ''))
        """
    )
    op.alter_column("project_evidence", "content_fingerprint", nullable=False)
    op.create_check_constraint(
        "ck_project_evidence_ingestion_status",
        "project_evidence",
        "ingestion_status IN ('pending', 'ready', 'failed')",
    )
    op.create_foreign_key(
        "fk_project_evidence_resume_source_owner",
        "project_evidence",
        "resume_source_items",
        ["resume_source_item_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    chunk_columns = (
        sa.Column("source_version", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(40), nullable=True),
        sa.Column("title", sa.String(240), nullable=True),
        sa.Column("dates", sa.String(100), nullable=True),
        sa.Column("skills", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("embedding_model", sa.String(80), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
    )
    for column in chunk_columns:
        op.add_column("project_evidence_chunks", column)
    op.execute(
        """
        UPDATE project_evidence_chunks AS chunk
        SET source_version = evidence.version,
            section = evidence.category,
            title = evidence.title,
            dates = NULLIF(concat_ws(' to ', evidence.start_date, evidence.end_date), ''),
            skills = evidence.skills,
            embedding_model = 'text-embedding-3-small',
            content_hash = md5(chunk.chunk_text) || md5(chunk.chunk_type || chunk.chunk_text)
        FROM project_evidence AS evidence
        WHERE evidence.id = chunk.project_evidence_id
          AND evidence.user_id = chunk.user_id
        """
    )
    for column_name in (
        "source_version",
        "section",
        "title",
        "skills",
        "embedding_model",
        "content_hash",
    ):
        op.alter_column("project_evidence_chunks", column_name, nullable=False)

    artifact_tables = (
        "application_resume_matches",
        "application_tailored_resumes",
        "application_full_resume_drafts",
    )
    for table_name in artifact_tables:
        op.add_column(
            table_name,
            sa.Column("resume_version", sa.Integer(), nullable=False, server_default="1"),
        )
        op.add_column(
            table_name,
            sa.Column(
                "is_stale", sa.Boolean(), nullable=False, server_default=sa.text("false")
            ),
        )
        op.execute(
            f"""
            UPDATE {table_name} AS artifact
            SET resume_version = resume.version
            FROM resumes AS resume
            WHERE resume.id = artifact.resume_id
              AND resume.user_id = artifact.user_id
            """
        )


def downgrade() -> None:
    for table_name in (
        "application_full_resume_drafts",
        "application_tailored_resumes",
        "application_resume_matches",
    ):
        op.drop_column(table_name, "is_stale")
        op.drop_column(table_name, "resume_version")

    for column_name in (
        "content_hash",
        "embedding_model",
        "skills",
        "dates",
        "title",
        "section",
        "source_version",
    ):
        op.drop_column("project_evidence_chunks", column_name)

    op.drop_constraint(
        "fk_project_evidence_resume_source_owner",
        "project_evidence",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_project_evidence_ingestion_status",
        "project_evidence",
        type_="check",
    )
    for column_name in (
        "updated_at",
        "resume_source_item_id",
        "ingestion_error",
        "ingestion_status",
        "content_fingerprint",
        "version",
        "ai_suggested_metrics",
        "verified_metrics",
        "links",
        "end_date",
        "start_date",
        "outcome",
    ):
        op.drop_column("project_evidence", column_name)

    op.execute(
        'DROP POLICY IF EXISTS "resume_source_items_owner_isolation" ON "resume_source_items"'
    )
    op.execute('ALTER TABLE "resume_source_items" DISABLE ROW LEVEL SECURITY')
    op.drop_index("ix_resume_source_items_resume_id", table_name="resume_source_items")
    op.drop_index("ix_resume_source_items_user_id", table_name="resume_source_items")
    op.drop_table("resume_source_items")

    op.drop_column("resumes", "object_storage_key")
    op.drop_column("resumes", "version")
    op.drop_column("resumes", "source_fingerprint")
    op.drop_column("resumes", "structured_data")
