# Suturé Frontend Enhancement - Implementation Plan

This document provides detailed implementation steps and code examples for enhancing the Suturé frontend to better leverage backend data.

---

## Phase 1: Backend API Enhancement (CRITICAL - Must be done first)

### Step 1.1: Enhance API Response Schema

**File:** `server/app/api/schemas.py`

Add support for old values in column changes and structured errors:

```python
class ColumnChange(BaseModel):
    name: str
    data_type: Optional[str] = None
    nullable: Optional[bool] = None
    default: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    references: Optional[tuple[str, str]] = None
    change_type: str
    # Add old values for modified columns
    old_data_type: Optional[str] = None
    old_nullable: Optional[bool] = None
    old_default: Optional[str] = None
    old_constraints: List[str] = Field(default_factory=list)
    old_references: Optional[tuple[str, str]] = None

class ParseError(BaseModel):
    error_type: str
    message: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    statement: Optional[str] = None
    suggestion: Optional[str] = None
    editor: str  # "v1" or "v2"

class AnalysisResult(BaseModel):
    status: str
    changes_detected: SchemaChanges
    migration_sql: str
    errors: List[ParseError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
```

### Step 1.2: Populate Complete Table Changes

**File:** `server/app/api/routes.py`

Replace lines 29-47 with complete data population:

```python
for table in diffs.tables_modified:
    # Convert columns_added
    columns_added = [
        ColumnChange(
            name=col.name,
            data_type=col.data_type,
            nullable=col.nullable,
            default=col.default,
            constraints=col.constraints,
            references=col.references,
            change_type="added"
        ) for col in table.columns_added
    ]

    # Convert columns_deleted
    columns_deleted = [
        ColumnChange(
            name=col.name,
            data_type=col.data_type,
            nullable=col.nullable,
            default=col.default,
            constraints=col.constraints,
            references=col.references,
            change_type="deleted"
        ) for col in table.columns_deleted
    ]

    # Convert columns_modified with old/new values
    columns_modified = [
        ColumnChange(
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
        ) for col_change in table.columns_modified
    ]

    # Convert constraints
    constraints_added = [
        ConstraintChange(
            name=const.name,
            constraint_type=const.constraint_type.value,
            columns=const.columns,
            definition=const.definition,
            references=const.references,
            change_type="added"
        ) for const in table.constraints_added
    ]

    constraints_deleted = [
        ConstraintChange(
            name=const.name,
            constraint_type=const.constraint_type.value,
            columns=const.columns,
            definition=const.definition,
            references=const.references,
            change_type="deleted"
        ) for const in table.constraints_deleted
    ]

    # Convert indexes
    indexes_added = [
        IndexChange(
            name=idx.name,
            table=idx.table,
            columns=idx.columns,
            unique=idx.unique,
            index_type=idx.index_type,
            change_type="added"
        ) for idx in table.indexes_added
    ]

    indexes_deleted = [
        IndexChange(
            name=idx.name,
            table=idx.table,
            columns=idx.columns,
            unique=idx.unique,
            index_type=idx.index_type,
            change_type="deleted"
        ) for idx in table.indexes_deleted
    ]

    tables_to_report.append(ApiTableChange(
        name=table.table_name,
        change_type=table.change_type,
        columns=columns_added + columns_deleted + columns_modified,
        constraints=constraints_added + constraints_deleted,
        indexes=indexes_added + indexes_deleted
    ))
```

### Step 1.3: Add Warning Generation

**File:** `server/app/api/routes.py`

Add after line 48 (before return statement):

```python
# Generate warnings for risky operations
warnings = []

for table in diffs.tables_deleted:
    warnings.append(f"⚠️ Table '{table.name}' will be dropped - data loss will occur")

for table in diffs.tables_modified:
    for col in table.columns_deleted:
        warnings.append(f"⚠️ Column '{table.table_name}.{col.name}' will be dropped - data loss will occur")

    for col_change in table.columns_modified:
        if col_change.old_definition and col_change.new_definition:
            old_type = col_change.old_definition.data_type
            new_type = col_change.new_definition.data_type
            if old_type != new_type:
                warnings.append(
                    f"⚠️ Column '{table.table_name}.{col_change.column_name}' "
                    f"type change ({old_type} → {new_type}) may require data casting"
                )

            # Check for NOT NULL addition on existing column
            if col_change.old_definition.nullable and not col_change.new_definition.nullable:
                warnings.append(
                    f"⚠️ Column '{table.table_name}.{col_change.column_name}' "
                    f"adding NOT NULL constraint - ensure no NULL values exist"
                )
```

### Step 1.4: Enhanced Error Handling

**File:** `server/app/api/routes.py`

Wrap the entire function body in better error handling:

```python
@router.post("/compare", response_model=AnalysisResult)
async def compare_schemas(request: SchemaComparisonRequest):
    errors = []
    warnings = []

    try:
        parser = SQLParser()

        # Parse v1 with error tracking
        try:
            schema_v1 = parser.parse(request.schema_v1)
        except Exception as e:
            errors.append(ParseError(
                error_type="parse_error",
                message=str(e),
                editor="v1",
                suggestion="Check SQL syntax in Base Schema"
            ))
            raise HTTPException(status_code=400, detail={
                "message": "Failed to parse Base Schema",
                "errors": [{"error_type": err.error_type, "message": err.message,
                           "editor": err.editor, "suggestion": err.suggestion} for err in errors]
            })

        # Parse v2 with error tracking
        try:
            schema_v2 = parser.parse(request.schema_v2)
        except Exception as e:
            errors.append(ParseError(
                error_type="parse_error",
                message=str(e),
                editor="v2",
                suggestion="Check SQL syntax in Destination Schema"
            ))
            raise HTTPException(status_code=400, detail={
                "message": "Failed to parse Destination Schema",
                "errors": [{"error_type": err.error_type, "message": err.message,
                           "editor": err.editor, "suggestion": err.suggestion} for err in errors]
            })

        # Continue with comparison...
        comparator = SchemaComparator()
        diffs = comparator.compare(schema_v1, schema_v2)

        generator = MigrationGenerator()
        migration_sql, rollback_sql = generator.generate(diffs)

        # ... rest of existing code ...

        return AnalysisResult(
            status=status,
            changes_detected=ApiSchemaChanges(...),
            migration_sql=sql_script,
            errors=[],
            warnings=warnings
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Phase 2: Frontend Type Definitions

### Step 2.1: Update TypeScript Interfaces

**File:** `client/types/api.d.ts`

Replace the entire file content:

```typescript
export interface SchemaComparisonRequest {
  schema_v1: string;
  schema_v2: string;
}

export interface ColumnChange {
  name: string;
  data_type?: string | null;
  nullable?: boolean | null;
  default?: string | null;
  constraints: string[];
  references?: [string, string] | null;
  change_type: 'added' | 'deleted' | 'modified';
  // Old values for comparison
  old_data_type?: string | null;
  old_nullable?: boolean | null;
  old_default?: string | null;
  old_constraints?: string[];
  old_references?: [string, string] | null;
}

export interface ConstraintChange {
  name?: string | null;
  constraint_type: string;
  columns: string[];
  definition: string;
  references?: [string, string[]] | null;
  change_type: string;
}

export interface IndexChange {
  name: string;
  table: string;
  columns: string[];
  unique: boolean;
  index_type?: string | null;
  change_type: string;
}

export interface TableChange {
  name: string;
  change_type: string;
  columns: ColumnChange[];
  constraints: ConstraintChange[];
  indexes: IndexChange[];
}

export interface SchemaChanges {
  tables: TableChange[];
  indexes: IndexChange[];
  summary: Record<string, number>;
}

export interface ParseError {
  error_type: string;
  message: string;
  line_number?: number | null;
  column_number?: number | null;
  statement?: string | null;
  suggestion?: string | null;
  editor: 'v1' | 'v2';
}

export interface AnalysisResult {
  status: string;
  changes_detected: SchemaChanges;
  migration_sql: string;
  errors: ParseError[];
  warnings: string[];
}

// Utility types for UI
export interface ColumnDiff {
  column: ColumnChange;
  hasTypeChange: boolean;
  hasNullabilityChange: boolean;
  hasDefaultChange: boolean;
  hasConstraintChange: boolean;
  riskLevel: 'safe' | 'caution' | 'danger' | 'critical';
}

export interface TableChangeEnhanced extends TableChange {
  totalChanges: number;
  riskLevel: 'safe' | 'caution' | 'danger' | 'critical';
  affectedColumns: number;
  affectedConstraints: number;
  affectedIndexes: number;
}
```

---

## Phase 3: Enhanced UI Components

### Step 3.1: Create TableChangeCard Component

**New File:** `client/components/results/TableChangeCard.tsx`

```typescript
'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import { TableChange, ColumnChange } from '@/types/api';

interface TableChangeCardProps {
  table: TableChange;
}

export default function TableChangeCard({ table }: TableChangeCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const columnsAdded = table.columns.filter(c => c.change_type === 'added');
  const columnsDeleted = table.columns.filter(c => c.change_type === 'deleted');
  const columnsModified = table.columns.filter(c => c.change_type === 'modified');

  const constraintsAdded = table.constraints.filter(c => c.change_type === 'added');
  const constraintsDeleted = table.constraints.filter(c => c.change_type === 'deleted');

  const indexesAdded = table.indexes.filter(i => i.change_type === 'added');
  const indexesDeleted = table.indexes.filter(i => i.change_type === 'deleted');

  const totalChanges =
    columnsAdded.length + columnsDeleted.length + columnsModified.length +
    constraintsAdded.length + constraintsDeleted.length +
    indexesAdded.length + indexesDeleted.length;

  const badgeColors =
    table.change_type === 'added' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
    table.change_type === 'deleted' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
    'bg-amber-500/10 text-amber-400 border-amber-500/20';

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-zinc-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <span className={`px-3 py-1 text-xs font-mono font-medium rounded-lg border ${badgeColors}`}>
            {table.name}
          </span>
          <span className="text-xs text-zinc-500">
            {totalChanges} {totalChanges === 1 ? 'change' : 'changes'}
          </span>
        </div>
        <span className="text-xs text-zinc-400 uppercase tracking-wider">
          {table.change_type}
        </span>
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-zinc-800">
          {columnsAdded.length > 0 && (
            <div className="pt-4">
              <h4 className="text-xs font-semibold text-emerald-400 mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-400 rounded-full"></span>
                Columns Added ({columnsAdded.length})
              </h4>
              <div className="space-y-2">
                {columnsAdded.map((col, idx) => (
                  <ColumnDetail key={idx} column={col} />
                ))}
              </div>
            </div>
          )}

          {columnsModified.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-amber-400 mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-amber-400 rounded-full"></span>
                Columns Modified ({columnsModified.length})
              </h4>
              <div className="space-y-2">
                {columnsModified.map((col, idx) => (
                  <ColumnDiffDetail key={idx} column={col} />
                ))}
              </div>
            </div>
          )}

          {columnsDeleted.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-rose-400 mb-2 flex items-center gap-2">
                <AlertTriangle className="w-3 h-3" />
                Columns Deleted ({columnsDeleted.length})
              </h4>
              <div className="space-y-2">
                {columnsDeleted.map((col, idx) => (
                  <ColumnDetail key={idx} column={col} showWarning />
                ))}
              </div>
            </div>
          )}

          {(constraintsAdded.length > 0 || constraintsDeleted.length > 0) && (
            <div>
              <h4 className="text-xs font-semibold text-indigo-400 mb-2">
                Constraints ({constraintsAdded.length} added, {constraintsDeleted.length} deleted)
              </h4>
              <div className="space-y-1 text-xs font-mono text-zinc-400">
                {constraintsAdded.map((c, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-400">+</span>
                    <span>{c.constraint_type} ({c.columns.join(', ')})</span>
                  </div>
                ))}
                {constraintsDeleted.map((c, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-rose-400">-</span>
                    <span>{c.constraint_type} ({c.columns.join(', ')})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(indexesAdded.length > 0 || indexesDeleted.length > 0) && (
            <div>
              <h4 className="text-xs font-semibold text-purple-400 mb-2">
                Indexes ({indexesAdded.length} added, {indexesDeleted.length} deleted)
              </h4>
              <div className="space-y-1 text-xs font-mono text-zinc-400">
                {indexesAdded.map((idx, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-emerald-400">+</span>
                    <span>{idx.name} ON ({idx.columns.join(', ')})</span>
                  </div>
                ))}
                {indexesDeleted.map((idx, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-rose-400">-</span>
                    <span>{idx.name} ON ({idx.columns.join(', ')})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ColumnDetail({ column, showWarning = false }: { column: ColumnChange; showWarning?: boolean }) {
  return (
    <div className="bg-zinc-800/50 rounded-lg p-3 text-xs font-mono">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="font-semibold text-zinc-200">{column.name}</div>
          <div className="text-zinc-400 mt-1">
            {column.data_type}
            {!column.nullable && <span className="ml-2 text-amber-400">NOT NULL</span>}
            {column.default && <span className="ml-2 text-indigo-400">DEFAULT {column.default}</span>}
          </div>
          {column.constraints.length > 0 && (
            <div className="text-zinc-500 mt-1">
              {column.constraints.join(', ')}
            </div>
          )}
        </div>
        {showWarning && (
          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
        )}
      </div>
    </div>
  );
}

function ColumnDiffDetail({ column }: { column: ColumnChange }) {
  const hasTypeChange = column.old_data_type && column.old_data_type !== column.data_type;
  const hasNullabilityChange = column.old_nullable !== undefined && column.old_nullable !== column.nullable;
  const hasDefaultChange = column.old_default !== column.default;

  return (
    <div className="bg-zinc-800/50 rounded-lg p-3 text-xs font-mono">
      <div className="font-semibold text-zinc-200 mb-2">{column.name}</div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-zinc-500 mb-1">Before (v1)</div>
          <div className="text-zinc-400">
            {column.old_data_type || column.data_type}
            {column.old_nullable === false && <span className="ml-2 text-amber-400">NOT NULL</span>}
            {column.old_default && <span className="ml-2 text-indigo-400">DEFAULT {column.old_default}</span>}
          </div>
        </div>

        <div>
          <div className="text-zinc-500 mb-1">After (v2)</div>
          <div className="text-zinc-400">
            {column.data_type}
            {column.nullable === false && <span className="ml-2 text-amber-400">NOT NULL</span>}
            {column.default && <span className="ml-2 text-indigo-400">DEFAULT {column.default}</span>}
          </div>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        {hasTypeChange && (
          <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded text-[10px]">
            Type Changed
          </span>
        )}
        {hasNullabilityChange && (
          <span className="px-2 py-0.5 bg-orange-500/10 text-orange-400 rounded text-[10px]">
            Nullability Changed
          </span>
        )}
        {hasDefaultChange && (
          <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-[10px]">
            Default Changed
          </span>
        )}
      </div>
    </div>
  );
}
```

### Step 3.2: Update ComparisonResults Component

**File:** `client/components/results/ComparisonResults.tsx`

Add import and replace the "Changes Detected" section:

```typescript
import TableChangeCard from './TableChangeCard';

// ... in the component, replace the "Changes Detected" section with:

<div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6 flex flex-col gap-4">
  <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">Detailed Changes</h3>
  <div className="space-y-3">
    {changes_detected.tables.map((table, idx) => (
      <TableChangeCard key={idx} table={table} />
    ))}
    {changes_detected.tables.length === 0 && (
      <span className="text-sm text-zinc-500 font-medium">No structural changes were detected in the tables.</span>
    )}
  </div>
</div>
```

### Step 3.3: Add Warnings Display

**File:** `client/components/results/ComparisonResults.tsx`

Add after the opening div and before summary cards:

```typescript
{warnings && warnings.length > 0 && (
  <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
    <div className="flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <h3 className="text-sm font-semibold text-amber-400 mb-2">Migration Warnings</h3>
        <ul className="space-y-1 text-xs text-amber-300/80">
          {warnings.map((warning, idx) => (
            <li key={idx}>{warning}</li>
          ))}
        </ul>
      </div>
    </div>
  </div>
)}
```

---

See ADVANCED_FEATURES.md for editor integration and real-time validation features.