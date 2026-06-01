"""SQLAlchemy declarative base for Eluven ORM models."""

from enum import Enum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase


def str_enum(enum_class: type[Enum]) -> SQLEnum:
    """PostgreSQL VARCHAR-backed enum matching Alembic migration schema."""
    return SQLEnum(enum_class, native_enum=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
