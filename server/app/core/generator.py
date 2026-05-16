"""
Migration Generator Module for Suturé

This module provides SQL migration generation capabilities to create
migration and rollback scripts from schema changes.

Python Version: 3.13+
"""

import logging
from typing import List

from .comparator import ColumnChange, SchemaChanges, TableChange
from .parser import (
    ColumnDefinition,
    ConstraintDefinition,
    ConstraintType,
    IndexDefinition,
    TableDefinition,
)

logger = logging.getLogger(__name__)


class MigrationGenerator:
    """
    Generates PostgreSQL migration and rollback SQL from schema changes.

    Handles:
    - Table creation and deletion
    - Column additions and deletions
    - Column data type changes
    - Constraint additions and deletions
    - Index additions and deletions
    """

    def __init__(self) -> None:
        """Initialize the migration generator."""
        pass

    def generate(self, changes: SchemaChanges) -> tuple[str, str]:
        """
        Generate migration and rollback SQL from schema changes.

        Args:
            changes: SchemaChanges object containing all detected differences.

        Returns:
            Tuple of (migration_sql, rollback_sql) strings.
        """
        migration_statements: List[str] = []
        rollback_statements: List[str] = []

        # Process in order: tables added, tables modified, tables deleted
        # This ensures proper dependency handling

        # 1. Create new tables (forward)
        for table in changes.tables_added:
            migration_statements.append(self._generate_create_table(table))
            rollback_statements.insert(0, self._generate_drop_table(table.name))

        # 2. Modify existing tables (forward)
        for table_change in changes.tables_modified:
            mig_stmts, roll_stmts = self._generate_table_modifications(table_change)
            migration_statements.extend(mig_stmts)
            # Rollback statements are inserted in reverse order
            for stmt in reversed(roll_stmts):
                rollback_statements.insert(0, stmt)

        # 3. Drop tables (forward)
        for table in changes.tables_deleted:
            migration_statements.append(self._generate_drop_table(table.name))
            rollback_statements.insert(0, self._generate_create_table(table))

        # 4. Standalone indexes
        for index in changes.indexes_added:
            migration_statements.append(self._generate_create_index(index))
            rollback_statements.insert(0, self._generate_drop_index(index.name))

        for index in changes.indexes_deleted:
            migration_statements.append(self._generate_drop_index(index.name))
            rollback_statements.insert(0, self._generate_create_index(index))

        # Join all statements
        migration_sql = "\n\n".join(migration_statements) if migration_statements else "-- No changes detected"
        rollback_sql = "\n\n".join(rollback_statements) if rollback_statements else "-- No rollback needed"

        return migration_sql, rollback_sql

    def _generate_create_table(self, table: TableDefinition) -> str:
        """Generate CREATE TABLE statement."""
        lines = [f"CREATE TABLE {self._quote_identifier(table.name)} ("]

        column_defs = []
        for col in table.columns.values():
            column_defs.append(f"    {self._generate_column_definition(col)}")

        # Add table-level constraints
        for constraint in table.constraints:
            column_defs.append(f"    {self._generate_constraint_definition(constraint)}")

        lines.append(",\n".join(column_defs))
        lines.append(");")

        result = "\n".join(lines)

        # Add indexes separately
        for index in table.indexes:
            result += f"\n\n{self._generate_create_index(index)}"

        return result

    def _generate_drop_table(self, table_name: str) -> str:
        """Generate DROP TABLE statement."""
        return f"DROP TABLE IF EXISTS {self._quote_identifier(table_name)};"

    def _generate_table_modifications(
        self, table_change: TableChange
    ) -> tuple[List[str], List[str]]:
        """
        Generate ALTER TABLE statements for table modifications.

        Returns:
            Tuple of (migration_statements, rollback_statements).
        """
        migration_stmts: List[str] = []
        rollback_stmts: List[str] = []
        table_name = table_change.table_name

        # Drop constraints first (they may depend on columns)
        for constraint in table_change.constraints_deleted:
            if constraint.name:
                migration_stmts.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"DROP CONSTRAINT {self._quote_identifier(constraint.name)};"
                )
                rollback_stmts.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ADD {self._generate_constraint_definition(constraint)};"
                )

        # Drop indexes
        for index in table_change.indexes_deleted:
            migration_stmts.append(self._generate_drop_index(index.name))
            rollback_stmts.append(self._generate_create_index(index))

        # Drop columns
        for col in table_change.columns_deleted:
            migration_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"DROP COLUMN {self._quote_identifier(col.name)};"
            )
            rollback_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ADD COLUMN {self._generate_column_definition(col)};"
            )

        # Modify columns (data type changes, nullability, etc.)
        for col_change in table_change.columns_modified:
            mig_stmt, roll_stmt = self._generate_column_modification(
                table_name, col_change
            )
            if mig_stmt:
                migration_stmts.append(mig_stmt)
            if roll_stmt:
                rollback_stmts.append(roll_stmt)

        # Add columns
        for col in table_change.columns_added:
            migration_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ADD COLUMN {self._generate_column_definition(col)};"
            )
            rollback_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"DROP COLUMN {self._quote_identifier(col.name)};"
            )

        # Add constraints
        for constraint in table_change.constraints_added:
            migration_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ADD {self._generate_constraint_definition(constraint)};"
            )
            if constraint.name:
                rollback_stmts.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"DROP CONSTRAINT {self._quote_identifier(constraint.name)};"
                )

        # Add indexes
        for index in table_change.indexes_added:
            migration_stmts.append(self._generate_create_index(index))
            rollback_stmts.append(self._generate_drop_index(index.name))

        return migration_stmts, rollback_stmts

    def _generate_column_modification(
        self, table_name: str, col_change: ColumnChange
    ) -> tuple[str, str]:
        """
        Generate ALTER COLUMN statements for column modifications.

        Returns:
            Tuple of (migration_statement, rollback_statement).
        """
        old_col = col_change.old_definition
        new_col = col_change.new_definition

        if not old_col or not new_col:
            return "", ""

        col_name = col_change.column_name
        statements: List[str] = []
        rollback_statements: List[str] = []

        # Data type change
        if old_col.data_type.upper() != new_col.data_type.upper():
            statements.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ALTER COLUMN {self._quote_identifier(col_name)} "
                f"TYPE {new_col.data_type}"
            )
            rollback_statements.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ALTER COLUMN {self._quote_identifier(col_name)} "
                f"TYPE {old_col.data_type}"
            )

        # Nullability change
        if old_col.nullable != new_col.nullable:
            if new_col.nullable:
                statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"DROP NOT NULL"
                )
                rollback_statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"SET NOT NULL"
                )
            else:
                statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"SET NOT NULL"
                )
                rollback_statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"DROP NOT NULL"
                )

        # Default value change
        if old_col.default != new_col.default:
            if new_col.default:
                statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"SET DEFAULT {new_col.default}"
                )
            else:
                statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"DROP DEFAULT"
                )

            if old_col.default:
                rollback_statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"SET DEFAULT {old_col.default}"
                )
            else:
                rollback_statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"DROP DEFAULT"
                )

        # Combine all statements for this column
        migration = ";\n".join(statements) + ";" if statements else ""
        rollback = ";\n".join(reversed(rollback_statements)) + ";" if rollback_statements else ""

        return migration, rollback

    def _generate_column_definition(self, col: ColumnDefinition) -> str:
        """Generate column definition for CREATE/ALTER TABLE."""
        parts = [self._quote_identifier(col.name), col.data_type]

        # Add constraints in proper order
        if not col.nullable:
            parts.append("NOT NULL")

        if col.default is not None:
            parts.append(f"DEFAULT {col.default}")

        # Add other constraints (PRIMARY KEY, UNIQUE, etc.)
        for constraint in col.constraints:
            constraint_upper = constraint.upper()
            # Skip NOT NULL and DEFAULT as they're already handled
            if "NOT NULL" not in constraint_upper and "DEFAULT" not in constraint_upper:
                parts.append(constraint)

        return " ".join(parts)

    def _generate_constraint_definition(self, constraint: ConstraintDefinition) -> str:
        """Generate constraint definition."""
        parts = []

        if constraint.name:
            parts.append(f"CONSTRAINT {self._quote_identifier(constraint.name)}")

        if constraint.constraint_type == ConstraintType.PRIMARY_KEY:
            cols = ", ".join(self._quote_identifier(c) for c in constraint.columns)
            parts.append(f"PRIMARY KEY ({cols})")
        elif constraint.constraint_type == ConstraintType.FOREIGN_KEY:
            cols = ", ".join(self._quote_identifier(c) for c in constraint.columns)
            parts.append(f"FOREIGN KEY ({cols})")
            if constraint.references:
                ref_table, ref_cols = constraint.references
                ref_cols_str = ", ".join(self._quote_identifier(c) for c in ref_cols)
                parts.append(f"REFERENCES {self._quote_identifier(ref_table)} ({ref_cols_str})")
        elif constraint.constraint_type == ConstraintType.UNIQUE:
            cols = ", ".join(self._quote_identifier(c) for c in constraint.columns)
            parts.append(f"UNIQUE ({cols})")
        elif constraint.constraint_type == ConstraintType.CHECK:
            # Use the raw definition for CHECK constraints
            parts.append(constraint.definition)

        return " ".join(parts)

    def _generate_create_index(self, index: IndexDefinition) -> str:
        """Generate CREATE INDEX statement."""
        unique = "UNIQUE " if index.unique else ""
        cols = ", ".join(self._quote_identifier(c) for c in index.columns)
        using = f" USING {index.index_type}" if index.index_type else ""

        return (
            f"CREATE {unique}INDEX {self._quote_identifier(index.name)} "
            f"ON {self._quote_identifier(index.table)}{using} ({cols});"
        )

    def _generate_drop_index(self, index_name: str) -> str:
        """Generate DROP INDEX statement."""
        return f"DROP INDEX IF EXISTS {self._quote_identifier(index_name)};"

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """
        Quote SQL identifier if needed.

        PostgreSQL identifiers are case-insensitive unless quoted.
        We quote identifiers that contain special characters or are reserved words.
        """
        # Simple heuristic: quote if contains uppercase, special chars, or spaces
        if (
            identifier.lower() != identifier
            or " " in identifier
            or "-" in identifier
            or any(c in identifier for c in "!@#$%^&*()+{}[]|\\:;'<>?,./")
        ):
            # Escape any existing double quotes
            escaped = identifier.replace('"', '""')
            return f'"{escaped}"'
        return identifier


# Made with Bob