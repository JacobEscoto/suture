from typing import List, Optional, Dict
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
    references: Optional[tuple[str, str]] = None  # (table, column)
    change_type: str

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

class AnalysisResult(BaseModel):
    status: str  # "success", "error", "no_changes"
    changes_detected: SchemaChanges
    migration_sql: str
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
