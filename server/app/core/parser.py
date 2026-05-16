"""
SQL Parser Module for Suturé

This module provides SQL parsing capabilities to extract schema information
from SQL scripts. It supports multiple SQL dialects with a focus on PostgreSQL.

Python Version: 3.13+
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import sqlparse
from sqlparse.sql import Parenthesis, Statement
from sqlparse.tokens import DDL, Keyword, Name

logger = logging.getLogger(__name__)

# Token-type helpers

_NAME_TYPES = (Name, Name.Builtin)

# Keywords to skip when searching for an identifier after TABLE / ALTER TABLE
_SKIP_KEYWORDS = frozenset({"IF", "NOT", "EXISTS", "TEMPORARY", "TEMP", "OR", "REPLACE"})

# DDL and Keyword are the two ttype groups that can carry SQL keywords
_DDL_OR_KEYWORD = (DDL, Keyword)


# Enums
class SQLDialect(Enum):
    """Supported SQL dialects."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SUPABASE = "supabase"  # PostgreSQL-based


class ConstraintType(Enum):
    """Database constraint types."""

    PRIMARY_KEY = "PRIMARY KEY"
    FOREIGN_KEY = "FOREIGN KEY"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    NOT_NULL = "NOT NULL"
    DEFAULT = "DEFAULT"


# Dataclasses

@dataclass
class ColumnDefinition:
    """Represents a database column definition."""

    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    references: Optional[Tuple[str, str]] = None  # (table, column)

    def __repr__(self) -> str:
        return f"Column({self.name}: {self.data_type})"


@dataclass
class IndexDefinition:
    """Represents a database index."""

    name: str
    table: str
    columns: List[str]
    unique: bool = False
    index_type: Optional[str] = None  # BTREE, HASH, etc.

    def __repr__(self) -> str:
        return f"Index({self.name} on {self.table})"


@dataclass
class ConstraintDefinition:
    """Represents a table constraint."""

    name: Optional[str]
    constraint_type: ConstraintType
    columns: List[str]
    definition: str
    references: Optional[Tuple[str, List[str]]] = None  # (table, columns)

    def __repr__(self) -> str:
        return f"Constraint({self.constraint_type.value})"


@dataclass
class TableDefinition:
    """Represents a complete table definition."""

    name: str
    columns: Dict[str, ColumnDefinition] = field(default_factory=dict)
    constraints: List[ConstraintDefinition] = field(default_factory=list)
    indexes: List[IndexDefinition] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Table({self.name}, {len(self.columns)} columns)"


@dataclass
class SchemaDefinition:
    """Represents a complete database schema."""

    tables: Dict[str, TableDefinition] = field(default_factory=dict)
    indexes: List[IndexDefinition] = field(default_factory=list)
    dialect: SQLDialect = SQLDialect.POSTGRESQL

    def __repr__(self) -> str:
        return f"Schema({len(self.tables)} tables, {len(self.indexes)} indexes)"


class SQLParser:
    """
    SQL Parser for extracting schema information from SQL scripts.

    Supports PostgreSQL, MySQL, and Supabase (PostgreSQL-based) dialects.
    Uses sqlparse for tokenization and custom logic for schema extraction.
    """

    def __init__(self, dialect: SQLDialect = SQLDialect.POSTGRESQL) -> None:
        self.dialect = dialect

    def parse(self, sql_script: str) -> SchemaDefinition:
        """
        Parse a SQL script and extract schema information.

        Args:
            sql_script: The SQL script content to parse.

        Returns:
            SchemaDefinition object containing all extracted schema information.

        Raises:
            ValueError: If the SQL script is empty.
        """
        if not sql_script or not sql_script.strip():
            raise ValueError("SQL script cannot be empty")

        cleaned_sql = self._clean_sql(sql_script)
        statements = sqlparse.parse(cleaned_sql)
        schema = SchemaDefinition(dialect=self.dialect)

        for statement in statements:
            try:
                self._process_statement(statement, schema)
            except Exception as exc:
                logger.warning("Failed to process statement: %s — %s", statement, exc)

        return schema

    @staticmethod
    def _clean_sql(sql_script: str) -> str:
        """Strip comments and normalise whitespace."""
        sql_script = sqlparse.format(sql_script, strip_comments=True, reindent=False)
        return re.sub(r"\s+", " ", sql_script).strip()

    def _process_statement(self, statement: Statement, schema: SchemaDefinition) -> None:
        stmt_type = statement.get_type()
        if stmt_type == "CREATE":
            self._process_create_statement(statement, schema)
        elif stmt_type == "ALTER":
            self._process_alter_statement(statement, schema)

    def _process_create_statement(self, statement: Statement, schema: SchemaDefinition) -> None:
        """Dispatch CREATE TABLE / CREATE [UNIQUE] INDEX."""
        tokens = list(statement.flatten())
        create_type: Optional[str] = None
        is_unique = False

        for i, token in enumerate(tokens):
            if token.ttype is DDL and token.value.upper() == "CREATE":
                for j in range(i + 1, min(i + 10, len(tokens))):
                    ttype = tokens[j].ttype
                    val = tokens[j].value.upper()

                    if ttype not in _DDL_OR_KEYWORD:
                        continue
                    if val in _SKIP_KEYWORDS:
                        continue
                    if val == "UNIQUE":
                        is_unique = True
                        continue

                    create_type = val
                    break
                break

        if create_type == "TABLE":
            self._process_create_table(statement, schema)
        elif create_type == "INDEX":
            self._process_create_index(statement, schema, unique=is_unique)

    def _process_create_table(self, statement: Statement, schema: SchemaDefinition) -> None:
        table_name = self._extract_table_name(statement)
        if not table_name:
            logger.warning("Could not extract table name from: %s", statement)
            return

        table_def = TableDefinition(name=table_name)
        self._extract_table_body(statement, table_def)
        schema.tables[table_name] = table_def

    def _extract_table_name(self, statement: Statement) -> Optional[str]:
        """
        Extract the table name, handling IF NOT EXISTS and all quote styles.
        """
        tokens = list(statement.flatten())
        found_table_kw = False

        for token in tokens:
            ttype = token.ttype
            val_upper = token.value.upper()

            if not found_table_kw:
                # TABLE can appear as Keyword or DDL (depending on sqlparse version)
                if ttype in _DDL_OR_KEYWORD and val_upper == "TABLE":
                    found_table_kw = True
                continue

            # Skip modifier keywords (IF NOT EXISTS, TEMPORARY …)
            if ttype in _DDL_OR_KEYWORD and val_upper in _SKIP_KEYWORDS:
                continue

            # First real identifier is the table name
            if ttype in _NAME_TYPES:
                return token.value.strip('"').strip("`").strip("'")

        return None

    def _extract_table_body(self, statement: Statement, table_def: TableDefinition) -> None:
        for token in statement.tokens:
            if isinstance(token, Parenthesis):
                self._parse_table_columns(token, table_def)
                break

    def _parse_table_columns(self, parenthesis: Parenthesis, table_def: TableDefinition) -> None:
        for raw_def in self._split_by_comma(parenthesis):
            definition_str = raw_def.strip()
            if not definition_str:
                continue

            if self._is_table_constraint(definition_str):
                constraint = self._parse_table_constraint(definition_str)
                if constraint:
                    table_def.constraints.append(constraint)
            else:
                column = self._parse_column_definition(definition_str)
                if column:
                    table_def.columns[column.name] = column

    @staticmethod
    def _split_by_comma(parenthesis: Parenthesis) -> List[str]:
        """
        Split parenthesis content by commas, respecting nested parentheses
        and single/double quoted strings.
        """
        content = str(parenthesis)[1:-1]  # Remove outer ( )
        definitions: List[str] = []
        current: List[str] = []
        depth = 0
        in_quote: Optional[str] = None

        for char in content:
            if in_quote:
                current.append(char)
                if char == in_quote:
                    in_quote = None
            elif char in ("'", '"'):
                in_quote = char
                current.append(char)
            elif char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                definitions.append("".join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            definitions.append("".join(current).strip())

        return definitions

    def _parse_column_definition(self, definition: str) -> Optional[ColumnDefinition]:
        """Parse a single column definition line."""
        parts = definition.split()
        if len(parts) < 2:
            return None

        col_name = parts[0].strip('"').strip("`").strip("'")

        type_match = re.match(r"^\s*\S+\s+(\w+\s*(?:\([^)]*\))?)", definition, re.IGNORECASE)
        col_type = type_match.group(1).strip().upper() if type_match else parts[1].upper()

        column = ColumnDefinition(name=col_name, data_type=col_type)
        definition_upper = definition.upper()

        if "NOT NULL" in definition_upper:
            column.nullable = False
            column.constraints.append("NOT NULL")

        if "PRIMARY KEY" in definition_upper:
            column.constraints.append("PRIMARY KEY")

        if re.search(r"\bUNIQUE\b", definition_upper):
            column.constraints.append("UNIQUE")

        default_value = self._extract_default_value(definition)
        if default_value is not None:
            column.default = default_value
            column.constraints.append(f"DEFAULT {default_value}")

        ref_match = re.search(
            r"\bREFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)",
            definition,
            re.IGNORECASE,
        )
        if ref_match:
            column.references = (ref_match.group(1), ref_match.group(2))
            column.constraints.append(
                f"REFERENCES {ref_match.group(1)}({ref_match.group(2)})"
            )

        return column

    @staticmethod
    def _extract_default_value(definition: str) -> Optional[str]:
        """
        Robustly extract the DEFAULT value from a column definition string.

        Handles:
        - Simple literals:        DEFAULT 0, DEFAULT true
        - Quoted strings:         DEFAULT 'hello world'
        - Functions:              DEFAULT NOW(), DEFAULT gen_random_uuid()
        - Multi-word expressions: DEFAULT CURRENT_TIMESTAMP
        - Negative numbers:       DEFAULT -1
        """
        match = re.search(r"\bDEFAULT\b", definition, re.IGNORECASE)
        if not match:
            return None

        rest = definition[match.end():].lstrip()

        # Patterns that signal the end of the DEFAULT value
        _stop = re.compile(
            r"\b(NOT\s+NULL|NULL|PRIMARY\s+KEY|UNIQUE|CHECK|REFERENCES)\b",
            re.IGNORECASE,
        )

        result: List[str] = []
        depth = 0
        in_quote: Optional[str] = None
        i = 0

        while i < len(rest):
            char = rest[i]

            if in_quote:
                result.append(char)
                # Handle escaped quotes inside strings
                if char == in_quote and (i == 0 or rest[i - 1] != "\\"):
                    in_quote = None
            elif char in ("'", '"'):
                in_quote = char
                result.append(char)
            elif char == "(":
                depth += 1
                result.append(char)
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
                result.append(char)
            elif char == "," and depth == 0:
                break
            else:
                # Check for stop-word only at depth 0
                if depth == 0:
                    stop_match = _stop.match(rest[i:])
                    if stop_match:
                        break
                result.append(char)
            i += 1

        value = "".join(result).strip()
        return value if value else None


    @staticmethod
    def _is_table_constraint(definition: str) -> bool:
        definition_upper = definition.upper()
        return any(
            kw in definition_upper
            for kw in ("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT")
        )

    def _parse_table_constraint(self, definition: str) -> Optional[ConstraintDefinition]:
        definition_upper = definition.upper()

        constraint_name: Optional[str] = None
        name_match = re.search(r"\bCONSTRAINT\s+(\w+)", definition, re.IGNORECASE)
        if name_match:
            constraint_name = name_match.group(1)

        if "PRIMARY KEY" in definition_upper:
            columns = self._extract_constraint_columns(definition, "PRIMARY KEY")
            return ConstraintDefinition(
                name=constraint_name,
                constraint_type=ConstraintType.PRIMARY_KEY,
                columns=columns,
                definition=definition,
            )

        if "FOREIGN KEY" in definition_upper:
            columns = self._extract_constraint_columns(definition, "FOREIGN KEY")
            ref_match = re.search(
                r"\bREFERENCES\s+(\w+)\s*\(([^)]+)\)",
                definition,
                re.IGNORECASE,
            )
            references: Optional[Tuple[str, List[str]]] = None
            if ref_match:
                ref_table = ref_match.group(1)
                ref_cols = [
                    c.strip().strip('"').strip("`").strip("'")
                    for c in ref_match.group(2).split(",")
                ]
                references = (ref_table, ref_cols)

            return ConstraintDefinition(
                name=constraint_name,
                constraint_type=ConstraintType.FOREIGN_KEY,
                columns=columns,
                definition=definition,
                references=references,
            )

        if re.search(r"\bUNIQUE\b", definition_upper):
            columns = self._extract_constraint_columns(definition, "UNIQUE")
            return ConstraintDefinition(
                name=constraint_name,
                constraint_type=ConstraintType.UNIQUE,
                columns=columns,
                definition=definition,
            )

        if "CHECK" in definition_upper:
            return ConstraintDefinition(
                name=constraint_name,
                constraint_type=ConstraintType.CHECK,
                columns=[],
                definition=definition,
            )

        return None

    @staticmethod
    def _extract_constraint_columns(definition: str, constraint_type: str) -> List[str]:
        pattern = rf"\b{re.escape(constraint_type)}\s*\(([^)]+)\)"
        match = re.search(pattern, definition, re.IGNORECASE)
        if match:
            return [
                col.strip().strip('"').strip("`").strip("'")
                for col in match.group(1).split(",")
            ]
        return []

    # Create INDEX
    def _process_create_index(
        self,
        statement: Statement,
        schema: SchemaDefinition,
        unique: bool = False,
    ) -> None:
        """
        Parse CREATE [UNIQUE] INDEX statement.

        sqlparse may tokenize 'table(col1, col2)' as a Function token,
        so we need to handle both Parenthesis and Function token types.
        """
        tokens = list(statement.flatten())
        index_name: Optional[str] = None
        table_name: Optional[str] = None
        columns: List[str] = []

        # Index name follows INDEX keyword
        for i, token in enumerate(tokens):
            if token.ttype in _DDL_OR_KEYWORD and token.value.upper() == "INDEX":
                for j in range(i + 1, len(tokens)):
                    if tokens[j].ttype in _NAME_TYPES:
                        index_name = tokens[j].value.strip('"').strip("`").strip("'")
                        break
                break

        # After ON keyword, we may have either:
        # 1. Separate tokens: table_name ( col1, col2 )
        # 2. Function token: table_name(col1, col2)
        # We need to handle both cases

        # First, try to find a Function token (e.g., "users(username)")
        from sqlparse.sql import Function
        for token in statement.tokens:
            if isinstance(token, Function):
                # Extract table name and columns from function token
                func_str = str(token)
                if '(' in func_str:
                    table_name = func_str[:func_str.index('(')].strip().strip('"').strip("`").strip("'")
                    cols_str = func_str[func_str.index('(')+1:func_str.rindex(')')].strip()
                    columns = [
                        col.strip().strip('"').strip("`").strip("'")
                        for col in cols_str.split(",")
                        if col.strip()
                    ]
                break

        # If no Function token found, try the traditional approach
        if not table_name:
            # Table name follows ON keyword
            for i, token in enumerate(tokens):
                if token.ttype in _DDL_OR_KEYWORD and token.value.upper() == "ON":
                    for j in range(i + 1, len(tokens)):
                        if tokens[j].ttype in _NAME_TYPES:
                            table_name = tokens[j].value.strip('"').strip("`").strip("'")
                            break
                    break

        # If no columns yet, look for Parenthesis token
        if not columns:
            for token in statement.tokens:
                if isinstance(token, Parenthesis):
                    cols_str = str(token)[1:-1].strip()
                    columns = [
                        col.strip().strip('"').strip("`").strip("'")
                        for col in cols_str.split(",")
                        if col.strip()
                    ]
                    break

        if not (index_name and table_name and columns):
            logger.warning(
                "Incomplete CREATE INDEX — name=%s, table=%s, columns=%s",
                index_name,
                table_name,
                columns,
            )
            return

        index_def = IndexDefinition(
            name=index_name,   # type: ignore[arg-type]
            table=table_name,  # type: ignore[arg-type]
            columns=columns,
            unique=unique,
        )

        # Associate index with its table if the table exists
        if table_name in schema.tables:
            schema.tables[table_name].indexes.append(index_def)
            logger.debug("Index '%s' added to table '%s'", index_name, table_name)
        else:
            # If table doesn't exist yet, add to schema-level indexes
            schema.indexes.append(index_def)
            logger.debug("Index '%s' added to schema-level indexes (table '%s' not found)", index_name, table_name)

    # Alter table
    def _process_alter_statement(self, statement: Statement, schema: SchemaDefinition) -> None:
        """
        Process ALTER TABLE statements.

        Supported operations:
        - ADD COLUMN
        - ADD CONSTRAINT (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK)
        - DROP COLUMN [IF EXISTS]
        """
        tokens = list(statement.flatten())
        table_name: Optional[str] = None
        found_alter = False
        found_table_kw = False

        for token in tokens:
            ttype = token.ttype
            val_upper = token.value.upper()

            if not found_alter:
                if ttype is DDL and val_upper == "ALTER":
                    found_alter = True
                continue

            if not found_table_kw:
                if ttype in _DDL_OR_KEYWORD and val_upper == "TABLE":
                    found_table_kw = True
                continue

            if ttype in _DDL_OR_KEYWORD and val_upper in _SKIP_KEYWORDS:
                continue

            if ttype in _NAME_TYPES:
                table_name = token.value.strip('"').strip("`").strip("'")
                break

        if not table_name:
            logger.warning("Could not extract table name from ALTER: %s", statement)
            return

        if table_name not in schema.tables:
            logger.warning("ALTER TABLE references unknown table '%s' — skipping.", table_name)
            return

        table_def = schema.tables[table_name]
        raw = statement.value

        # Add column / Add constraint
        add_match = re.search(
            r"\bADD\s+(?:COLUMN\s+)?(.+?)(?:\s*;?\s*$)",
            raw,
            re.IGNORECASE | re.DOTALL,
        )
        if add_match:
            added = add_match.group(1).strip().rstrip(";").strip()
            if self._is_table_constraint(added):
                constraint = self._parse_table_constraint(added)
                if constraint:
                    table_def.constraints.append(constraint)
            else:
                col = self._parse_column_definition(added)
                if col:
                    table_def.columns[col.name] = col
            return

        # Drop column if exists
        drop_match = re.search(
            r"\bDROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?(\w+)",
            raw,
            re.IGNORECASE,
        )
        if drop_match:
            col_name = drop_match.group(1).strip('"').strip("`").strip("'")
            if col_name in table_def.columns:
                del table_def.columns[col_name]
            else:
                logger.warning(
                    "ALTER TABLE DROP COLUMN: '%s' not found in table '%s'.",
                    col_name,
                    table_name,
                )
            return

        logger.warning("Unrecognized ALTER TABLE operation: %s", raw)

# Made with Bob
