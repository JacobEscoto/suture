from typing import List, Optional, Dict, Tuple, Any
from pydantic import BaseModel, Field

class SchemaComparisonRequest(BaseModel):
    schema_v1: str
    schema_v2: str

class ColumnChange(BaseModel):
    name: str
    data_type: Optional[str] = None
    nullable: Optional[bool] = None
    default: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    references: Optional[Tuple[str, str]] = None
    change_type: str
    old_data_type: Optional[str] = None
    old_nullable: Optional[bool] = None
    old_default: Optional[str] = None
    old_constraints: List[str] = Field(default_factory=list)
    old_references: Optional[Tuple[str, str]] = None

class ConstraintChange(BaseModel):
    name: Optional[str] = None
    constraint_type: str
    columns: List[str] = Field(default_factory=list)
    definition: str
    references: Optional[tuple[str, List[str]]] = None  # (table, columns)
    change_type: str

class IndexChange(BaseModel):
    name: str
    table: str
    columns: List[str]
    unique: bool = False
    index_type: Optional[str] = None
    change_type: str

class TableChange(BaseModel):
    name: str
    change_type: str
    columns: List[ColumnChange] = Field(default_factory=list)
    constraints: List[ConstraintChange] = Field(default_factory=list)
    indexes: List[IndexChange] = Field(default_factory=list)

class SchemaChanges(BaseModel):
    tables: List[TableChange] = Field(default_factory=list)
    indexes: List[IndexChange] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)

class ParseError(BaseModel):
    error_type: str
    message: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    statement: Optional[str] = None
    suggestion: Optional[str] = None
    editor: str

class AnalysisResult(BaseModel):
    status: str
    changes_detected: SchemaChanges
    migration_sql: str
    rollback_sql: str
    blast_radius: Dict[str, Any]
    errors: List[ParseError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
