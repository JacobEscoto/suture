from typing import List, Tuple, Dict, Any
import sqlite3
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
        schema = parser.parse(sql)

        if sql.strip() and not schema.tables:
            raise ValueError("The provided SQL text does not contain any valid table structures or definitions.")

        return schema
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

def calculate_blast_radius(diffs) -> Dict[str, Any]:
    """Calculate migration risk based on schema changes.

    Analyzes the diffs object to determine the risk level of a migration by
    identifying destructive operations and breaking changes.

    Risk Levels:
    - CRITICAL (90-100): Tables deleted OR columns deleted (data loss)
    - MEDIUM (40-75): Column type modifications OR adding NOT NULL constraints
    - LOW (0-20): Only additions (tables, columns, indexes) with no deletions

    Args:
        diffs: Schema differences from comparator containing:
            - tables_added: List of added tables
            - tables_modified: List of modified tables with column changes
            - tables_deleted: List of deleted tables
            - indexes_added: List of added indexes
            - indexes_deleted: List of deleted indexes

    Returns:
        Dictionary with risk analysis:
        {
            "risk_level": str,  # "LOW", "MEDIUM", or "CRITICAL"
            "score": int,  # 0-100
            "destructive_actions_count": int,
            "affected_tables": List[str],
            "details": {
                "tables_dropped": List[str],
                "columns_dropped": List[Dict[str, str]],
                "type_changes": List[Dict[str, Any]],
                "not_null_additions": List[Dict[str, str]]
            }
        }
    """
    # Initialize tracking structures
    tables_dropped: List[str] = []
    columns_dropped: List[Dict[str, str]] = []
    type_changes: List[Dict[str, Any]] = []
    not_null_additions: List[Dict[str, str]] = []
    affected_tables: List[str] = []

    # Track dropped tables (CRITICAL)
    for table in diffs.tables_deleted:
        tables_dropped.append(table.name)
        affected_tables.append(table.name)

    # Analyze modified tables
    for table in diffs.tables_modified:
        table_name = table.table_name
        affected_tables.append(table_name)

        # Track dropped columns (CRITICAL)
        for col in table.columns_deleted:
            columns_dropped.append({
                "table": table_name,
                "column": col.name
            })

        # Analyze column modifications (MEDIUM risk)
        for col_change in table.columns_modified:
            if not (col_change.old_definition and col_change.new_definition):
                continue

            old_def = col_change.old_definition
            new_def = col_change.new_definition

            # Track type changes
            if old_def.data_type != new_def.data_type:
                type_changes.append({
                    "table": table_name,
                    "column": col_change.column_name,
                    "old_type": old_def.data_type,
                    "new_type": new_def.data_type
                })

            # Track NOT NULL additions
            if old_def.nullable and not new_def.nullable:
                not_null_additions.append({
                    "table": table_name,
                    "column": col_change.column_name
                })

    # Track added tables (for completeness)
    for table in diffs.tables_added:
        affected_tables.append(table.name)

    # Calculate destructive actions count
    destructive_actions_count = len(tables_dropped) + len(columns_dropped)

    # Determine risk level and score
    risk_level: str
    score: int

    if destructive_actions_count > 0:
        # CRITICAL: Any data loss operations
        risk_level = "CRITICAL"
        score = 95
    elif len(type_changes) > 0 or len(not_null_additions) > 0:
        # MEDIUM: Breaking changes that don't lose data but may cause issues
        risk_level = "MEDIUM"
        score = 60
    else:
        # LOW: Only additions, no breaking changes
        risk_level = "LOW"
        score = 10

    return {
        "risk_level": risk_level,
        "score": score,
        "destructive_actions_count": destructive_actions_count,
        "affected_tables": affected_tables,
        "details": {
            "tables_dropped": tables_dropped,
            "columns_dropped": columns_dropped,
            "type_changes": type_changes,
            "not_null_additions": not_null_additions
        }
    }


# Made with Bob


def validate_sql_execution(migration_sql: str, rollback_sql: str, base_schema: str = "") -> Dict[str, Any]:
    """Validate SQL execution in a temporary SQLite in-memory database.

    Tests both migration and rollback SQL scripts to ensure they are 100% executable
    before returning them to the client. This provides a sandbox verification layer.

    Args:
        migration_sql: The forward migration SQL script to test.
        rollback_sql: The rollback SQL script to test.
        base_schema: Optional base schema SQL to execute before migration (default: "").

    Returns:
        Dictionary with validation status:
        {
            "success": bool,  # True if both scripts executed successfully
            "error_message": str | None,  # Error message if validation failed
            "failed_script": str | None  # "migration" or "rollback" if failed
        }
    """
    conn = None
    try:
        # Create a single in-memory SQLite database connection
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # First, execute the base schema if provided
        if base_schema and base_schema.strip():
            try:
                cursor.executescript(base_schema)
                conn.commit()
            except sqlite3.Error as e:
                return {
                    "success": False,
                    "error_message": f"Base schema execution failed: {str(e)}",
                    "failed_script": "base_schema"
                }

        # Test migration SQL execution on the same connection
        try:
            # Execute the entire migration script
            cursor.executescript(migration_sql)
            conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
            return {
                "success": False,
                "error_message": str(e),
                "failed_script": "migration"
            }

        # Test rollback SQL execution
        try:
            # Execute the rollback script to ensure clean reversal
            cursor.executescript(rollback_sql)
            conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
            return {
                "success": False,
                "error_message": str(e),
                "failed_script": "rollback"
            }

        # Both scripts executed successfully
        return {
            "success": True,
            "error_message": None,
            "failed_script": None
        }

    except Exception as e:
        # Catch any unexpected errors
        return {
            "success": False,
            "error_message": f"Unexpected validation error: {str(e)}",
            "failed_script": "unknown"
        }
    finally:
        # Always close the connection
        if conn:
            conn.close()
