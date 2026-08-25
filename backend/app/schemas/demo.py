from uuid import UUID

from pydantic import BaseModel, Field


class DemoTenantRead(BaseModel):
    id: UUID
    name: str
    description: str
    short_label: str = Field(
        description="Short industry label for the playground selector.",
    )
