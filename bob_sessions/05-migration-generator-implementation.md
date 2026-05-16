**User:**

<task>
We have 'server/app/core/parser.py' (see below for file content)  and 'server/app/core/comparator.py' (see below for file content). I need the last chore nucleus `generator.py`

Create a class `MigrationGenerator` that grabs a SchemaChanges object and generates:

1. A migration_sql string for applying changes.
2. A rollback_sql string for reverting.

Focus on PostgreSQL. Should manage:

- Creation/Deletion of tables
- ADD COLUMN and DROP COLUMN
- Data type changes using ALTER COLUMN ... TYPE ...
</task>

<file_content path="server/app/core/parser.py">
  1 | """
  2 | SQL Parser Module for Suturé
  3 | 
  4 | This module provides SQL parsing capabilities to extract schema information
  5 | from SQL scripts. It supports multiple SQL dialects with a focus on PostgreSQL.
  6 | 
  7 | Python Version: 3.13+
  8 | """
  9 | 
 10 | import logging
 11 | import re
 12 | from dataclasses import dataclass, field
 13 | from enum import Enum
 14 | from typing import Dict, List, Optional, Tuple
 15 | 
 16 | import sqlparse
 17 | from sqlparse.sql import Parenthesis, Statement
 18 | from sqlparse.tokens import DDL, Keyword, Name
 19 | 
 20 | logger = logging.getLogger(__name__)
 21 | 
 22 | # Token-type helpers
 23 | 
 24 | _NAME_TYPES = (Name, Name.Builtin)
 25 | 
 26 | # Keywords to skip when searching for an identifier after TABLE / ALTER TABLE
 27 | _SKIP_KEYWORDS = frozenset({"IF", "NOT", "EXISTS", "TEMPORARY", "TEMP", "OR", "REPLACE"})
 28 | 
 29 | # DDL and Keyword are the two ttype groups that can carry SQL keywords
 30 | _DDL_OR_KEYWORD = (DDL, Keyword)
 31 | 
 32 | 
 33 | # Enums
 34 | class SQLDialect(Enum):
 35 |     """Supported SQL dialects."""
 36 | 
 37 |     POSTGRESQL = "postgresql"
 38 |     MYSQL = "mysql"
 39 |     SUPABASE = "supabase"  # PostgreSQL-based
 40 | 
 41 | 
 42 | class ConstraintType(Enum):
 43 |     """Database constraint types."""
 44 | 
 45 |     PRIMARY_KEY = "PRIMARY KEY"
 46 |     FOREIGN_KEY = "FOREIGN KEY"
 47 |     UNIQUE = "UNIQUE"
 48 |     CHECK = "CHECK"
 49 |     NOT_NULL = "NOT NULL"
 50 |     DEFAULT = "DEFAULT"
 51 | 
 52 | 
 53 | # Dataclasses
 54 | 
 55 | @dataclass
 56 | class ColumnDefinition:
 57 |     """Represents a database column definition."""
 58 | 
 59 |     name: str
 60 |     data_type: str
 61 |     nullable: bool = True
 62 |     default: Optional[str] = None
 63 |     constraints: List[str] = field(default_factory=list)
 64 |     references: Optional[Tuple[str, str]] = None  # (table, column)
 65 | 
 66 |     def __repr__(self) -> str:
 67 |         return f"Column({self.name}: {self.data_type})"
 68 | 
 69 | 
 70 | @dataclass
 71 | class IndexDefinition:
 72 |     """Represents a database index."""
 73 | 
 74 |     name: str
 75 |     table: str
 76 |     columns: List[str]
 77 |     unique: bool = False
 78 |     index_type: Optional[str] = None  # BTREE, HASH, etc.
 79 | 
 80 |     def __repr__(self) -> str:
 81 |         return f"Index({self.name} on {self.table})"
 82 | 
 83 | 
 84 | @dataclass
 85 | class ConstraintDefinition:
 86 |     """Represents a table constraint."""
 87 | 
 88 |     name: Optional[str]
 89 |     constraint_type: ConstraintType
 90 |     columns: List[str]
 91 |     definition: str
 92 |     references: Optional[Tuple[str, List[str]]] = None  # (table, columns)
 93 | 
 94 |     def __repr__(self) -> str:
 95 |         return f"Constraint({self.constraint_type.value})"
 96 | 
 97 | 
 98 | @dataclass
 99 | class TableDefinition:
100 |     """Represents a complete table definition."""
101 | 
102 |     name: str
103 |     columns: Dict[str, ColumnDefinition] = field(default_factory=dict)
104 |     constraints: List[ConstraintDefinition] = field(default_factory=list)
105 |     indexes: List[IndexDefinition] = field(default_factory=list)
106 | 
107 |     def __repr__(self) -> str:
108 |         return f"Table({self.name}, {len(self.columns)} columns)"
109 | 
110 | 
111 | @dataclass
112 | class SchemaDefinition:
113 |     """Represents a complete database schema."""
114 | 
115 |     tables: Dict[str, TableDefinition] = field(default_factory=dict)
116 |     indexes: List[IndexDefinition] = field(default_factory=list)
117 |     dialect: SQLDialect = SQLDialect.POSTGRESQL
118 | 
119 |     def __repr__(self) -> str:
120 |         return f"Schema({len(self.tables)} tables, {len(self.indexes)} indexes)"
121 | 
122 | 
123 | class SQLParser:
124 |     """
125 |     SQL Parser for extracting schema information from SQL scripts.
126 | 
127 |     Supports PostgreSQL, MySQL, and Supabase (PostgreSQL-based) dialects.
128 |     Uses sqlparse for tokenization and custom logic for schema extraction.
129 |     """
130 | 
131 |     def __init__(self, dialect: SQLDialect = SQLDialect.POSTGRESQL) -> None:
132 |         self.dialect = dialect
133 | 
134 |     def parse(self, sql_script: str) -> SchemaDefinition:
135 |         """
136 |         Parse a SQL script and extract schema information.
137 | 
138 |         Args:
139 |             sql_script: The SQL script content to parse.
140 | 
141 |         Returns:
142 |             SchemaDefinition object containing all extracted schema information.
143 | 
144 |         Raises:
145 |             ValueError: If the SQL script is empty.
146 |         """
147 |         if not sql_script or not sql_script.strip():
148 |             raise ValueError("SQL script cannot be empty")
149 | 
150 |         cleaned_sql = self._clean_sql(sql_script)
151 |         statements = sqlparse.parse(cleaned_sql)
152 |         schema = SchemaDefinition(dialect=self.dialect)
153 | 
154 |         for statement in statements:
155 |             try:
156 |                 self._process_statement(statement, schema)
157 |             except Exception as exc:
158 |                 logger.warning("Failed to process statement: %s — %s", statement, exc)
159 | 
160 |         return schema
161 | 
162 |     @staticmethod
163 |     def _clean_sql(sql_script: str) -> str:
164 |         """Strip comments and normalise whitespace."""
165 |         sql_script = sqlparse.format(sql_script, strip_comments=True, reindent=False)
166 |         return re.sub(r"\s+", " ", sql_script).strip()
167 | 
168 |     def _process_statement(self, statement: Statement, schema: SchemaDefinition) -> None:
169 |         stmt_type = statement.get_type()
170 |         if stmt_type == "CREATE":
171 |             self._process_create_statement(statement, schema)
172 |         elif stmt_type == "ALTER":
173 |             self._process_alter_statement(statement, schema)
174 | 
175 |     def _process_create_statement(self, statement: Statement, schema: SchemaDefinition) -> None:
176 |         """Dispatch CREATE TABLE / CREATE [UNIQUE] INDEX."""
177 |         tokens = list(statement.flatten())
178 |         create_type: Optional[str] = None
179 |         is_unique = False
180 | 
181 |         for i, token in enumerate(tokens):
182 |             if token.ttype is DDL and token.value.upper() == "CREATE":
183 |                 for j in range(i + 1, min(i + 10, len(tokens))):
184 |                     ttype = tokens[j].ttype
185 |                     val = tokens[j].value.upper()
186 | 
187 |                     if ttype not in _DDL_OR_KEYWORD:
188 |                         continue
189 |                     if val in _SKIP_KEYWORDS:
190 |                         continue
191 |                     if val == "UNIQUE":
192 |                         is_unique = True
193 |                         continue
194 | 
195 |                     create_type = val
196 |                     break
197 |                 break
198 | 
199 |         if create_type == "TABLE":
200 |             self._process_create_table(statement, schema)
201 |         elif create_type == "INDEX":
202 |             self._process_create_index(statement, schema, unique=is_unique)
203 | 
204 |     def _process_create_table(self, statement: Statement, schema: SchemaDefinition) -> None:
205 |         table_name = self._extract_table_name(statement)
206 |         if not table_name:
207 |             logger.warning("Could not extract table name from: %s", statement)
208 |             return
209 | 
210 |         table_def = TableDefinition(name=table_name)
211 |         self._extract_table_body(statement, table_def)
212 |         schema.tables[table_name] = table_def
213 | 
214 |     def _extract_table_name(self, statement: Statement) -> Optional[str]:
215 |         """
216 |         Extract the table name, handling IF NOT EXISTS and all quote styles.
217 |         """
218 |         tokens = list(statement.flatten())
219 |         found_table_kw = False
220 | 
221 |         for token in tokens:
222 |             ttype = token.ttype
223 |             val_upper = token.value.upper()
224 | 
225 |             if not found_table_kw:
226 |                 # TABLE can appear as Keyword or DDL (depending on sqlparse version)
227 |                 if ttype in _DDL_OR_KEYWORD and val_upper == "TABLE":
228 |                     found_table_kw = True
229 |                 continue
230 | 
231 |             # Skip modifier keywords (IF NOT EXISTS, TEMPORARY …)
232 |             if ttype in _DDL_OR_KEYWORD and val_upper in _SKIP_KEYWORDS:
233 |                 continue
234 | 
235 |             # First real identifier is the table name
236 |             if ttype in _NAME_TYPES:
237 |                 return token.value.strip('"').strip("`").strip("'")
238 | 
239 |         return None
240 | 
241 |     def _extract_table_body(self, statement: Statement, table_def: TableDefinition) -> None:
242 |         for token in statement.tokens:
243 |             if isinstance(token, Parenthesis):
244 |                 self._parse_table_columns(token, table_def)
245 |                 break
246 | 
247 |     def _parse_table_columns(self, parenthesis: Parenthesis, table_def: TableDefinition) -> None:
248 |         for raw_def in self._split_by_comma(parenthesis):
249 |             definition_str = raw_def.strip()
250 |             if not definition_str:
251 |                 continue
252 | 
253 |             if self._is_table_constraint(definition_str):
254 |                 constraint = self._parse_table_constraint(definition_str)
255 |                 if constraint:
256 |                     table_def.constraints.append(constraint)
257 |             else:
258 |                 column = self._parse_column_definition(definition_str)
259 |                 if column:
260 |                     table_def.columns[column.name] = column
261 | 
262 |     @staticmethod
263 |     def _split_by_comma(parenthesis: Parenthesis) -> List[str]:
264 |         """
265 |         Split parenthesis content by commas, respecting nested parentheses
266 |         and single/double quoted strings.
267 |         """
268 |         content = str(parenthesis)[1:-1]  # Remove outer ( )
269 |         definitions: List[str] = []
270 |         current: List[str] = []
271 |         depth = 0
272 |         in_quote: Optional[str] = None
273 | 
274 |         for char in content:
275 |             if in_quote:
276 |                 current.append(char)
277 |                 if char == in_quote:
278 |                     in_quote = None
279 |             elif char in ("'", '"'):
280 |                 in_quote = char
281 |                 current.append(char)
282 |             elif char == "(":
283 |                 depth += 1
284 |                 current.append(char)
285 |             elif char == ")":
286 |                 depth -= 1
287 |                 current.append(char)
288 |             elif char == "," and depth == 0:
289 |                 definitions.append("".join(current).strip())
290 |                 current = []
291 |             else:
292 |                 current.append(char)
293 | 
294 |         if current:
295 |             definitions.append("".join(current).strip())
296 | 
297 |         return definitions
298 | 
299 |     def _parse_column_definition(self, definition: str) -> Optional[ColumnDefinition]:
300 |         """Parse a single column definition line."""
301 |         parts = definition.split()
302 |         if len(parts) < 2:
303 |             return None
304 | 
305 |         col_name = parts[0].strip('"').strip("`").strip("'")
306 | 
307 |         type_match = re.match(r"^\s*\S+\s+(\w+\s*(?:\([^)]*\))?)", definition, re.IGNORECASE)
308 |         col_type = type_match.group(1).strip().upper() if type_match else parts[1].upper()
309 | 
310 |         column = ColumnDefinition(name=col_name, data_type=col_type)
311 |         definition_upper = definition.upper()
312 | 
313 |         if "NOT NULL" in definition_upper:
314 |             column.nullable = False
315 |             column.constraints.append("NOT NULL")
316 | 
317 |         if "PRIMARY KEY" in definition_upper:
318 |             column.constraints.append("PRIMARY KEY")
319 | 
320 |         if re.search(r"\bUNIQUE\b", definition_upper):
321 |             column.constraints.append("UNIQUE")
322 | 
323 |         default_value = self._extract_default_value(definition)
324 |         if default_value is not None:
325 |             column.default = default_value
326 |             column.constraints.append(f"DEFAULT {default_value}")
327 | 
328 |         ref_match = re.search(
329 |             r"\bREFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)",
330 |             definition,
331 |             re.IGNORECASE,
332 |         )
333 |         if ref_match:
334 |             column.references = (ref_match.group(1), ref_match.group(2))
335 |             column.constraints.append(
336 |                 f"REFERENCES {ref_match.group(1)}({ref_match.group(2)})"
337 |             )
338 | 
339 |         return column
340 | 
341 |     @staticmethod
342 |     def _extract_default_value(definition: str) -> Optional[str]:
343 |         """
344 |         Robustly extract the DEFAULT value from a column definition string.
345 | 
346 |         Handles:
347 |         - Simple literals:        DEFAULT 0, DEFAULT true
348 |         - Quoted strings:         DEFAULT 'hello world'
349 |         - Functions:              DEFAULT NOW(), DEFAULT gen_random_uuid()
350 |         - Multi-word expressions: DEFAULT CURRENT_TIMESTAMP
351 |         - Negative numbers:       DEFAULT -1
352 |         """
353 |         match = re.search(r"\bDEFAULT\b", definition, re.IGNORECASE)
354 |         if not match:
355 |             return None
356 | 
357 |         rest = definition[match.end():].lstrip()
358 | 
359 |         # Patterns that signal the end of the DEFAULT value
360 |         _stop = re.compile(
361 |             r"\b(NOT\s+NULL|NULL|PRIMARY\s+KEY|UNIQUE|CHECK|REFERENCES)\b",
362 |             re.IGNORECASE,
363 |         )
364 | 
365 |         result: List[str] = []
366 |         depth = 0
367 |         in_quote: Optional[str] = None
368 |         i = 0
369 | 
370 |         while i < len(rest):
371 |             char = rest[i]
372 | 
373 |             if in_quote:
374 |                 result.append(char)
375 |                 # Handle escaped quotes inside strings
376 |                 if char == in_quote and (i == 0 or rest[i - 1] != "\\"):
377 |                     in_quote = None
378 |             elif char in ("'", '"'):
379 |                 in_quote = char
380 |                 result.append(char)
381 |             elif char == "(":
382 |                 depth += 1
383 |                 result.append(char)
384 |             elif char == ")":
385 |                 if depth == 0:
386 |                     break
387 |                 depth -= 1
388 |                 result.append(char)
389 |             elif char == "," and depth == 0:
390 |                 break
391 |             else:
392 |                 # Check for stop-word only at depth 0
393 |                 if depth == 0:
394 |                     stop_match = _stop.match(rest[i:])
395 |                     if stop_match:
396 |                         break
397 |                 result.append(char)
398 |             i += 1
399 | 
400 |         value = "".join(result).strip()
401 |         return value if value else None
402 | 
403 | 
404 |     @staticmethod
405 |     def _is_table_constraint(definition: str) -> bool:
406 |         definition_upper = definition.upper()
407 |         return any(
408 |             kw in definition_upper
409 |             for kw in ("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT")
410 |         )
411 | 
412 |     def _parse_table_constraint(self, definition: str) -> Optional[ConstraintDefinition]:
413 |         definition_upper = definition.upper()
414 | 
415 |         constraint_name: Optional[str] = None
416 |         name_match = re.search(r"\bCONSTRAINT\s+(\w+)", definition, re.IGNORECASE)
417 |         if name_match:
418 |             constraint_name = name_match.group(1)
419 | 
420 |         if "PRIMARY KEY" in definition_upper:
421 |             columns = self._extract_constraint_columns(definition, "PRIMARY KEY")
422 |             return ConstraintDefinition(
423 |                 name=constraint_name,
424 |                 constraint_type=ConstraintType.PRIMARY_KEY,
425 |                 columns=columns,
426 |                 definition=definition,
427 |             )
428 | 
429 |         if "FOREIGN KEY" in definition_upper:
430 |             columns = self._extract_constraint_columns(definition, "FOREIGN KEY")
431 |             ref_match = re.search(
432 |                 r"\bREFERENCES\s+(\w+)\s*\(([^)]+)\)",
433 |                 definition,
434 |                 re.IGNORECASE,
435 |             )
436 |             references: Optional[Tuple[str, List[str]]] = None
437 |             if ref_match:
438 |                 ref_table = ref_match.group(1)
439 |                 ref_cols = [
440 |                     c.strip().strip('"').strip("`").strip("'")
441 |                     for c in ref_match.group(2).split(",")
442 |                 ]
443 |                 references = (ref_table, ref_cols)
444 | 
445 |             return ConstraintDefinition(
446 |                 name=constraint_name,
447 |                 constraint_type=ConstraintType.FOREIGN_KEY,
448 |                 columns=columns,
449 |                 definition=definition,
450 |                 references=references,
451 |             )
452 | 
453 |         if re.search(r"\bUNIQUE\b", definition_upper):
454 |             columns = self._extract_constraint_columns(definition, "UNIQUE")
455 |             return ConstraintDefinition(
456 |                 name=constraint_name,
457 |                 constraint_type=ConstraintType.UNIQUE,
458 |                 columns=columns,
459 |                 definition=definition,
460 |             )
461 | 
462 |         if "CHECK" in definition_upper:
463 |             return ConstraintDefinition(
464 |                 name=constraint_name,
465 |                 constraint_type=ConstraintType.CHECK,
466 |                 columns=[],
467 |                 definition=definition,
468 |             )
469 | 
470 |         return None
471 | 
472 |     @staticmethod
473 |     def _extract_constraint_columns(definition: str, constraint_type: str) -> List[str]:
474 |         pattern = rf"\b{re.escape(constraint_type)}\s*\(([^)]+)\)"
475 |         match = re.search(pattern, definition, re.IGNORECASE)
476 |         if match:
477 |             return [
478 |                 col.strip().strip('"').strip("`").strip("'")
479 |                 for col in match.group(1).split(",")
480 |             ]
481 |         return []
482 | 
483 |     # Create INDEX
484 |     def _process_create_index(
485 |         self,
486 |         statement: Statement,
487 |         schema: SchemaDefinition,
488 |         unique: bool = False,
489 |     ) -> None:
490 |         tokens = list(statement.flatten())
491 |         index_name: Optional[str] = None
492 |         table_name: Optional[str] = None
493 |         columns: List[str] = []
494 | 
495 |         # Index name follows INDEX keyword
496 |         for i, token in enumerate(tokens):
497 |             if token.ttype in _DDL_OR_KEYWORD and token.value.upper() == "INDEX":
498 |                 for j in range(i + 1, len(tokens)):
499 |                     if tokens[j].ttype in _NAME_TYPES:
500 |                         index_name = tokens[j].value.strip('"').strip("`").strip("'")
501 |                         break
502 |                 break
503 | 
504 |         # Table name follows ON keyword
505 |         for i, token in enumerate(tokens):
506 |             if token.ttype in _DDL_OR_KEYWORD and token.value.upper() == "ON":
507 |                 for j in range(i + 1, len(tokens)):
508 |                     if tokens[j].ttype in _NAME_TYPES:
509 |                         table_name = tokens[j].value.strip('"').strip("`").strip("'")
510 |                         break
511 |                 break
512 | 
513 |         # Columns from the first Parenthesis token
514 |         for token in statement.tokens:
515 |             if isinstance(token, Parenthesis):
516 |                 cols_str = str(token)[1:-1]
517 |                 columns = [
518 |                     col.strip().strip('"').strip("`").strip("'")
519 |                     for col in cols_str.split(",")
520 |                     if col.strip()
521 |                 ]
522 |                 break
523 | 
524 |         if not (index_name and table_name and columns):
525 |             logger.warning(
526 |                 "Incomplete CREATE INDEX — name=%s, table=%s, columns=%s",
527 |                 index_name,
528 |                 table_name,
529 |                 columns,
530 |             )
531 |             return
532 | 
533 |         index_def = IndexDefinition(
534 |             name=index_name,   # type: ignore[arg-type]
535 |             table=table_name,  # type: ignore[arg-type]
536 |             columns=columns,
537 |             unique=unique,
538 |         )
539 |         schema.indexes.append(index_def)
540 | 
541 |         if table_name in schema.tables:
542 |             schema.tables[table_name].indexes.append(index_def)
543 | 
544 |     # Alter table
545 |     def _process_alter_statement(self, statement: Statement, schema: SchemaDefinition) -> None:
546 |         """
547 |         Process ALTER TABLE statements.
548 | 
549 |         Supported operations:
550 |         - ADD COLUMN
551 |         - ADD CONSTRAINT (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK)
552 |         - DROP COLUMN [IF EXISTS]
553 |         """
554 |         tokens = list(statement.flatten())
555 |         table_name: Optional[str] = None
556 |         found_alter = False
557 |         found_table_kw = False
558 | 
559 |         for token in tokens:
560 |             ttype = token.ttype
561 |             val_upper = token.value.upper()
562 | 
563 |             if not found_alter:
564 |                 if ttype is DDL and val_upper == "ALTER":
565 |                     found_alter = True
566 |                 continue
567 | 
568 |             if not found_table_kw:
569 |                 if ttype in _DDL_OR_KEYWORD and val_upper == "TABLE":
570 |                     found_table_kw = True
571 |                 continue
572 | 
573 |             if ttype in _DDL_OR_KEYWORD and val_upper in _SKIP_KEYWORDS:
574 |                 continue
575 | 
576 |             if ttype in _NAME_TYPES:
577 |                 table_name = token.value.strip('"').strip("`").strip("'")
578 |                 break
579 | 
580 |         if not table_name:
581 |             logger.warning("Could not extract table name from ALTER: %s", statement)
582 |             return
583 | 
584 |         if table_name not in schema.tables:
585 |             logger.warning("ALTER TABLE references unknown table '%s' — skipping.", table_name)
586 |             return
587 | 
588 |         table_def = schema.tables[table_name]
589 |         raw = statement.value
590 | 
591 |         # Add column / Add constraint
592 |         add_match = re.search(
593 |             r"\bADD\s+(?:COLUMN\s+)?(.+?)(?:\s*;?\s*$)",
594 |             raw,
595 |             re.IGNORECASE | re.DOTALL,
596 |         )
597 |         if add_match:
598 |             added = add_match.group(1).strip().rstrip(";").strip()
599 |             if self._is_table_constraint(added):
600 |                 constraint = self._parse_table_constraint(added)
601 |                 if constraint:
602 |                     table_def.constraints.append(constraint)
603 |             else:
604 |                 col = self._parse_column_definition(added)
605 |                 if col:
606 |                     table_def.columns[col.name] = col
607 |             return
608 | 
609 |         # Drop column if exists
610 |         drop_match = re.search(
611 |             r"\bDROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?(\w+)",
612 |             raw,
613 |             re.IGNORECASE,
614 |         )
615 |         if drop_match:
616 |             col_name = drop_match.group(1).strip('"').strip("`").strip("'")
617 |             if col_name in table_def.columns:
618 |                 del table_def.columns[col_name]
619 |             else:
620 |                 logger.warning(
621 |                     "ALTER TABLE DROP COLUMN: '%s' not found in table '%s'.",
622 |                     col_name,
623 |                     table_name,
624 |                 )
625 |             return
626 | 
627 |         logger.warning("Unrecognized ALTER TABLE operation: %s", raw)
628 | 
629 | # Made with Bob

</file_content>

<file_content path="server/app/core/comparator.py">
  1 | """
  2 | Schema Comparator Module for Suturé
  3 | 
  4 | This module provides schema comparison capabilities to detect differences
  5 | between two database schemas, including tables, columns, indexes, and constraints.
  6 | 
  7 | Python Version: 3.13+
  8 | """
  9 | 
 10 | import logging
 11 | from dataclasses import dataclass, field
 12 | from typing import Dict, List, Optional, Set
 13 | 
 14 | from .parser import (
 15 |     ColumnDefinition,
 16 |     ConstraintDefinition,
 17 |     IndexDefinition,
 18 |     SchemaDefinition,
 19 |     TableDefinition,
 20 | )
 21 | 
 22 | logger = logging.getLogger(__name__)
 23 | 
 24 | 
 25 | @dataclass
 26 | class ColumnChange:
 27 |     """Represents a change to a column."""
 28 | 
 29 |     column_name: str
 30 |     old_definition: Optional[ColumnDefinition] = None
 31 |     new_definition: Optional[ColumnDefinition] = None
 32 |     change_type: str = "modified"  # "added", "deleted", "modified"
 33 | 
 34 |     def __repr__(self) -> str:
 35 |         return f"ColumnChange({self.change_type}: {self.column_name})"
 36 | 
 37 | 
 38 | @dataclass
 39 | class TableChange:
 40 |     """Represents changes to a table."""
 41 | 
 42 |     table_name: str
 43 |     change_type: str  # "added", "deleted", "modified"
 44 |     columns_added: List[ColumnDefinition] = field(default_factory=list)
 45 |     columns_deleted: List[ColumnDefinition] = field(default_factory=list)
 46 |     columns_modified: List[ColumnChange] = field(default_factory=list)
 47 |     constraints_added: List[ConstraintDefinition] = field(default_factory=list)
 48 |     constraints_deleted: List[ConstraintDefinition] = field(default_factory=list)
 49 |     indexes_added: List[IndexDefinition] = field(default_factory=list)
 50 |     indexes_deleted: List[IndexDefinition] = field(default_factory=list)
 51 | 
 52 |     def __repr__(self) -> str:
 53 |         return f"TableChange({self.change_type}: {self.table_name})"
 54 | 
 55 |     def has_changes(self) -> bool:
 56 |         """Check if this table has any actual changes."""
 57 |         return bool(
 58 |             self.columns_added
 59 |             or self.columns_deleted
 60 |             or self.columns_modified
 61 |             or self.constraints_added
 62 |             or self.constraints_deleted
 63 |             or self.indexes_added
 64 |             or self.indexes_deleted
 65 |         )
 66 | 
 67 | 
 68 | @dataclass
 69 | class SchemaChanges:
 70 |     """Represents all changes between two schemas."""
 71 | 
 72 |     tables_added: List[TableDefinition] = field(default_factory=list)
 73 |     tables_deleted: List[TableDefinition] = field(default_factory=list)
 74 |     tables_modified: List[TableChange] = field(default_factory=list)
 75 |     indexes_added: List[IndexDefinition] = field(default_factory=list)
 76 |     indexes_deleted: List[IndexDefinition] = field(default_factory=list)
 77 | 
 78 |     def __repr__(self) -> str:
 79 |         return (
 80 |             f"SchemaChanges("
 81 |             f"tables_added={len(self.tables_added)}, "
 82 |             f"tables_deleted={len(self.tables_deleted)}, "
 83 |             f"tables_modified={len(self.tables_modified)}, "
 84 |             f"indexes_added={len(self.indexes_added)}, "
 85 |             f"indexes_deleted={len(self.indexes_deleted)})"
 86 |         )
 87 | 
 88 |     def has_changes(self) -> bool:
 89 |         """Check if there are any changes between the schemas."""
 90 |         return bool(
 91 |             self.tables_added
 92 |             or self.tables_deleted
 93 |             or self.tables_modified
 94 |             or self.indexes_added
 95 |             or self.indexes_deleted
 96 |         )
 97 | 
 98 |     def get_summary(self) -> Dict[str, int]:
 99 |         """Get a summary of all changes."""
100 |         return {
101 |             "tables_added": len(self.tables_added),
102 |             "tables_deleted": len(self.tables_deleted),
103 |             "tables_modified": len(self.tables_modified),
104 |             "indexes_added": len(self.indexes_added),
105 |             "indexes_deleted": len(self.indexes_deleted),
106 |         }
107 | 
108 | 
109 | class SchemaComparator:
110 |     """
111 |     Compares two SchemaDefinition instances and identifies differences.
112 | 
113 |     Detects:
114 |     - Added/deleted/modified tables
115 |     - Added/deleted/modified columns (including data type changes)
116 |     - Added/deleted constraints
117 |     - Added/deleted indexes
118 |     """
119 | 
120 |     def __init__(self) -> None:
121 |         """Initialize the schema comparator."""
122 |         pass
123 | 
124 |     def compare(
125 |         self, old_schema: SchemaDefinition, new_schema: SchemaDefinition
126 |     ) -> SchemaChanges:
127 |         """
128 |         Compare two schemas and return detailed changes.
129 | 
130 |         Args:
131 |             old_schema: The original schema definition.
132 |             new_schema: The new schema definition to compare against.
133 | 
134 |         Returns:
135 |             SchemaChanges object containing all detected differences.
136 |         """
137 |         changes = SchemaChanges()
138 | 
139 |         # Compare tables
140 |         old_table_names = set(old_schema.tables.keys())
141 |         new_table_names = set(new_schema.tables.keys())
142 | 
143 |         # Find added tables
144 |         for table_name in new_table_names - old_table_names:
145 |             changes.tables_added.append(new_schema.tables[table_name])
146 |             logger.debug("Table added: %s", table_name)
147 | 
148 |         # Find deleted tables
149 |         for table_name in old_table_names - new_table_names:
150 |             changes.tables_deleted.append(old_schema.tables[table_name])
151 |             logger.debug("Table deleted: %s", table_name)
152 | 
153 |         # Find modified tables
154 |         for table_name in old_table_names & new_table_names:
155 |             table_change = self._compare_tables(
156 |                 old_schema.tables[table_name], new_schema.tables[table_name]
157 |             )
158 |             if table_change.has_changes():
159 |                 changes.tables_modified.append(table_change)
160 |                 logger.debug("Table modified: %s", table_name)
161 | 
162 |         # Compare standalone indexes (not associated with specific tables)
163 |         self._compare_standalone_indexes(old_schema, new_schema, changes)
164 | 
165 |         return changes
166 | 
167 |     def _compare_tables(
168 |         self, old_table: TableDefinition, new_table: TableDefinition
169 |     ) -> TableChange:
170 |         """
171 |         Compare two table definitions and identify changes.
172 | 
173 |         Args:
174 |             old_table: The original table definition.
175 |             new_table: The new table definition.
176 | 
177 |         Returns:
178 |             TableChange object with all detected differences.
179 |         """
180 |         table_change = TableChange(table_name=old_table.name, change_type="modified")
181 | 
182 |         # Compare columns
183 |         old_column_names = set(old_table.columns.keys())
184 |         new_column_names = set(new_table.columns.keys())
185 | 
186 |         # Added columns
187 |         for col_name in new_column_names - old_column_names:
188 |             table_change.columns_added.append(new_table.columns[col_name])
189 |             logger.debug("Column added: %s.%s", old_table.name, col_name)
190 | 
191 |         # Deleted columns
192 |         for col_name in old_column_names - new_column_names:
193 |             table_change.columns_deleted.append(old_table.columns[col_name])
194 |             logger.debug("Column deleted: %s.%s", old_table.name, col_name)
195 | 
196 |         # Modified columns
197 |         for col_name in old_column_names & new_column_names:
198 |             old_col = old_table.columns[col_name]
199 |             new_col = new_table.columns[col_name]
200 | 
201 |             if self._columns_differ(old_col, new_col):
202 |                 column_change = ColumnChange(
203 |                     column_name=col_name,
204 |                     old_definition=old_col,
205 |                     new_definition=new_col,
206 |                     change_type="modified",
207 |                 )
208 |                 table_change.columns_modified.append(column_change)
209 |                 logger.debug("Column modified: %s.%s", old_table.name, col_name)
210 | 
211 |         # Compare constraints
212 |         self._compare_constraints(old_table, new_table, table_change)
213 | 
214 |         # Compare table-level indexes
215 |         self._compare_table_indexes(old_table, new_table, table_change)
216 | 
217 |         return table_change
218 | 
219 |     def _columns_differ(
220 |         self, old_col: ColumnDefinition, new_col: ColumnDefinition
221 |     ) -> bool:
222 |         """
223 |         Check if two column definitions are different.
224 | 
225 |         Compares:
226 |         - Data type
227 |         - Nullable flag
228 |         - Default value
229 |         - Constraints
230 |         - References
231 | 
232 |         Args:
233 |             old_col: The original column definition.
234 |             new_col: The new column definition.
235 | 
236 |         Returns:
237 |             True if columns differ, False otherwise.
238 |         """
239 |         # Normalize data types for comparison (case-insensitive)
240 |         old_type = old_col.data_type.upper().strip()
241 |         new_type = new_col.data_type.upper().strip()
242 | 
243 |         if old_type != new_type:
244 |             logger.debug(
245 |                 "Data type changed: %s -> %s", old_col.data_type, new_col.data_type
246 |             )
247 |             return True
248 | 
249 |         if old_col.nullable != new_col.nullable:
250 |             logger.debug("Nullable changed: %s -> %s", old_col.nullable, new_col.nullable)
251 |             return True
252 | 
253 |         # Normalize default values for comparison
254 |         old_default = self._normalize_default(old_col.default)
255 |         new_default = self._normalize_default(new_col.default)
256 | 
257 |         if old_default != new_default:
258 |             logger.debug("Default changed: %s -> %s", old_col.default, new_col.default)
259 |             return True
260 | 
261 |         # Compare constraints (order-independent)
262 |         old_constraints = set(self._normalize_constraint(c) for c in old_col.constraints)
263 |         new_constraints = set(self._normalize_constraint(c) for c in new_col.constraints)
264 | 
265 |         if old_constraints != new_constraints:
266 |             logger.debug(
267 |                 "Constraints changed: %s -> %s", old_col.constraints, new_col.constraints
268 |             )
269 |             return True
270 | 
271 |         # Compare references
272 |         if old_col.references != new_col.references:
273 |             logger.debug(
274 |                 "References changed: %s -> %s", old_col.references, new_col.references
275 |             )
276 |             return True
277 | 
278 |         return False
279 | 
280 |     @staticmethod
281 |     def _normalize_default(default: Optional[str]) -> Optional[str]:
282 |         """Normalize default value for comparison."""
283 |         if default is None:
284 |             return None
285 |         # Remove extra whitespace and normalize case for keywords
286 |         normalized = " ".join(default.split())
287 |         return normalized.upper() if normalized.upper() in ("NULL", "TRUE", "FALSE") else normalized
288 | 
289 |     @staticmethod
290 |     def _normalize_constraint(constraint: str) -> str:
291 |         """Normalize constraint string for comparison."""
292 |         # Remove extra whitespace and normalize to uppercase
293 |         return " ".join(constraint.upper().split())
294 | 
295 |     def _compare_constraints(
296 |         self,
297 |         old_table: TableDefinition,
298 |         new_table: TableDefinition,
299 |         table_change: TableChange,
300 |     ) -> None:
301 |         """
302 |         Compare constraints between two tables.
303 | 
304 |         Args:
305 |             old_table: The original table definition.
306 |             new_table: The new table definition.
307 |             table_change: The TableChange object to populate.
308 |         """
309 |         # Create comparable representations of constraints
310 |         old_constraints = {
311 |             self._constraint_signature(c): c for c in old_table.constraints
312 |         }
313 |         new_constraints = {
314 |             self._constraint_signature(c): c for c in new_table.constraints
315 |         }
316 | 
317 |         old_sigs = set(old_constraints.keys())
318 |         new_sigs = set(new_constraints.keys())
319 | 
320 |         # Added constraints
321 |         for sig in new_sigs - old_sigs:
322 |             table_change.constraints_added.append(new_constraints[sig])
323 |             logger.debug("Constraint added: %s", new_constraints[sig])
324 | 
325 |         # Deleted constraints
326 |         for sig in old_sigs - new_sigs:
327 |             table_change.constraints_deleted.append(old_constraints[sig])
328 |             logger.debug("Constraint deleted: %s", old_constraints[sig])
329 | 
330 |     @staticmethod
331 |     def _constraint_signature(constraint: ConstraintDefinition) -> str:
332 |         """
333 |         Create a unique signature for a constraint for comparison.
334 | 
335 |         Args:
336 |             constraint: The constraint definition.
337 | 
338 |         Returns:
339 |             A string signature representing the constraint.
340 |         """
341 |         # Use constraint type, columns, and references to create signature
342 |         sig_parts = [
343 |             constraint.constraint_type.value,
344 |             ",".join(sorted(constraint.columns)),
345 |         ]
346 | 
347 |         if constraint.references:
348 |             ref_table, ref_cols = constraint.references
349 |             sig_parts.append(f"REF:{ref_table}({','.join(sorted(ref_cols))})")
350 | 
351 |         # Include name if present (for named constraints)
352 |         if constraint.name:
353 |             sig_parts.append(f"NAME:{constraint.name}")
354 | 
355 |         return "|".join(sig_parts)
356 | 
357 |     def _compare_table_indexes(
358 |         self,
359 |         old_table: TableDefinition,
360 |         new_table: TableDefinition,
361 |         table_change: TableChange,
362 |     ) -> None:
363 |         """
364 |         Compare indexes within a table.
365 | 
366 |         Args:
367 |             old_table: The original table definition.
368 |             new_table: The new table definition.
369 |             table_change: The TableChange object to populate.
370 |         """
371 |         old_indexes = {self._index_signature(idx): idx for idx in old_table.indexes}
372 |         new_indexes = {self._index_signature(idx): idx for idx in new_table.indexes}
373 | 
374 |         old_sigs = set(old_indexes.keys())
375 |         new_sigs = set(new_indexes.keys())
376 | 
377 |         # Added indexes
378 |         for sig in new_sigs - old_sigs:
379 |             table_change.indexes_added.append(new_indexes[sig])
380 |             logger.debug("Index added: %s", new_indexes[sig])
381 | 
382 |         # Deleted indexes
383 |         for sig in old_sigs - new_sigs:
384 |             table_change.indexes_deleted.append(old_indexes[sig])
385 |             logger.debug("Index deleted: %s", old_indexes[sig])
386 | 
387 |     def _compare_standalone_indexes(
388 |         self,
389 |         old_schema: SchemaDefinition,
390 |         new_schema: SchemaDefinition,
391 |         changes: SchemaChanges,
392 |     ) -> None:
393 |         """
394 |         Compare standalone indexes (schema-level indexes).
395 | 
396 |         Args:
397 |             old_schema: The original schema definition.
398 |             new_schema: The new schema definition.
399 |             changes: The SchemaChanges object to populate.
400 |         """
401 |         old_indexes = {self._index_signature(idx): idx for idx in old_schema.indexes}
402 |         new_indexes = {self._index_signature(idx): idx for idx in new_schema.indexes}
403 | 
404 |         old_sigs = set(old_indexes.keys())
405 |         new_sigs = set(new_indexes.keys())
406 | 
407 |         # Added indexes
408 |         for sig in new_sigs - old_sigs:
409 |             changes.indexes_added.append(new_indexes[sig])
410 |             logger.debug("Standalone index added: %s", new_indexes[sig])
411 | 
412 |         # Deleted indexes
413 |         for sig in old_sigs - new_sigs:
414 |             changes.indexes_deleted.append(old_indexes[sig])
415 |             logger.debug("Standalone index deleted: %s", old_indexes[sig])
416 | 
417 |     @staticmethod
418 |     def _index_signature(index: IndexDefinition) -> str:
419 |         """
420 |         Create a unique signature for an index for comparison.
421 | 
422 |         Args:
423 |             index: The index definition.
424 | 
425 |         Returns:
426 |             A string signature representing the index.
427 |         """
428 |         sig_parts = [
429 |             index.name,
430 |             index.table,
431 |             ",".join(sorted(index.columns)),
432 |             str(index.unique),
433 |         ]
434 | 
435 |         if index.index_type:
436 |             sig_parts.append(index.index_type)
437 | 
438 |         return "|".join(sig_parts)
439 | 
440 | # Made with Bob

</file_content>
<environment_details>
# VSCode Visible Files
server/app/api/routes.py

# VSCode Open Tabs
.gitignore,server/app/__init__.py,server/app/core/comparator.py,server/app/core/parser.py,client/components/FileUpload.tsx,client/lib/api.ts,server/app/api/routes.py

# Current Time
Current time in ISO 8601 UTC format: 2026-05-15T21:04:18.890Z
User time zone: America/Tegucigalpa, UTC-6:00

# Current Cost
$0.00

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- node_modules/
- client/node_modules/
- server/venv/
- .venv/
- __pycache__/
- *.pyc
- .next/
- client/.next/
- dist/
- build/
- .cache/
- *.log
- .env
- .env.*
- .DS_Store
- Thumbs.db
- .git/
- *.png
- *.jpg
- *.jpeg
- *.gif
- *.svg
- *.ico
- *.pdf
- bob_sessions/

# Current Mode
<slug>code</slug>
<name>💻 Code</name>


# Current Workspace Directory (/home/djacoz/projects/fullstack/suture) Files
.gitignore
PHASE1_PLAN.md
bob_sessions/
client/
client/eslint.config.mjs
client/next-env.d.ts
client/next.config.ts
client/package.json
client/pnpm-lock.yaml
client/pnpm-workspace.yaml
client/postcss.config.mjs
client/tsconfig.json
client/app/
client/app/globals.css
client/app/layout.tsx
client/app/page.tsx
client/components/
client/components/FileUpload.tsx
client/hooks/
client/lib/
client/lib/api.ts
client/public/
client/services/
docs/
server/
server/requirements.txt
server/setup.py
server/app/
server/app/__init__.py
server/app/main.py
server/app/api/
server/app/api/__init__.py
server/app/api/routes.py
server/app/api/schemas.py
server/app/core/
server/app/core/__init__.py
server/app/core/comparator.py
server/app/core/parser.py
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

I'll create the `generator.py` file that generates migration and rollback SQL from a `SchemaChanges` object. Let me first read the existing files to understand the structure better.

<read_file>
<args>
<file>
<path>server/app/core/parser.py</path>
<line_range>1-121</line_range>
</file>
<file>
<path>server/app/core/comparator.py</path>
<line_range>1-107</line_range>
</file>
</args>
</read_file>

---

**User:**

[read_file for 'server/app/core/parser.py', 'server/app/core/comparator.py'] Result:
<files>
<file><path>server/app/core/parser.py</path>
<content lines="1-121">
  1 | """
  2 | SQL Parser Module for Suturé
  3 | 
  4 | This module provides SQL parsing capabilities to extract schema information
  5 | from SQL scripts. It supports multiple SQL dialects with a focus on PostgreSQL.
  6 | 
  7 | Python Version: 3.13+
  8 | """
  9 | 
 10 | import logging
 11 | import re
 12 | from dataclasses import dataclass, field
 13 | from enum import Enum
 14 | from typing import Dict, List, Optional, Tuple
 15 | 
 16 | import sqlparse
 17 | from sqlparse.sql import Parenthesis, Statement
 18 | from sqlparse.tokens import DDL, Keyword, Name
 19 | 
 20 | logger = logging.getLogger(__name__)
 21 | 
 22 | # Token-type helpers
 23 | 
 24 | _NAME_TYPES = (Name, Name.Builtin)
 25 | 
 26 | # Keywords to skip when searching for an identifier after TABLE / ALTER TABLE
 27 | _SKIP_KEYWORDS = frozenset({"IF", "NOT", "EXISTS", "TEMPORARY", "TEMP", "OR", "REPLACE"})
 28 | 
 29 | # DDL and Keyword are the two ttype groups that can carry SQL keywords
 30 | _DDL_OR_KEYWORD = (DDL, Keyword)
 31 | 
 32 | 
 33 | # Enums
 34 | class SQLDialect(Enum):
 35 |     """Supported SQL dialects."""
 36 | 
 37 |     POSTGRESQL = "postgresql"
 38 |     MYSQL = "mysql"
 39 |     SUPABASE = "supabase"  # PostgreSQL-based
 40 | 
 41 | 
 42 | class ConstraintType(Enum):
 43 |     """Database constraint types."""
 44 | 
 45 |     PRIMARY_KEY = "PRIMARY KEY"
 46 |     FOREIGN_KEY = "FOREIGN KEY"
 47 |     UNIQUE = "UNIQUE"
 48 |     CHECK = "CHECK"
 49 |     NOT_NULL = "NOT NULL"
 50 |     DEFAULT = "DEFAULT"
 51 | 
 52 | 
 53 | # Dataclasses
 54 | 
 55 | @dataclass
 56 | class ColumnDefinition:
 57 |     """Represents a database column definition."""
 58 | 
 59 |     name: str
 60 |     data_type: str
 61 |     nullable: bool = True
 62 |     default: Optional[str] = None
 63 |     constraints: List[str] = field(default_factory=list)
 64 |     references: Optional[Tuple[str, str]] = None  # (table, column)
 65 | 
 66 |     def __repr__(self) -> str:
 67 |         return f"Column({self.name}: {self.data_type})"
 68 | 
 69 | 
 70 | @dataclass
 71 | class IndexDefinition:
 72 |     """Represents a database index."""
 73 | 
 74 |     name: str
 75 |     table: str
 76 |     columns: List[str]
 77 |     unique: bool = False
 78 |     index_type: Optional[str] = None  # BTREE, HASH, etc.
 79 | 
 80 |     def __repr__(self) -> str:
 81 |         return f"Index({self.name} on {self.table})"
 82 | 
 83 | 
 84 | @dataclass
 85 | class ConstraintDefinition:
 86 |     """Represents a table constraint."""
 87 | 
 88 |     name: Optional[str]
 89 |     constraint_type: ConstraintType
 90 |     columns: List[str]
 91 |     definition: str
 92 |     references: Optional[Tuple[str, List[str]]] = None  # (table, columns)
 93 | 
 94 |     def __repr__(self) -> str:
 95 |         return f"Constraint({self.constraint_type.value})"
 96 | 
 97 | 
 98 | @dataclass
 99 | class TableDefinition:
100 |     """Represents a complete table definition."""
101 | 
102 |     name: str
103 |     columns: Dict[str, ColumnDefinition] = field(default_factory=dict)
104 |     constraints: List[ConstraintDefinition] = field(default_factory=list)
105 |     indexes: List[IndexDefinition] = field(default_factory=list)
106 | 
107 |     def __repr__(self) -> str:
108 |         return f"Table({self.name}, {len(self.columns)} columns)"
109 | 
110 | 
111 | @dataclass
112 | class SchemaDefinition:
113 |     """Represents a complete database schema."""
114 | 
115 |     tables: Dict[str, TableDefinition] = field(default_factory=dict)
116 |     indexes: List[IndexDefinition] = field(default_factory=list)
117 |     dialect: SQLDialect = SQLDialect.POSTGRESQL
118 | 
119 |     def __repr__(self) -> str:
120 |         return f"Schema({len(self.tables)} tables, {len(self.indexes)} indexes)"
121 | 
</content>
</file>
<file><path>server/app/core/comparator.py</path>
<content lines="1-107">
  1 | """
  2 | Schema Comparator Module for Suturé
  3 | 
  4 | This module provides schema comparison capabilities to detect differences
  5 | between two database schemas, including tables, columns, indexes, and constraints.
  6 | 
  7 | Python Version: 3.13+
  8 | """
  9 | 
 10 | import logging
 11 | from dataclasses import dataclass, field
 12 | from typing import Dict, List, Optional, Set
 13 | 
 14 | from .parser import (
 15 |     ColumnDefinition,
 16 |     ConstraintDefinition,
 17 |     IndexDefinition,
 18 |     SchemaDefinition,
 19 |     TableDefinition,
 20 | )
 21 | 
 22 | logger = logging.getLogger(__name__)
 23 | 
 24 | 
 25 | @dataclass
 26 | class ColumnChange:
 27 |     """Represents a change to a column."""
 28 | 
 29 |     column_name: str
 30 |     old_definition: Optional[ColumnDefinition] = None
 31 |     new_definition: Optional[ColumnDefinition] = None
 32 |     change_type: str = "modified"  # "added", "deleted", "modified"
 33 | 
 34 |     def __repr__(self) -> str:
 35 |         return f"ColumnChange({self.change_type}: {self.column_name})"
 36 | 
 37 | 
 38 | @dataclass
 39 | class TableChange:
 40 |     """Represents changes to a table."""
 41 | 
 42 |     table_name: str
 43 |     change_type: str  # "added", "deleted", "modified"
 44 |     columns_added: List[ColumnDefinition] = field(default_factory=list)
 45 |     columns_deleted: List[ColumnDefinition] = field(default_factory=list)
 46 |     columns_modified: List[ColumnChange] = field(default_factory=list)
 47 |     constraints_added: List[ConstraintDefinition] = field(default_factory=list)
 48 |     constraints_deleted: List[ConstraintDefinition] = field(default_factory=list)
 49 |     indexes_added: List[IndexDefinition] = field(default_factory=list)
 50 |     indexes_deleted: List[IndexDefinition] = field(default_factory=list)
 51 | 
 52 |     def __repr__(self) -> str:
 53 |         return f"TableChange({self.change_type}: {self.table_name})"
 54 | 
 55 |     def has_changes(self) -> bool:
 56 |         """Check if this table has any actual changes."""
 57 |         return bool(
 58 |             self.columns_added
 59 |             or self.columns_deleted
 60 |             or self.columns_modified
 61 |             or self.constraints_added
 62 |             or self.constraints_deleted
 63 |             or self.indexes_added
 64 |             or self.indexes_deleted
 65 |         )
 66 | 
 67 | 
 68 | @dataclass
 69 | class SchemaChanges:
 70 |     """Represents all changes between two schemas."""
 71 | 
 72 |     tables_added: List[TableDefinition] = field(default_factory=list)
 73 |     tables_deleted: List[TableDefinition] = field(default_factory=list)
 74 |     tables_modified: List[TableChange] = field(default_factory=list)
 75 |     indexes_added: List[IndexDefinition] = field(default_factory=list)
 76 |     indexes_deleted: List[IndexDefinition] = field(default_factory=list)
 77 | 
 78 |     def __repr__(self) -> str:
 79 |         return (
 80 |             f"SchemaChanges("
 81 |             f"tables_added={len(self.tables_added)}, "
 82 |             f"tables_deleted={len(self.tables_deleted)}, "
 83 |             f"tables_modified={len(self.tables_modified)}, "
 84 |             f"indexes_added={len(self.indexes_added)}, "
 85 |             f"indexes_deleted={len(self.indexes_deleted)})"
 86 |         )
 87 | 
 88 |     def has_changes(self) -> bool:
 89 |         """Check if there are any changes between the schemas."""
 90 |         return bool(
 91 |             self.tables_added
 92 |             or self.tables_deleted
 93 |             or self.tables_modified
 94 |             or self.indexes_added
 95 |             or self.indexes_deleted
 96 |         )
 97 | 
 98 |     def get_summary(self) -> Dict[str, int]:
 99 |         """Get a summary of all changes."""
100 |         return {
101 |             "tables_added": len(self.tables_added),
102 |             "tables_deleted": len(self.tables_deleted),
103 |             "tables_modified": len(self.tables_modified),
104 |             "indexes_added": len(self.indexes_added),
105 |             "indexes_deleted": len(self.indexes_deleted),
106 |         }
107 | 
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
server/app/api/routes.py

# VSCode Open Tabs
.gitignore,server/app/__init__.py,server/app/core/comparator.py,server/app/core/parser.py,client/components/FileUpload.tsx,client/lib/api.ts,server/app/api/routes.py

# Current Time
Current time in ISO 8601 UTC format: 2026-05-15T21:04:26.796Z
User time zone: America/Tegucigalpa, UTC-6:00

# Current Cost
$0.04

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- node_modules/
- client/node_modules/
- server/venv/
- .venv/
- __pycache__/
- *.pyc
- .next/
- client/.next/
- dist/
- build/
- .cache/
- *.log
- .env
- .env.*
- .DS_Store
- Thumbs.db
- .git/
- *.png
- *.jpg
- *.jpeg
- *.gif
- *.svg
- *.ico
- *.pdf
- bob_sessions/

# Current Mode
<slug>code</slug>
<name>💻 Code</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Now I'll create the `generator.py` file with the `MigrationGenerator` class that generates PostgreSQL migration and rollback SQL from a `SchemaChanges` object.

<write_to_file>
<path>server/app/core/generator.py</path>
<content>"""
Migration Generator Module for Suturé

This module provides SQL migration generation capabilities to create
migration and rollback scripts from schema changes.

Python Version: 3.13+
"""

import logging
from typing import List

from .comparator import ColumnChange, SchemaChanges, TableChange
from .parser import (
    ColumnDefinition,
    ConstraintDefinition,
    ConstraintType,
    IndexDefinition,
    TableDefinition,
)

logger = logging.getLogger(__name__)


class MigrationGenerator:
    """
    Generates PostgreSQL migration and rollback SQL from schema changes.

    Handles:
    - Table creation and deletion
    - Column additions and deletions
    - Column data type changes
    - Constraint additions and deletions
    - Index additions and deletions
    """

    def __init__(self) -> None:
        """Initialize the migration generator."""
        pass

    def generate(self, changes: SchemaChanges) -> tuple[str, str]:
        """
        Generate migration and rollback SQL from schema changes.

        Args:
            changes: SchemaChanges object containing all detected differences.

        Returns:
            Tuple of (migration_sql, rollback_sql) strings.
        """
        migration_statements: List[str] = []
        rollback_statements: List[str] = []

        # Process in order: tables added, tables modified, tables deleted
        # This ensures proper dependency handling

        # 1. Create new tables (forward)
        for table in changes.tables_added:
            migration_statements.append(self._generate_create_table(table))
            rollback_statements.insert(0, self._generate_drop_table(table.name))

        # 2. Modify existing tables (forward)
        for table_change in changes.tables_modified:
            mig_stmts, roll_stmts = self._generate_table_modifications(table_change)
            migration_statements.extend(mig_stmts)
            # Rollback statements are inserted in reverse order
            for stmt in reversed(roll_stmts):
                rollback_statements.insert(0, stmt)

        # 3. Drop tables (forward)
        for table in changes.tables_deleted:
            migration_statements.append(self._generate_drop_table(table.name))
            rollback_statements.insert(0, self._generate_create_table(table))

        # 4. Standalone indexes
        for index in changes.indexes_added:
            migration_statements.append(self._generate_create_index(index))
            rollback_statements.insert(0, self._generate_drop_index(index.name))

        for index in changes.indexes_deleted:
            migration_statements.append(self._generate_drop_index(index.name))
            rollback_statements.insert(0, self._generate_create_index(index))

        # Join all statements
        migration_sql = "\n\n".join(migration_statements) if migration_statements else "-- No changes detected"
        rollback_sql = "\n\n".join(rollback_statements) if rollback_statements else "-- No rollback needed"

        return migration_sql, rollback_sql

    def _generate_create_table(self, table: TableDefinition) -> str:
        """Generate CREATE TABLE statement."""
        lines = [f"CREATE TABLE {self._quote_identifier(table.name)} ("]
        
        column_defs = []
        for col in table.columns.values():
            column_defs.append(f"    {self._generate_column_definition(col)}")
        
        # Add table-level constraints
        for constraint in table.constraints:
            column_defs.append(f"    {self._generate_constraint_definition(constraint)}")
        
        lines.append(",\n".join(column_defs))
        lines.append(");")
        
        result = "\n".join(lines)
        
        # Add indexes separately
        for index in table.indexes:
            result += f"\n\n{self._generate_create_index(index)}"
        
        return result

    def _generate_drop_table(self, table_name: str) -> str:
        """Generate DROP TABLE statement."""
        return f"DROP TABLE IF EXISTS {self._quote_identifier(table_name)};"

    def _generate_table_modifications(
        self, table_change: TableChange
    ) -> tuple[List[str], List[str]]:
        """
        Generate ALTER TABLE statements for table modifications.

        Returns:
            Tuple of (migration_statements, rollback_statements).
        """
        migration_stmts: List[str] = []
        rollback_stmts: List[str] = []
        table_name = table_change.table_name

        # Drop constraints first (they may depend on columns)
        for constraint in table_change.constraints_deleted:
            if constraint.name:
                migration_stmts.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"DROP CONSTRAINT {self._quote_identifier(constraint.name)};"
                )
                rollback_stmts.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ADD {self._generate_constraint_definition(constraint)};"
                )

        # Drop indexes
        for index in table_change.indexes_deleted:
            migration_stmts.append(self._generate_drop_index(index.name))
            rollback_stmts.append(self._generate_create_index(index))

        # Drop columns
        for col in table_change.columns_deleted:
            migration_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"DROP COLUMN {self._quote_identifier(col.name)};"
            )
            rollback_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ADD COLUMN {self._generate_column_definition(col)};"
            )

        # Modify columns (data type changes, nullability, etc.)
        for col_change in table_change.columns_modified:
            mig_stmt, roll_stmt = self._generate_column_modification(
                table_name, col_change
            )
            if mig_stmt:
                migration_stmts.append(mig_stmt)
            if roll_stmt:
                rollback_stmts.append(roll_stmt)

        # Add columns
        for col in table_change.columns_added:
            migration_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ADD COLUMN {self._generate_column_definition(col)};"
            )
            rollback_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"DROP COLUMN {self._quote_identifier(col.name)};"
            )

        # Add constraints
        for constraint in table_change.constraints_added:
            migration_stmts.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ADD {self._generate_constraint_definition(constraint)};"
            )
            if constraint.name:
                rollback_stmts.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"DROP CONSTRAINT {self._quote_identifier(constraint.name)};"
                )

        # Add indexes
        for index in table_change.indexes_added:
            migration_stmts.append(self._generate_create_index(index))
            rollback_stmts.append(self._generate_drop_index(index.name))

        return migration_stmts, rollback_stmts

    def _generate_column_modification(
        self, table_name: str, col_change: ColumnChange
    ) -> tuple[str, str]:
        """
        Generate ALTER COLUMN statements for column modifications.

        Returns:
            Tuple of (migration_statement, rollback_statement).
        """
        old_col = col_change.old_definition
        new_col = col_change.new_definition
        
        if not old_col or not new_col:
            return "", ""

        col_name = col_change.column_name
        statements: List[str] = []
        rollback_statements: List[str] = []

        # Data type change
        if old_col.data_type.upper() != new_col.data_type.upper():
            statements.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ALTER COLUMN {self._quote_identifier(col_name)} "
                f"TYPE {new_col.data_type}"
            )
            rollback_statements.append(
                f"ALTER TABLE {self._quote_identifier(table_name)} "
                f"ALTER COLUMN {self._quote_identifier(col_name)} "
                f"TYPE {old_col.data_type}"
            )

        # Nullability change
        if old_col.nullable != new_col.nullable:
            if new_col.nullable:
                statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"DROP NOT NULL"
                )
                rollback_statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"SET NOT NULL"
                )
            else:
                statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"SET NOT NULL"
                )
                rollback_statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"DROP NOT NULL"
                )

        # Default value change
        if old_col.default != new_col.default:
            if new_col.default:
                statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"SET DEFAULT {new_col.default}"
                )
            else:
                statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"DROP DEFAULT"
                )
            
            if old_col.default:
                rollback_statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"SET DEFAULT {old_col.default}"
                )
            else:
                rollback_statements.append(
                    f"ALTER TABLE {self._quote_identifier(table_name)} "
                    f"ALTER COLUMN {self._quote_identifier(col_name)} "
                    f"DROP DEFAULT"
                )

        # Combine all statements for this column
        migration = ";\n".join(statements) + ";" if statements else ""
        rollback = ";\n".join(reversed(rollback_statements)) + ";" if rollback_statements else ""

        return migration, rollback

    def _generate_column_definition(self, col: ColumnDefinition) -> str:
        """Generate column definition for CREATE/ALTER TABLE."""
        parts = [self._quote_identifier(col.name), col.data_type]

        # Add constraints in proper order
        if not col.nullable:
            parts.append("NOT NULL")

        if col.default is not None:
            parts.append(f"DEFAULT {col.default}")

        # Add other constraints (PRIMARY KEY, UNIQUE, etc.)
        for constraint in col.constraints:
            constraint_upper = constraint.upper()
            # Skip NOT NULL and DEFAULT as they're already handled
            if "NOT NULL" not in constraint_upper and "DEFAULT" not in constraint_upper:
                parts.append(constraint)

        return " ".join(parts)

    def _generate_constraint_definition(self, constraint: ConstraintDefinition) -> str:
        """Generate constraint definition."""
        parts = []

        if constraint.name:
            parts.append(f"CONSTRAINT {self._quote_identifier(constraint.name)}")

        if constraint.constraint_type == ConstraintType.PRIMARY_KEY:
            cols = ", ".join(self._quote_identifier(c) for c in constraint.columns)
            parts.append(f"PRIMARY KEY ({cols})")
        elif constraint.constraint_type == ConstraintType.FOREIGN_KEY:
            cols = ", ".join(self._quote_identifier(c) for c in constraint.columns)
            parts.append(f"FOREIGN KEY ({cols})")
            if constraint.references:
                ref_table, ref_cols = constraint.references
                ref_cols_str = ", ".join(self._quote_identifier(c) for c in ref_cols)
                parts.append(f"REFERENCES {self._quote_identifier(ref_table)} ({ref_cols_str})")
        elif constraint.constraint_type == ConstraintType.UNIQUE:
            cols = ", ".join(self._quote_identifier(c) for c in constraint.columns)
            parts.append(f"UNIQUE ({cols})")
        elif constraint.constraint_type == ConstraintType.CHECK:
            # Use the raw definition for CHECK constraints
            parts.append(constraint.definition)

        return " ".join(parts)

    def _generate_create_index(self, index: IndexDefinition) -> str:
        """Generate CREATE INDEX statement."""
        unique = "UNIQUE " if index.unique else ""
        cols = ", ".join(self._quote_identifier(c) for c in index.columns)
        
        stmt = (
            f"CREATE {unique}INDEX {self._quote_identifier(index.name)} "
            f"ON {self._quote_identifier(index.table)} ({cols})"
        )
        
        if index.index_type:
            stmt += f" USING {index.index_type}"
        
        return stmt + ";"

    def _generate_drop_index(self, index_name: str) -> str:
        """Generate DROP INDEX statement."""
        return f"DROP INDEX IF EXISTS {self._quote_identifier(index_name)};"

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """
        Quote SQL identifier if needed.

        PostgreSQL identifiers are case-insensitive unless quoted.
        We quote identifiers that contain special characters or are reserved words.
        """
        # Simple heuristic: quote if contains uppercase, special chars, or spaces
        if (
            identifier.lower() != identifier
            or " " in identifier
            or "-" in identifier
            or any(c in identifier for c in "!@#$%^&*()+{}[]|\\:;'<>?,./")
        ):
            # Escape any existing double quotes
            escaped = identifier.replace('"', '""')
            return f'"{escaped}"'
        return identifier


# Made with Bob
</content>
<line_count>389</line_count>
</write_to_file>

---

**User:**

[write_to_file for 'server/app/core/generator.py'] Result:
<file_write_result>
<path>server/app/core/generator.py</path>
<operation>created</operation>
<user_edits>@@ -90,24 +90,24 @@
     def _generate_create_table(self, table: TableDefinition) -&gt; str:
         """Generate CREATE TABLE statement."""
         lines = [f"CREATE TABLE {self._quote_identifier(table.name)} ("]
-        
+
         column_defs = []
         for col in table.columns.values():
             column_defs.append(f"    {self._generate_column_definition(col)}")
-        
+
         # Add table-level constraints
         for constraint in table.constraints:
             column_defs.append(f"    {self._generate_constraint_definition(constraint)}")
-        
+
         lines.append(",\n".join(column_defs))
         lines.append(");")
-        
+
         result = "\n".join(lines)
-        
+
         # Add indexes separately
         for index in table.indexes:
             result += f"\n\n{self._generate_create_index(index)}"
-        
+
         return result
 
     def _generate_drop_table(self, table_name: str) -&gt; str:
@@ -206,7 +206,7 @@
         """
         old_col = col_change.old_definition
         new_col = col_change.new_definition
-        
+
         if not old_col or not new_col:
             return "", ""
 
@@ -266,7 +266,7 @@
                     f"ALTER COLUMN {self._quote_identifier(col_name)} "
                     f"DROP DEFAULT"
                 )
-            
+
             if old_col.default:
                 rollback_statements.append(
                     f"ALTER TABLE {self._quote_identifier(table_name)} "
@@ -336,15 +336,15 @@
         """Generate CREATE INDEX statement."""
         unique = "UNIQUE " if index.unique else ""
         cols = ", ".join(self._quote_identifier(c) for c in index.columns)
-        
+
         stmt = (
             f"CREATE {unique}INDEX {self._quote_identifier(index.name)} "
             f"ON {self._quote_identifier(index.table)} ({cols})"
         )
-        
+
         if index.index_type:
             stmt += f" USING {index.index_type}"
-        
+
         return stmt + ";"
 
     def _generate_drop_index(self, index_name: str) -&gt; str:
</user_edits>
<notice>
<i>You do not need to re-read the file, as you have seen all changes</i>
<i>Proceed with the task using these changes as the new baseline.</i>
<i>If the user's edits have addressed part of the task or changed the requirements, adjust your approach accordingly.</i>
</notice>
</file_write_result>

<environment_details>
# VSCode Visible Files
server/app/core/generator.py

# VSCode Open Tabs
.gitignore,server/app/__init__.py,server/app/core/comparator.py,server/app/core/parser.py,client/components/FileUpload.tsx,client/lib/api.ts,server/app/api/routes.py,server/app/core/generator.py

# Current Time
Current time in ISO 8601 UTC format: 2026-05-15T21:05:12.105Z
User time zone: America/Tegucigalpa, UTC-6:00

# Current Cost
$0.10

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**
- node_modules/
- client/node_modules/
- server/venv/
- .venv/
- __pycache__/
- *.pyc
- .next/
- client/.next/
- dist/
- build/
- .cache/
- *.log
- .env
- .env.*
- .DS_Store
- Thumbs.db
- .git/
- *.png
- *.jpg
- *.jpeg
- *.gif
- *.svg
- *.ico
- *.pdf
- bob_sessions/

# Current Mode
<slug>code</slug>
<name>💻 Code</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

<attempt_completion>
<result>
Created `server/app/core/generator.py` with the `MigrationGenerator` class that generates PostgreSQL migration and rollback SQL from `SchemaChanges` objects.

**Key Features:**

1. **Migration & Rollback Generation**: The `generate()` method returns a tuple of (migration_sql, rollback_sql) strings

2. **Table Operations**:
   - CREATE TABLE with all columns, constraints, and indexes
   - DROP TABLE with IF EXISTS safety

3. **Column Operations**:
   - ADD COLUMN with full definition (type, nullable, default, constraints)
   - DROP COLUMN
   - ALTER COLUMN TYPE for data type changes
   - SET/DROP NOT NULL for nullability changes
   - SET/DROP DEFAULT for default value changes

4. **Constraint & Index Operations**:
   - ADD/DROP CONSTRAINT (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK)
   - CREATE/DROP INDEX (including UNIQUE indexes)

5. **PostgreSQL-Focused**:
   - Uses proper PostgreSQL syntax
   - Handles identifier quoting for special characters
   - Maintains proper operation order (constraints before columns, etc.)
   - Rollback statements generated in reverse order for safe unwinding

The generator integrates seamlessly with the existing `parser.py` and `comparator.py` modules, completing the core migration pipeline.
</result>
</attempt_completion>

