from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    asset_code: str
    name: str
    location: str
    status: str
    active_error_code: str | None
    created_at: datetime
    updated_at: datetime


class MaintenanceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    asset_id: UUID
    asset_code: str | None = None
    maintenance_date: date
    maintenance_type: str
    description: str
    technician: str
    created_at: datetime


class MaintenanceTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    asset_id: UUID
    asset_code: str | None = None
    issue: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
