"""
Schema Comparator Module for Suturé

This module provides schema comparison capabilities to detect differences
between two database schemas, including tables, columns, indexes, and constraints.

Python Version: 3.13+
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .parser import (
    ColumnDefinition,
    ConstraintDefinition,
    IndexDefinition,
    SchemaDefinition,
    TableDefinition,
)

logger = logging.getLogger(__name__)


@dataclass
class ColumnChange:
    """Represents a change to a column."""

    column_name: str
    old_definition: Optional[ColumnDefinition] = None
    new_definition: Optional[ColumnDefinition] = None
    change_type: str = "modified"  # "added", "deleted", "modified"

    def __repr__(self) -> str:
        return f"ColumnChange({self.change_type}: {self.column_name})"


@dataclass
class TableChange:
    """Represents changes to a table."""

    table_name: str
    change_type: str  # "added", "deleted", "modified"
    columns_added: List[ColumnDefinition] = field(default_factory=list)
    columns_deleted: List[ColumnDefinition] = field(default_factory=list)
    columns_modified: List[ColumnChange] = field(default_factory=list)
    constraints_added: List[ConstraintDefinition] = field(default_factory=list)
    constraints_deleted: List[ConstraintDefinition] = field(default_factory=list)
    indexes_added: List[IndexDefinition] = field(default_factory=list)
    indexes_deleted: List[IndexDefinition] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"TableChange({self.change_type}: {self.table_name})"

    def has_changes(self) -> bool:
        """Check if this table has any actual changes."""
        return bool(
            self.columns_added
            or self.columns_deleted
            or self.columns_modified
            or self.constraints_added
            or self.constraints_deleted
            or self.indexes_added
            or self.indexes_deleted
        )


@dataclass
class SchemaChanges:
    """Represents all changes between two schemas."""

    tables_added: List[TableDefinition] = field(default_factory=list)
    tables_deleted: List[TableDefinition] = field(default_factory=list)
    tables_modified: List[TableChange] = field(default_factory=list)
    indexes_added: List[IndexDefinition] = field(default_factory=list)
    indexes_deleted: List[IndexDefinition] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"SchemaChanges("
            f"tables_added={len(self.tables_added)}, "
            f"tables_deleted={len(self.tables_deleted)}, "
            f"tables_modified={len(self.tables_modified)}, "
            f"indexes_added={len(self.indexes_added)}, "
            f"indexes_deleted={len(self.indexes_deleted)})"
        )

    def has_changes(self) -> bool:
        """Check if there are any changes between the schemas."""
        return bool(
            self.tables_added
            or self.tables_deleted
            or self.tables_modified
            or self.indexes_added
            or self.indexes_deleted
        )

    def get_summary(self) -> Dict[str, int]:
        """Get a summary of all changes."""
        return {
            "tables_added": len(self.tables_added),
            "tables_deleted": len(self.tables_deleted),
            "tables_modified": len(self.tables_modified),
            "indexes_added": len(self.indexes_added),
            "indexes_deleted": len(self.indexes_deleted),
        }


class SchemaComparator:
    """
    Compares two SchemaDefinition instances and identifies differences.

    Detects:
    - Added/deleted/modified tables
    - Added/deleted/modified columns (including data type changes)
    - Added/deleted constraints
    - Added/deleted indexes
    """

    def __init__(self) -> None:
        """Initialize the schema comparator."""
        pass

    def compare(
        self, old_schema: SchemaDefinition, new_schema: SchemaDefinition
    ) -> SchemaChanges:
        """
        Compare two schemas and return detailed changes.

        Args:
            old_schema: The original schema definition.
            new_schema: The new schema definition to compare against.

        Returns:
            SchemaChanges object containing all detected differences.
        """
        changes = SchemaChanges()

        # Compare tables
        old_table_names = set(old_schema.tables.keys())
        new_table_names = set(new_schema.tables.keys())

        # Find added tables
        for table_name in new_table_names - old_table_names:
            changes.tables_added.append(new_schema.tables[table_name])
            logger.debug("Table added: %s", table_name)

        # Find deleted tables
        for table_name in old_table_names - new_table_names:
            changes.tables_deleted.append(old_schema.tables[table_name])
            logger.debug("Table deleted: %s", table_name)

        # Find modified tables
        for table_name in old_table_names & new_table_names:
            table_change = self._compare_tables(
                old_schema.tables[table_name], new_schema.tables[table_name]
            )
            if table_change.has_changes():
                changes.tables_modified.append(table_change)
                logger.debug("Table modified: %s", table_name)

        # Compare standalone indexes (not associated with specific tables)
        self._compare_standalone_indexes(old_schema, new_schema, changes)

        return changes

    def _compare_tables(
        self, old_table: TableDefinition, new_table: TableDefinition
    ) -> TableChange:
        """
        Compare two table definitions and identify changes.

        Args:
            old_table: The original table definition.
            new_table: The new table definition.

        Returns:
            TableChange object with all detected differences.
        """
        table_change = TableChange(table_name=old_table.name, change_type="modified")

        # Compare columns
        old_column_names = set(old_table.columns.keys())
        new_column_names = set(new_table.columns.keys())

        # Added columns
        for col_name in new_column_names - old_column_names:
            table_change.columns_added.append(new_table.columns[col_name])
            logger.debug("Column added: %s.%s", old_table.name, col_name)

        # Deleted columns
        for col_name in old_column_names - new_column_names:
            table_change.columns_deleted.append(old_table.columns[col_name])
            logger.debug("Column deleted: %s.%s", old_table.name, col_name)

        # Modified columns
        for col_name in old_column_names & new_column_names:
            old_col = old_table.columns[col_name]
            new_col = new_table.columns[col_name]

            if self._columns_differ(old_col, new_col):
                column_change = ColumnChange(
                    column_name=col_name,
                    old_definition=old_col,
                    new_definition=new_col,
                    change_type="modified",
                )
                table_change.columns_modified.append(column_change)
                logger.debug("Column modified: %s.%s", old_table.name, col_name)

        # Compare constraints
        self._compare_constraints(old_table, new_table, table_change)

        # Compare table-level indexes
        self._compare_table_indexes(old_table, new_table, table_change)

        return table_change

    def _columns_differ(
        self, old_col: ColumnDefinition, new_col: ColumnDefinition
    ) -> bool:
        """
        Check if two column definitions are different.

        Compares:
        - Data type
        - Nullable flag
        - Default value
        - Constraints
        - References

        Args:
            old_col: The original column definition.
            new_col: The new column definition.

        Returns:
            True if columns differ, False otherwise.
        """
        # Normalize data types for comparison (case-insensitive)
        old_type = old_col.data_type.upper().strip()
        new_type = new_col.data_type.upper().strip()

        if old_type != new_type:
            logger.debug(
                "Data type changed: %s -> %s", old_col.data_type, new_col.data_type
            )
            return True

        if old_col.nullable != new_col.nullable:
            logger.debug("Nullable changed: %s -> %s", old_col.nullable, new_col.nullable)
            return True

        # Normalize default values for comparison
        old_default = self._normalize_default(old_col.default)
        new_default = self._normalize_default(new_col.default)

        if old_default != new_default:
            logger.debug("Default changed: %s -> %s", old_col.default, new_col.default)
            return True

        # Compare constraints (order-independent)
        old_constraints = set(self._normalize_constraint(c) for c in old_col.constraints)
        new_constraints = set(self._normalize_constraint(c) for c in new_col.constraints)

        if old_constraints != new_constraints:
            logger.debug(
                "Constraints changed: %s -> %s", old_col.constraints, new_col.constraints
            )
            return True

        # Compare references
        if old_col.references != new_col.references:
            logger.debug(
                "References changed: %s -> %s", old_col.references, new_col.references
            )
            return True

        return False

    @staticmethod
    def _normalize_default(default: Optional[str]) -> Optional[str]:
        """Normalize default value for comparison."""
        if default is None:
            return None
        # Remove extra whitespace and normalize case for keywords
        normalized = " ".join(default.split())
        return normalized.upper() if normalized.upper() in ("NULL", "TRUE", "FALSE") else normalized

    @staticmethod
    def _normalize_constraint(constraint: str) -> str:
        """Normalize constraint string for comparison."""
        # Remove extra whitespace and normalize to uppercase
        return " ".join(constraint.upper().split())

    def _compare_constraints(
        self,
        old_table: TableDefinition,
        new_table: TableDefinition,
        table_change: TableChange,
    ) -> None:
        """
        Compare constraints between two tables.

        Args:
            old_table: The original table definition.
            new_table: The new table definition.
            table_change: The TableChange object to populate.
        """
        # Create comparable representations of constraints
        old_constraints = {
            self._constraint_signature(c): c for c in old_table.constraints
        }
        new_constraints = {
            self._constraint_signature(c): c for c in new_table.constraints
        }

        old_sigs = set(old_constraints.keys())
        new_sigs = set(new_constraints.keys())

        # Added constraints
        for sig in new_sigs - old_sigs:
            table_change.constraints_added.append(new_constraints[sig])
            logger.debug("Constraint added: %s", new_constraints[sig])

        # Deleted constraints
        for sig in old_sigs - new_sigs:
            table_change.constraints_deleted.append(old_constraints[sig])
            logger.debug("Constraint deleted: %s", old_constraints[sig])

    @staticmethod
    def _constraint_signature(constraint: ConstraintDefinition) -> str:
        """
        Create a unique signature for a constraint for comparison.

        Args:
            constraint: The constraint definition.

        Returns:
            A string signature representing the constraint.
        """
        # Use constraint type, columns, and references to create signature
        sig_parts = [
            constraint.constraint_type.value,
            ",".join(sorted(constraint.columns)),
        ]

        if constraint.references:
            ref_table, ref_cols = constraint.references
            sig_parts.append(f"REF:{ref_table}({','.join(sorted(ref_cols))})")

        # Include name if present (for named constraints)
        if constraint.name:
            sig_parts.append(f"NAME:{constraint.name}")

        return "|".join(sig_parts)

    def _compare_table_indexes(
        self,
        old_table: TableDefinition,
        new_table: TableDefinition,
        table_change: TableChange,
    ) -> None:
        """
        Compare indexes within a table.

        Args:
            old_table: The original table definition.
            new_table: The new table definition.
            table_change: The TableChange object to populate.
        """
        old_indexes = {self._index_signature(idx): idx for idx in old_table.indexes}
        new_indexes = {self._index_signature(idx): idx for idx in new_table.indexes}

        old_sigs = set(old_indexes.keys())
        new_sigs = set(new_indexes.keys())

        # Added indexes
        for sig in new_sigs - old_sigs:
            table_change.indexes_added.append(new_indexes[sig])
            logger.debug("Index added: %s", new_indexes[sig])

        # Deleted indexes
        for sig in old_sigs - new_sigs:
            table_change.indexes_deleted.append(old_indexes[sig])
            logger.debug("Index deleted: %s", old_indexes[sig])

    def _compare_standalone_indexes(
        self,
        old_schema: SchemaDefinition,
        new_schema: SchemaDefinition,
        changes: SchemaChanges,
    ) -> None:
        """
        Compare standalone indexes (schema-level indexes).

        Args:
            old_schema: The original schema definition.
            new_schema: The new schema definition.
            changes: The SchemaChanges object to populate.
        """
        old_indexes = {self._index_signature(idx): idx for idx in old_schema.indexes}
        new_indexes = {self._index_signature(idx): idx for idx in new_schema.indexes}

        old_sigs = set(old_indexes.keys())
        new_sigs = set(new_indexes.keys())

        # Added indexes
        for sig in new_sigs - old_sigs:
            changes.indexes_added.append(new_indexes[sig])
            logger.debug("Standalone index added: %s", new_indexes[sig])

        # Deleted indexes
        for sig in old_sigs - new_sigs:
            changes.indexes_deleted.append(old_indexes[sig])
            logger.debug("Standalone index deleted: %s", old_indexes[sig])

    @staticmethod
    def _index_signature(index: IndexDefinition) -> str:
        """
        Create a unique signature for an index for comparison.

        Args:
            index: The index definition.

        Returns:
            A string signature representing the index.
        """
        sig_parts = [
            index.name,
            index.table,
            ",".join(sorted(index.columns)),
            str(index.unique),
        ]

        if index.index_type:
            sig_parts.append(index.index_type)

        return "|".join(sig_parts)

# Made with Bob
