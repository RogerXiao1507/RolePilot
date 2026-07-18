"""Add Phase 0 application constraints.

Revision ID: 0002_phase0_constraints
Revises: 0001_initial_schema
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_phase0_constraints"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM applications
                WHERE status NOT IN ('saved', 'applied', 'interview', 'offer', 'rejected')
            ) THEN
                RAISE EXCEPTION 'applications contains unsupported status values';
            END IF;
        END $$
        """
    )
    op.alter_column(
        "applications",
        "company",
        existing_type=sa.String(),
        type_=sa.String(length=200),
        existing_nullable=False,
    )
    op.alter_column(
        "applications",
        "role_title",
        existing_type=sa.String(),
        type_=sa.String(length=200),
        existing_nullable=False,
    )
    op.alter_column(
        "applications",
        "status",
        existing_type=sa.String(),
        type_=sa.String(length=32),
        existing_nullable=False,
        server_default="saved",
    )
    op.alter_column(
        "applications",
        "location",
        existing_type=sa.String(),
        type_=sa.String(length=300),
        existing_nullable=True,
    )
    op.alter_column(
        "applications",
        "job_url",
        existing_type=sa.String(),
        type_=sa.String(length=2048),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "ck_applications_status",
        "applications",
        "status IN ('saved', 'applied', 'interview', 'offer', 'rejected')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_applications_status", "applications", type_="check")
    op.alter_column(
        "applications",
        "job_url",
        existing_type=sa.String(length=2048),
        type_=sa.String(),
        existing_nullable=True,
    )
    op.alter_column(
        "applications",
        "location",
        existing_type=sa.String(length=300),
        type_=sa.String(),
        existing_nullable=True,
    )
    op.alter_column(
        "applications",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(),
        existing_nullable=False,
        server_default=None,
    )
    op.alter_column(
        "applications",
        "role_title",
        existing_type=sa.String(length=200),
        type_=sa.String(),
        existing_nullable=False,
    )
    op.alter_column(
        "applications",
        "company",
        existing_type=sa.String(length=200),
        type_=sa.String(),
        existing_nullable=False,
    )
