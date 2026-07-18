"""Baseline the original RolePilot schema.

Revision ID: 0001_initial_schema
Revises: None
"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("role_title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("job_url", sa.String(), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=True),
        sa.Column("preferred_skills", sa.JSON(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("next_steps", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_id", "applications", ["id"])

    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("strengths", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("weaknesses", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("wording_issues", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("missing_metrics", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("suggested_improvements", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resumes_id", "resumes", ["id"])

    op.create_table(
        "project_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("keywords", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("bullet_bank", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_evidence_id", "project_evidence", ["id"])

    op.create_table(
        "project_evidence_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_evidence_id", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_type", sa.String(), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_evidence_id"], ["project_evidence.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_evidence_chunks_id", "project_evidence_chunks", ["id"])
    op.create_index(
        "ix_project_evidence_chunks_project_evidence_id",
        "project_evidence_chunks",
        ["project_evidence_id"],
    )

    op.create_table(
        "application_resume_matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("overall_match_summary", sa.Text(), nullable=False),
        sa.Column("matched_skills", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("missing_skills", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("strengths_for_role", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("improvement_areas", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("suggested_resume_changes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_resume_matches_application_id",
        "application_resume_matches",
        ["application_id"],
        unique=True,
    )
    op.create_index("ix_application_resume_matches_id", "application_resume_matches", ["id"])
    op.create_index(
        "ix_application_resume_matches_resume_id",
        "application_resume_matches",
        ["resume_id"],
    )

    op.create_table(
        "application_tailored_resumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("tailored_summary", sa.Text(), nullable=False),
        sa.Column("tailored_skills", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("tailored_bullets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tailoring_notes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_tailored_resumes_application_id",
        "application_tailored_resumes",
        ["application_id"],
        unique=True,
    )
    op.create_index("ix_application_tailored_resumes_id", "application_tailored_resumes", ["id"])
    op.create_index(
        "ix_application_tailored_resumes_resume_id",
        "application_tailored_resumes",
        ["resume_id"],
    )

    op.create_table(
        "application_full_resume_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("draft_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_full_resume_drafts_application_id",
        "application_full_resume_drafts",
        ["application_id"],
        unique=True,
    )
    op.create_index("ix_application_full_resume_drafts_id", "application_full_resume_drafts", ["id"])
    op.create_index(
        "ix_application_full_resume_drafts_resume_id",
        "application_full_resume_drafts",
        ["resume_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_application_full_resume_drafts_resume_id", table_name="application_full_resume_drafts")
    op.drop_index("ix_application_full_resume_drafts_id", table_name="application_full_resume_drafts")
    op.drop_index(
        "ix_application_full_resume_drafts_application_id",
        table_name="application_full_resume_drafts",
    )
    op.drop_table("application_full_resume_drafts")
    op.drop_index("ix_application_tailored_resumes_resume_id", table_name="application_tailored_resumes")
    op.drop_index("ix_application_tailored_resumes_id", table_name="application_tailored_resumes")
    op.drop_index(
        "ix_application_tailored_resumes_application_id",
        table_name="application_tailored_resumes",
    )
    op.drop_table("application_tailored_resumes")
    op.drop_index("ix_application_resume_matches_resume_id", table_name="application_resume_matches")
    op.drop_index("ix_application_resume_matches_id", table_name="application_resume_matches")
    op.drop_index(
        "ix_application_resume_matches_application_id",
        table_name="application_resume_matches",
    )
    op.drop_table("application_resume_matches")
    op.drop_index(
        "ix_project_evidence_chunks_project_evidence_id",
        table_name="project_evidence_chunks",
    )
    op.drop_index("ix_project_evidence_chunks_id", table_name="project_evidence_chunks")
    op.drop_table("project_evidence_chunks")
    op.drop_index("ix_project_evidence_id", table_name="project_evidence")
    op.drop_table("project_evidence")
    op.drop_index("ix_resumes_id", table_name="resumes")
    op.drop_table("resumes")
    op.drop_index("ix_applications_id", table_name="applications")
    op.drop_table("applications")
