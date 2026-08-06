"""
SQL Validator Service

Uses sqlglot to parse the generated SQL query's AST and validate it against the
live database schema. Ensures that:
  - Only allowed read-only statements (SELECT, WITH) are used.
  - No unsafe keywords/statements exist.
  - Referenced tables exist in the schema.
  - Referenced columns exist in their respective tables.
  - Aliases resolve correctly.
"""

from __future__ import annotations

import logging
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.schemas.database_schema import DatabaseSchemaResponse

logger = logging.getLogger(__name__)


class SQLValidationError(ValueError):
    """Raised when the SQL query violates quality/safety rules (e.g. DELETE, syntax error)."""


class SQLSchemaValidationError(ValueError):
    """
    Raised when the SQL query references unknown tables or columns.
    Contains structured feedback for the LLM retry prompt.
    """
    def __init__(self, message: str, type_: str, table: str | None = None, column: str | None = None, suggestions: list[str] | None = None):
        super().__init__(message)
        self.type = type_
        self.table = table
        self.column = column
        self.suggestions = suggestions or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "table": self.table,
            "column": self.column,
            "suggestions": self.suggestions,
            "message": self.args[0]
        }


def validate_sql_schema(sql: str, schema: DatabaseSchemaResponse) -> str:
    """
    Parse SQL with sqlglot and validate against the schema.
    Returns the formatted SQL string if valid.
    Raises SQLValidationError for unsafe/invalid SQL.
    Raises SQLSchemaValidationError for schema mismatch.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Generated SQL is empty.")

    try:
        # We parse the query and expect exactly one statement.
        statements = sqlglot.parse(sql, dialect=schema.dialect)
    except ParseError as e:
        raise SQLValidationError(f"SQL syntax error: {e}") from e

    if not statements:
        raise SQLValidationError("Generated SQL is empty.")
    
    # Check for multiple statements
    if len([s for s in statements if s]) > 1:
        raise SQLValidationError("Multiple SQL statements are not permitted.")

    ast = statements[0]
    if ast is None:
         raise SQLValidationError("Generated SQL could not be parsed.")

    # 1. Check statement type (Only SELECT or WITH)
    if not isinstance(ast, (exp.Select, exp.CTE, exp.With)):
        raise SQLValidationError(f"Only SELECT or WITH queries are allowed. Got {ast.key}.")
    
    # 2. Block unsafe nodes recursively
    for node in ast.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command)):
            raise SQLValidationError(f"Forbidden SQL node type found: {node.key}")

    # 3. Reject SELECT * (but allow COUNT(*))
    for node in ast.find_all(exp.Star):
        if not isinstance(node.parent, exp.Count):
            raise SQLValidationError("SELECT * is not allowed. Please explicitly specify columns.")

    # Build schema map from DatabaseSchemaResponse
    schema_tables: dict[str, set[str]] = {}
    for table in schema.tables:
        schema_tables[table.name.lower()] = {col.name.lower() for col in table.columns}
    
    # Analyze table aliases and referenced tables
    table_aliases: dict[str, str] = {}
    
    # Collect CTE names to ignore them in schema checks
    cte_names = set()
    for cte in ast.find_all(exp.CTE):
        cte_names.add(cte.alias.lower())

    for table_node in ast.find_all(exp.Table):
        table_name = table_node.name.lower()
        if not table_name or table_name in cte_names:
            continue
            
        if table_name not in schema_tables:
            raise SQLSchemaValidationError(
                message=f"Unknown table: {table_node.name}",
                type_="schema_validation",
                table=table_node.name,
                suggestions=list(schema_tables.keys())
            )
            
        alias = table_node.alias.lower()
        if alias:
            if alias in table_aliases and table_aliases[alias] != table_name:
                raise SQLValidationError(f"Duplicate/Ambiguous alias: {alias}")
            table_aliases[alias] = table_name
        else:
            table_aliases[table_name] = table_name
            
    # Check cartesian joins (CROSS JOIN or JOIN without ON/USING)
    for join_node in ast.find_all(exp.Join):
        if join_node.args.get("side") == "CROSS" or (not join_node.args.get("on") and not join_node.args.get("using")):
            raise SQLValidationError("Cartesian joins (CROSS JOIN or JOIN without ON/USING) are not permitted.")
            
    # Collect SELECT aliases
    select_aliases = set()
    for select_expr in ast.find_all(exp.Alias):
        select_aliases.add(select_expr.alias.lower())
            
    # Validate columns
    for column_node in ast.find_all(exp.Column):
        col_name = column_node.name.lower()
        table_ref = column_node.table.lower() if column_node.table else None
        
        # Skip CTE columns and SELECT aliases
        if table_ref and table_ref in cte_names:
            continue
        if col_name in select_aliases:
            continue
            
        if not table_ref:
            # If no table alias is provided, check if the column exists in ANY of the referenced physical tables.
            found_in_tables = []
            for t_alias, t_name in table_aliases.items():
                if t_name in schema_tables and col_name in schema_tables[t_name]:
                    found_in_tables.append(t_name)
                    
            if not found_in_tables:
                all_cols = []
                for cols in schema_tables.values():
                    all_cols.extend(cols)
                raise SQLSchemaValidationError(
                    message=f"Unknown column: {column_node.name}",
                    type_="schema_validation",
                    column=column_node.name,
                    suggestions=list(set(all_cols))
                )
        else:
            # table_ref is provided
            if table_ref not in table_aliases and table_ref not in schema_tables:
                raise SQLSchemaValidationError(
                    message=f"Unknown table alias or table: {table_ref}",
                    type_="schema_validation",
                    table=table_ref,
                    suggestions=list(table_aliases.keys()) + list(schema_tables.keys())
                )
                
            actual_table_name = table_aliases.get(table_ref, table_ref)
            if actual_table_name in schema_tables:
                if col_name not in schema_tables[actual_table_name]:
                    raise SQLSchemaValidationError(
                        message=f"Unknown column: {table_ref}.{column_node.name}",
                        type_="schema_validation",
                        table=actual_table_name,
                        column=column_node.name,
                        suggestions=list(schema_tables[actual_table_name])
                    )
                    
    return ast.sql(dialect=schema.dialect) + ";"


