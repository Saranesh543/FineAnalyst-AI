"""
Database Schema Pydantic Models

Defines the structured response models used by the Schema Intelligence
module to describe a discovered database schema: tables, columns,
primary keys, foreign keys, and indexes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Column-level models
# ---------------------------------------------------------------------------


class ColumnInfo(BaseModel):
    """Metadata for a single table column."""

    name: str = Field(description="Column name.")
    type: str = Field(description="SQL data type as a string (e.g. 'VARCHAR(255)').")
    nullable: bool = Field(description="Whether the column accepts NULL values.")
    default: Any = Field(default=None, description="Column default value, if any.")
    autoincrement: bool = Field(
        default=False,
        description="True when the column is auto-incremented by the database engine.",
    )
    comment: str | None = Field(
        default=None, description="Optional column comment / description."
    )


# ---------------------------------------------------------------------------
# Foreign-key model
# ---------------------------------------------------------------------------


class ForeignKeyInfo(BaseModel):
    """Metadata for a single foreign-key constraint."""

    name: str | None = Field(
        default=None, description="Constraint name, if the database exposes one."
    )
    constrained_columns: list[str] = Field(
        description="Columns in this table that form the FK."
    )
    referred_table: str = Field(description="Target table name.")
    referred_columns: list[str] = Field(description="Target column names.")


# ---------------------------------------------------------------------------
# Index model
# ---------------------------------------------------------------------------


class IndexInfo(BaseModel):
    """Metadata for a single table index."""

    name: str | None = Field(default=None, description="Index name.")
    columns: list[str] = Field(description="Columns covered by the index.")
    unique: bool = Field(description="True if this is a UNIQUE index.")


# ---------------------------------------------------------------------------
# Table model
# ---------------------------------------------------------------------------


class TableInfo(BaseModel):
    """Metadata for a single database table."""

    name: str = Field(description="Table name.")
    columns: list[ColumnInfo] = Field(
        default_factory=list, description="Ordered list of column descriptors."
    )
    primary_keys: list[str] = Field(
        default_factory=list, description="Column names that form the primary key."
    )
    foreign_keys: list[ForeignKeyInfo] = Field(
        default_factory=list, description="Foreign-key constraints defined on this table."
    )
    indexes: list[IndexInfo] = Field(
        default_factory=list,
        description="Indexes defined on this table (excluding the implicit PK index).",
    )
    row_count: int | None = Field(
        default=None,
        description="Approximate row count (populated only when supported and cheap).",
    )


# ---------------------------------------------------------------------------
# Top-level database schema model
# ---------------------------------------------------------------------------


class DatabaseSchemaResponse(BaseModel):
    """Full schema description returned by GET /api/v1/schema."""

    database: str = Field(
        description="Database name or file path (dialect-dependent)."
    )
    dialect: str = Field(
        description="SQLAlchemy dialect identifier (e.g. 'sqlite', 'postgresql')."
    )
    table_count: int = Field(description="Total number of discovered tables.")
    tables: list[TableInfo] = Field(
        default_factory=list,
        description="Metadata for every discovered table.",
    )
    is_empty: bool = Field(
        default=False,
        description="True when no tables exist in the connected database.",
    )
    message: str | None = Field(
        default=None,
        description=(
            "Optional human-readable summary. Populated when the schema is "
            "empty or a noteworthy condition is detected."
        ),
    )
