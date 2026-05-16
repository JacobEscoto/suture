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
  change_type: 'added' | 'deleted';
}

export interface IndexChange {
  name: string;
  table: string;
  columns: string[];
  unique: boolean;
  index_type?: string | null;
  change_type: 'added' | 'deleted';
}

export interface TableChange {
  name: string;
  change_type: 'added' | 'deleted' | 'modified';
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