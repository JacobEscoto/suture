from typing import List, Tuple, Dict, Any
from fastapi import HTTPException
from app.api.schemas import (
    ParseError,
    TableChange as ApiTableChange,
    ColumnChange,
    ConstraintChange,
    IndexChange,
)
from app.core.parser import (
    SQLParser,
    SchemaDefinition,
    ColumnDefinition,
    ConstraintDefinition,
    IndexDefinition,
)
from app.core.comparator import (
    TableChange as ComparatorTableChange,
    ColumnChange as ComparatorColumnChange,
)


def parse_schema_safe(sql: str, editor: str, editor_label: str) -> SchemaDefinition:
    """Parse SQL schema and raise HTTPException on failure.

    Args:
        sql: The SQL script to parse.
        editor: Editor identifier ("v1" or "v2").
        editor_label: Human-readable label for error messages.

    Returns:
        Parsed SchemaDefinition.

    Raises:
        HTTPException: If parsing fails.
    """
    parser = SQLParser()
    try:
        return parser.parse(sql)
    except Exception as e:
        error = ParseError(
            error_type="parse_error",
            message=str(e),
            editor=editor,
            suggestion=f"Check SQL syntax in {editor_label}"
        )
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Failed to parse {editor_label}",
                "errors": [{
                    "error_type": error.error_type,
                    "message": error.message,
                    "editor": error.editor,
                    "suggestion": error.suggestion
                }]
            }
        )


def _transform_column_to_api(col: ColumnDefinition, change_type: str) -> ColumnChange:
    """Transform parser ColumnDefinition to API ColumnChange.

    Args:
        col: Column definition from parser.
        change_type: Type of change ("added", "deleted", "modified").

    Returns:
        API ColumnChange object.
    """
    return ColumnChange(
        name=col.name,
        data_type=col.data_type,
        nullable=col.nullable,
        default=col.default,
        constraints=col.constraints,
        references=col.references,
        change_type=change_type
    )


def _transform_modified_column(col_change: ComparatorColumnChange) -> ColumnChange:
    """Transform comparator ColumnChange to API ColumnChange with old/new values.

    Args:
        col_change: Column change from comparator.

    Returns:
        API ColumnChange object with both old and new values.
    """
    return ColumnChange(
        name=col_change.column_name,
        data_type=col_change.new_definition.data_type if col_change.new_definition else None,
        nullable=col_change.new_definition.nullable if col_change.new_definition else None,
        default=col_change.new_definition.default if col_change.new_definition else None,
        constraints=col_change.new_definition.constraints if col_change.new_definition else [],
        references=col_change.new_definition.references if col_change.new_definition else None,
        change_type="modified",
        old_data_type=col_change.old_definition.data_type if col_change.old_definition else None,
        old_nullable=col_change.old_definition.nullable if col_change.old_definition else None,
        old_default=col_change.old_definition.default if col_change.old_definition else None,
        old_constraints=col_change.old_definition.constraints if col_change.old_definition else [],
        old_references=col_change.old_definition.references if col_change.old_definition else None,
    )


def _transform_constraint_to_api(const: ConstraintDefinition, change_type: str) -> ConstraintChange:
    """Transform parser ConstraintDefinition to API ConstraintChange.

    Args:
        const: Constraint definition from parser.
        change_type: Type of change ("added", "deleted").

    Returns:
        API ConstraintChange object.
    """
    return ConstraintChange(
        name=const.name,
        constraint_type=const.constraint_type.value,
        columns=const.columns,
        definition=const.definition,
        references=const.references,
        change_type=change_type
    )


def _transform_index_to_api(idx: IndexDefinition, change_type: str) -> IndexChange:
    """Transform parser IndexDefinition to API IndexChange.

    Args:
        idx: Index definition from parser.
        change_type: Type of change ("added", "deleted").

    Returns:
        API IndexChange object.
    """
    return IndexChange(
        name=idx.name,
        table=idx.table,
        columns=idx.columns,
        unique=idx.unique,
        index_type=idx.index_type,
        change_type=change_type
    )


def generate_table_warnings(table: ComparatorTableChange) -> List[str]:
    """Generate warnings for potentially destructive table changes.

    Args:
        table: Table change from comparator.

    Returns:
        List of warning messages.
    """
    warnings = []

    # Warn about dropped columns
    for col in table.columns_deleted:
        warnings.append(
            f"⚠️ Column '{table.table_name}.{col.name}' will be dropped - data loss will occur"
        )

    # Warn about column modifications
    for col_change in table.columns_modified:
        if not (col_change.old_definition and col_change.new_definition):
            continue

        old_def = col_change.old_definition
        new_def = col_change.new_definition

        # Type change warning
        if old_def.data_type != new_def.data_type:
            warnings.append(
                f"⚠️ Column '{table.table_name}.{col_change.column_name}' "
                f"type change ({old_def.data_type} → {new_def.data_type}) may require data casting"
            )

        # NOT NULL constraint warning
        if old_def.nullable and not new_def.nullable:
            warnings.append(
                f"⚠️ Column '{table.table_name}.{col_change.column_name}' "
                f"adding NOT NULL constraint - ensure no NULL values exist"
            )

    return warnings


def transform_table_changes(table: ComparatorTableChange) -> ApiTableChange:
    """Transform comparator TableChange to API TableChange.

    Args:
        table: Table change from comparator.

    Returns:
        API TableChange object with all transformations applied.
    """
    # Transform columns
    columns_added = [_transform_column_to_api(col, "added") for col in table.columns_added]
    columns_deleted = [_transform_column_to_api(col, "deleted") for col in table.columns_deleted]
    columns_modified = [_transform_modified_column(col) for col in table.columns_modified]

    # Transform constraints
    constraints_added = [_transform_constraint_to_api(c, "added") for c in table.constraints_added]
    constraints_deleted = [_transform_constraint_to_api(c, "deleted") for c in table.constraints_deleted]

    # Transform indexes
    indexes_added = [_transform_index_to_api(idx, "added") for idx in table.indexes_added]
    indexes_deleted = [_transform_index_to_api(idx, "deleted") for idx in table.indexes_deleted]

    return ApiTableChange(
        name=table.table_name,
        change_type=table.change_type,
        columns=columns_added + columns_deleted + columns_modified,
        constraints=constraints_added + constraints_deleted,
        indexes=indexes_added + indexes_deleted
    )


def build_comparison_summary(diffs) -> Tuple[List[str], List[ApiTableChange], Dict[str, int]]:
    """Process comparison results and build warnings, tables, and summary.

    Args:
        diffs: Schema differences from comparator.

    Returns:
        Tuple of (warnings, transformed_tables, summary_data).
    """
    warnings: List[str] = []
    tables_to_report: List[ApiTableChange] = []

    # Warn about dropped tables
    for table in diffs.tables_deleted:
        warnings.append(f"⚠️ Table '{table.name}' will be dropped - data loss will occur")

    # Process modified tables
    for table in diffs.tables_modified:
        warnings.extend(generate_table_warnings(table))
        tables_to_report.append(transform_table_changes(table))

    # Calculate index changes
    idx_added = (
        sum(len(table.indexes_added) for table in diffs.tables_modified)
        + len(diffs.indexes_added)
    )
    idx_deleted = (
        sum(len(table.indexes_deleted) for table in diffs.tables_modified)
        + len(diffs.indexes_deleted)
    )

    # Warn about dropped indexes
    for idx in diffs.indexes_deleted:
        warnings.append(f"⚠️ Index '{idx.name}' on '{idx.table}' will be dropped")

    # Build summary
    summary_data: Dict[str, int] = {
        "tables_added": len(diffs.tables_added),
        "tables_modified": len(diffs.tables_modified),
        "tables_deleted": len(diffs.tables_deleted),
        "indexes_added": idx_added,
        "indexes_deleted": idx_deleted,
    }

    return warnings, tables_to_report, summary_data

# Made with Bob
