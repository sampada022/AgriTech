from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from .models import now


class AeroUser(SQLModel, table=True):
    """Website (Studio) login: email + password, unrelated to the farmer OTP flow."""

    id: str = Field(primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    salt: str
    pw_hash: str
    created_at: datetime = Field(default_factory=now)
