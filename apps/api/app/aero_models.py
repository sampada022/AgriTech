from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from .models import now


class AeroScan(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    source: str = "upload"  # upload | sample
    original_name: str = ""
    status: str = "COMPLETED"  # COMPLETED | FAILED
    created_at: datetime = Field(default_factory=now)
    gsd_cm: float = 1.0
    result: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    error: Optional[str] = None


class LeafPhoto(SQLModel, table=True):
    id: str = Field(primary_key=True)
    scan_id: str = Field(foreign_key="aeroscan.id", index=True)
    hotspot_id: str
    filename: str
    species: str = "Not sure"  # reported by the scout; there is no species classifier in this build
    note: str = ""
    created_at: datetime = Field(default_factory=now)
    tile_features: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # aerial features saved as a labelled example


class HotspotState(SQLModel, table=True):
    """Field-work state of a hotspot: new -> visited -> treated, or dismissed (false alarm)."""
    pk: Optional[int] = Field(default=None, primary_key=True)
    scan_id: str = Field(foreign_key="aeroscan.id", index=True)
    hotspot_id: str
    state: str = "new"  # new | visited | treated | dismissed
    note: str = ""
    updated_at: datetime = Field(default_factory=now)


class AeroUser(SQLModel, table=True):
    id: str = Field(primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    salt: str
    pw_hash: str
    created_at: datetime = Field(default_factory=now)
