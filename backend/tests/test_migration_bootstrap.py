import pytest

from scripts.migrate_database import LEGACY_SCHEMA_COLUMNS, validate_legacy_schema


class FakeInspector:
    def __init__(self, tables):
        self.tables = tables

    def get_table_names(self):
        return list(self.tables)

    def get_columns(self, table_name):
        return [{"name": name} for name in self.tables[table_name]]


def test_empty_database_does_not_need_legacy_baseline():
    assert validate_legacy_schema(FakeInspector({})) is False


def test_complete_legacy_database_can_be_baselined():
    inspector = FakeInspector(
        {table: set(columns) for table, columns in LEGACY_SCHEMA_COLUMNS.items()}
    )

    assert validate_legacy_schema(inspector) is True


def test_partial_legacy_database_is_rejected():
    inspector = FakeInspector(
        {"applications": set(LEGACY_SCHEMA_COLUMNS["applications"])}
    )

    with pytest.raises(RuntimeError, match="partial legacy database"):
        validate_legacy_schema(inspector)


def test_legacy_table_missing_a_column_is_rejected():
    tables = {table: set(columns) for table, columns in LEGACY_SCHEMA_COLUMNS.items()}
    tables["resumes"].remove("extracted_text")

    with pytest.raises(RuntimeError, match="missing columns: extracted_text"):
        validate_legacy_schema(FakeInspector(tables))
