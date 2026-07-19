"""Add the user-managed resume library and application selection.

Revision ID: 0004_resume_library
Revises: 0003_user_ownership
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_resume_library"
down_revision: Union[str, None] = "0003_user_ownership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("label", sa.String(length=120), nullable=True))
    op.add_column(
        "resumes",
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "resumes",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "resumes",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.execute(
        """
        UPDATE resumes
        SET label = LEFT(
            COALESCE(
                NULLIF(regexp_replace(file_name, '\\.[^.]+$', ''), ''),
                'Resume ' || id::text
            ),
            120
        )
        """
    )
    op.alter_column("resumes", "label", nullable=False)

    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY user_id
                       ORDER BY created_at DESC, id DESC
                   ) AS resume_rank
            FROM resumes
        )
        UPDATE resumes AS resume
        SET is_default = true
        FROM ranked
        WHERE resume.id = ranked.id AND ranked.resume_rank = 1
        """
    )
    op.create_index(
        "uq_resumes_one_default_per_user",
        "resumes",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default AND NOT is_archived"),
    )

    op.add_column(
        "applications",
        sa.Column("selected_resume_id", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE applications AS application
        SET selected_resume_id = resume.id
        FROM resumes AS resume
        WHERE resume.user_id = application.user_id
          AND resume.is_default = true
          AND resume.is_archived = false
        """
    )
    op.create_foreign_key(
        "fk_applications_selected_resume_owner",
        "applications",
        "resumes",
        ["selected_resume_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_index(
        "ix_applications_user_selected_resume",
        "applications",
        ["user_id", "selected_resume_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_applications_user_selected_resume",
        table_name="applications",
    )
    op.drop_constraint(
        "fk_applications_selected_resume_owner",
        "applications",
        type_="foreignkey",
    )
    op.drop_column("applications", "selected_resume_id")

    op.drop_index("uq_resumes_one_default_per_user", table_name="resumes")
    op.drop_column("resumes", "updated_at")
    op.drop_column("resumes", "is_archived")
    op.drop_column("resumes", "is_default")
    op.drop_column("resumes", "label")
