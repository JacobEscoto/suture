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
  references?: [string, string] | null;  // [table, column]
  change_type: string;
}

export interface ConstraintChange {
  name?: string | null;
  constraint_type: string;
  columns: string[];
  definition: string;
  references?: [string, string[]] | null;  // [table, columns]
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

export interface AnalysisResult {
  status: string;
  changes_detected: SchemaChanges;
  migration_sql: string;
  errors: string[];
  warnings: string[];
}