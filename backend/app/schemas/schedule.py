"""Schedule schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScheduleOut(BaseModel):
    id: uuid.UUID
    goal: str
    algorithm: str
    scope: str
    cron_expression: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    goal: str
    algorithm: str
    scope: str
    cron_expression: str
