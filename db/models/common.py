"""Shared ORM column types."""

from sqlalchemy import BigInteger, Integer


def bigint_type():
    """Use INTEGER on SQLite so local tests retain autoincrement semantics."""
    return BigInteger().with_variant(Integer, "sqlite")
