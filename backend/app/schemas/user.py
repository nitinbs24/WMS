"""User request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, EmailStr


UserRole = Literal["admin", "manager", "staff"]


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    password: str | None = None
