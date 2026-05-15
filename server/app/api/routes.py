from fastapi import APIRouter, HTTPException
from app.api.schemas import SchemaComparisonRequest, AnalysisResult, SchemaChanges as ApiSchemaChanges, TableChange as ApiTableChange
from app.core.parser import SQLParser
from app.core.comparator import SchemaComparator
from app.core.generator import MigrationGenerator

router = APIRouter()

@router.post("/compare", response_model=AnalysisResult)
async def compare_schemas(request: SchemaComparisonRequest):
    try:
        parser = SQLParser()
        schema_v1 = parser.parse(request.schema_v1)
        schema_v2 = parser.parse(request.schema_v2)

        comparator = SchemaComparator()
        diffs = comparator.compare(schema_v1, schema_v2)

        generator = MigrationGenerator()
        migration_sql, rollback_sql = generator.generate(diffs)

        sql_script = (
            "-- MIGRATION SCRIPT\n"
            f"{migration_sql}\n\n"
            "-- ROLLBACK SCRIPT\n"
            f"{rollback_sql}"
        )

        tables_to_report = []

        for table in diffs.tables_added:
            tables_to_report.append(ApiTableChange(
                name=table.name,
                change_type="added"
            ))

        for table in diffs.tables_deleted:
            tables_to_report.append(ApiTableChange(
                name=table.name,
                change_type="deleted"
            ))

        for table in diffs.tables_modified:
            tables_to_report.append(ApiTableChange(
                name=table.table_name,
                change_type=table.change_type
            ))

        status = "success" if diffs.has_changes() else "no_changes"

        return AnalysisResult(
            status=status,
            changes_detected=ApiSchemaChanges(
                tables=tables_to_report,
                summary=diffs.get_summary()
            ),
            migration_sql=sql_script,
            errors=[],
            warnings=[]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))