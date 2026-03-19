# app/models/base.py
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos."""
    pass


class TimestampMixin:
    """
    Agrega created_at y updated_at a cualquier modelo que lo herede.
    SQLAlchemy gestiona los valores automaticamente via server_default y onupdate.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
