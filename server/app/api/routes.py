from fastapi import APIRouter
from app.api.schemas import (
    SchemaComparisonRequest,
    AnalysisResult,
    SchemaChanges as ApiSchemaChanges,
)
from app.api.helpers import (
    parse_schema_safe,
    build_comparison_summary,
    calculate_blast_radius,
    validate_sql_execution,
)
from app.core.comparator import SchemaComparator
from app.core.generator import MigrationGenerator

router = APIRouter()


@router.post("/compare", response_model=AnalysisResult)
def compare_schemas(request: SchemaComparisonRequest):
    """Compare two SQL schemas and generate migration analysis.

    Args:
        request: Schema comparison request containing v1 and v2 SQL.

    Returns:
        Analysis result with detected changes, migration SQL, and warnings.

    Raises:
        HTTPException: If schema parsing fails.
    """
    # Parse schemas
    schema_v1 = parse_schema_safe(request.schema_v1, "v1", "Base Schema")
    schema_v2 = parse_schema_safe(request.schema_v2, "v2", "Destination Schema")

    # Compare schemas
    comparator = SchemaComparator()
    diffs = comparator.compare(schema_v1, schema_v2)

    # Generate migration SQL
    generator = MigrationGenerator()
    migration_sql, rollback_sql = generator.generate(diffs)

    # Validate SQL execution in sandbox (SQLite in-memory database)
    # Pass base schema (v1) so migration is tested against actual starting state
    validation_result = validate_sql_execution(migration_sql, rollback_sql, request.schema_v1)

    # Build comparison summary with warnings and transformed tables
    warnings, tables_to_report, summary_data = build_comparison_summary(diffs)

    # Initialize errors list
    errors = []

    # If sandbox validation failed, add error to the response
    if not validation_result["success"]:
        from app.api.schemas import ParseError

        error = ParseError(
            error_type="sql_execution_error",
            message=validation_result["error_message"],
            editor="sandbox",
            suggestion=f"The generated {validation_result['failed_script']} SQL failed to execute in SQLite. "
                      f"This may indicate a constraint violation, syntax issue, or unsupported operation."
        )
        errors.append(error)

        # Add a warning to the warnings list as well
        warnings.insert(0, f"⚠️ SQL Validation Failed: {validation_result['error_message']}")

    blast_radius_data = calculate_blast_radius(diffs)

    return AnalysisResult(
        status="success",
        changes_detected=ApiSchemaChanges(
            tables=tables_to_report,
            summary=summary_data
        ),
        migration_sql=migration_sql,
        rollback_sql=rollback_sql,
        blast_radius=blast_radius_data,
        errors=errors,
        warnings=warnings
    )


@router.post("/validate")
def validate_sql_migration(request: SchemaComparisonRequest):
    """Validate SQL migration in an in-memory SQLite sandbox.

    This endpoint validates that the 'New SQL' (schema_v2) can be successfully
    executed against the 'Base Schema' (schema_v1) in a single SQLite connection.

    Args:
        request: Schema comparison request where:
            - schema_v1: Base Schema SQL (tables, inserts, etc.)
            - schema_v2: New SQL to validate against the base

    Returns:
        JSON response with validation result:
        {
            "success": bool,
            "error_message": str | None,
            "blast_radius": str  # "CRITICAL" if validation fails
        }
    """
    conn = None
    try:
        import sqlite3

        # Open a single in-memory SQLite connection
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # First, execute the entire Base Schema
        if request.schema_v1 and request.schema_v1.strip():
            try:
                cursor.executescript(request.schema_v1)
                conn.commit()
            except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
                return {
                    "success": False,
                    "error_message": str(e),
                    "blast_radius": "CRITICAL"
                }

        # In the SAME connection, execute the New SQL
        try:
            cursor.executescript(request.schema_v2)
            conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.IntegrityError) as e:
            return {
                "success": False,
                "error_message": str(e),
                "blast_radius": "CRITICAL"
            }

        # Both executed successfully
        return {
            "success": True,
            "error_message": None,
            "blast_radius": "LOW"
        }

    except Exception as e:
        # Catch any unexpected errors
        return {
            "success": False,
            "error_message": str(e),
            "blast_radius": "CRITICAL"
        }
    finally:
        # Always close the connection
        if conn:
            conn.close()


# Made with Bob
