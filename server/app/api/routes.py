from fastapi import APIRouter
from app.api.schemas import (
    SchemaComparisonRequest,
    AnalysisResult,
    SchemaChanges as ApiSchemaChanges,
)
from app.api.helpers import (
    parse_schema_safe,
    build_comparison_summary,
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

    # Build comparison summary with warnings and transformed tables
    warnings, tables_to_report, summary_data = build_comparison_summary(diffs)

    return AnalysisResult(
        status="success",
        changes_detected=ApiSchemaChanges(
            tables=tables_to_report,
            summary=summary_data
        ),
        migration_sql=migration_sql,
        errors=[],
        warnings=warnings
    )

# Made with Bob
