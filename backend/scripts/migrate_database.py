"""Apply migrations, safely baselining databases created before Alembic."""
from __future__ import annotations

from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import engine
import app.models  # noqa: F401  # Registers PostgreSQL/pgvector model types for inspection.


LEGACY_BASELINE_REVISION = "0001_initial_schema"
LEGACY_SCHEMA_COLUMNS = {
    "applications": {
        "id",
        "company",
        "role_title",
        "status",
        "location",
        "job_url",
        "job_description",
        "ai_summary",
        "required_skills",
        "preferred_skills",
        "keywords",
        "next_steps",
        "created_at",
    },
    "resumes": {
        "id",
        "file_name",
        "extracted_text",
        "summary",
        "strengths",
        "weaknesses",
        "wording_issues",
        "missing_metrics",
        "suggested_improvements",
        "created_at",
    },
    "project_evidence": {
        "id",
        "title",
        "category",
        "description",
        "skills",
        "keywords",
        "bullet_bank",
        "created_at",
    },
    "project_evidence_chunks": {
        "id",
        "project_evidence_id",
        "chunk_text",
        "chunk_type",
        "embedding",
        "created_at",
    },
    "application_resume_matches": {
        "id",
        "application_id",
        "resume_id",
        "overall_match_summary",
        "matched_skills",
        "missing_skills",
        "strengths_for_role",
        "improvement_areas",
        "suggested_resume_changes",
        "created_at",
        "updated_at",
    },
    "application_tailored_resumes": {
        "id",
        "application_id",
        "resume_id",
        "tailored_summary",
        "tailored_skills",
        "tailored_bullets",
        "tailoring_notes",
        "created_at",
        "updated_at",
    },
    "application_full_resume_drafts": {
        "id",
        "application_id",
        "resume_id",
        "draft_data",
        "created_at",
        "updated_at",
    },
}


def validate_legacy_schema(database_inspector) -> bool:
    """Return True for a complete legacy schema and reject partial/mismatched schemas."""
    existing_tables = set(database_inspector.get_table_names())
    expected_tables = set(LEGACY_SCHEMA_COLUMNS)
    present_rolepilot_tables = existing_tables.intersection(expected_tables)

    if not present_rolepilot_tables:
        return False
    if present_rolepilot_tables != expected_tables:
        missing = sorted(expected_tables - present_rolepilot_tables)
        raise RuntimeError(
            "Refusing to baseline a partial legacy database. "
            f"Missing tables: {', '.join(missing)}"
        )

    for table_name, required_columns in LEGACY_SCHEMA_COLUMNS.items():
        existing_columns = {
            column["name"] for column in database_inspector.get_columns(table_name)
        }
        missing_columns = required_columns - existing_columns
        if missing_columns:
            raise RuntimeError(
                f"Refusing to baseline table {table_name}; missing columns: "
                f"{', '.join(sorted(missing_columns))}"
            )

    return True


def main() -> None:
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    database_inspector = inspect(engine)
    existing_tables = set(database_inspector.get_table_names())

    if "alembic_version" not in existing_tables and validate_legacy_schema(database_inspector):
        command.stamp(alembic_config, LEGACY_BASELINE_REVISION)

    command.upgrade(alembic_config, "head")


if __name__ == "__main__":
    main()
