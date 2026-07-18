"""Add users, tenant ownership, and row-level security.

Revision ID: 0003_user_ownership
Revises: 0002_phase0_constraints
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_user_ownership"
down_revision: Union[str, None] = "0002_phase0_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_USER_ID = "00000000-0000-4000-8000-000000000001"
OWNED_TABLES = (
    "applications",
    "resumes",
    "project_evidence",
    "project_evidence_chunks",
    "application_resume_matches",
    "application_tailored_resumes",
    "application_full_resume_drafts",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column(
            "onboarding_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_legacy_principal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_external_subject", "users", ["external_subject"], unique=True)

    op.execute(
        sa.text(
            """
            INSERT INTO users (
                id, external_subject, name, onboarding_complete, is_legacy_principal
            ) VALUES (
                :id, 'legacy|rolepilot-owner', 'Legacy RolePilot data', false, true
            )
            """
        ).bindparams(id=LEGACY_USER_ID)
    )

    for table_name in OWNED_TABLES:
        op.add_column(
            table_name,
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.execute(
            sa.text(f"UPDATE {table_name} SET user_id = :legacy_user_id").bindparams(
                legacy_user_id=LEGACY_USER_ID
            )
        )
        op.alter_column(table_name, "user_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table_name}_user_id",
            table_name,
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(f"ix_{table_name}_user_id", table_name, ["user_id"])

    op.create_unique_constraint(
        "uq_applications_id_user_id", "applications", ["id", "user_id"]
    )
    op.create_unique_constraint(
        "uq_resumes_id_user_id", "resumes", ["id", "user_id"]
    )
    op.create_unique_constraint(
        "uq_project_evidence_id_user_id", "project_evidence", ["id", "user_id"]
    )

    op.drop_constraint(
        "project_evidence_chunks_project_evidence_id_fkey",
        "project_evidence_chunks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_evidence_chunks_evidence_owner",
        "project_evidence_chunks",
        "project_evidence",
        ["project_evidence_id", "user_id"],
        ["id", "user_id"],
        ondelete="CASCADE",
        deferrable=True,
        initially="DEFERRED",
    )

    relationship_tables = (
        (
            "application_resume_matches",
            "fk_resume_matches_application_owner",
            "fk_resume_matches_resume_owner",
        ),
        (
            "application_tailored_resumes",
            "fk_tailored_resumes_application_owner",
            "fk_tailored_resumes_resume_owner",
        ),
        (
            "application_full_resume_drafts",
            "fk_full_drafts_application_owner",
            "fk_full_drafts_resume_owner",
        ),
    )
    for table_name, application_fk, resume_fk in relationship_tables:
        op.drop_constraint(
            f"{table_name}_application_id_fkey", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"{table_name}_resume_id_fkey", table_name, type_="foreignkey"
        )
        op.create_foreign_key(
            application_fk,
            table_name,
            "applications",
            ["application_id", "user_id"],
            ["id", "user_id"],
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        )
        op.create_foreign_key(
            resume_fk,
            table_name,
            "resumes",
            ["resume_id", "user_id"],
            ["id", "user_id"],
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        )

    rls_tables = ("users",) + OWNED_TABLES
    for table_name in rls_tables:
        policy_name = f"{table_name}_owner_isolation"
        if table_name == "users":
            predicate = (
                "external_subject = "
                "NULLIF(current_setting('app.current_subject', true), '')"
            )
        else:
            predicate = (
                "user_id = "
                "NULLIF(current_setting('app.current_user_id', true), '')::uuid"
            )
        op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{policy_name}" ON "{table_name}" '
            f"USING ({predicate}) WITH CHECK ({predicate})"
        )


def downgrade() -> None:
    rls_tables = ("users",) + OWNED_TABLES
    for table_name in rls_tables:
        op.execute(
            f'DROP POLICY IF EXISTS "{table_name}_owner_isolation" ON "{table_name}"'
        )
        op.execute(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY')

    relationship_tables = (
        (
            "application_resume_matches",
            "fk_resume_matches_application_owner",
            "fk_resume_matches_resume_owner",
        ),
        (
            "application_tailored_resumes",
            "fk_tailored_resumes_application_owner",
            "fk_tailored_resumes_resume_owner",
        ),
        (
            "application_full_resume_drafts",
            "fk_full_drafts_application_owner",
            "fk_full_drafts_resume_owner",
        ),
    )
    for table_name, application_fk, resume_fk in relationship_tables:
        op.drop_constraint(application_fk, table_name, type_="foreignkey")
        op.drop_constraint(resume_fk, table_name, type_="foreignkey")
        op.create_foreign_key(
            f"{table_name}_application_id_fkey",
            table_name,
            "applications",
            ["application_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            f"{table_name}_resume_id_fkey",
            table_name,
            "resumes",
            ["resume_id"],
            ["id"],
            ondelete="CASCADE",
        )

    op.drop_constraint(
        "fk_evidence_chunks_evidence_owner",
        "project_evidence_chunks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "project_evidence_chunks_project_evidence_id_fkey",
        "project_evidence_chunks",
        "project_evidence",
        ["project_evidence_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("uq_project_evidence_id_user_id", "project_evidence", type_="unique")
    op.drop_constraint("uq_resumes_id_user_id", "resumes", type_="unique")
    op.drop_constraint("uq_applications_id_user_id", "applications", type_="unique")

    for table_name in reversed(OWNED_TABLES):
        op.drop_index(f"ix_{table_name}_user_id", table_name=table_name)
        op.drop_constraint(f"fk_{table_name}_user_id", table_name, type_="foreignkey")
        op.drop_column(table_name, "user_id")

    op.drop_index("ix_users_external_subject", table_name="users")
    op.drop_table("users")
