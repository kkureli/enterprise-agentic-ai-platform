from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    users = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    documents = relationship(
        "Document",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    assets = relationship(
        "Asset",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    maintenance_records = relationship(
        "MaintenanceRecord",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    maintenance_tickets = relationship(
        "MaintenanceTicket",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
