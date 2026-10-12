from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ParkingSlotOut(BaseModel):
    id: int
    slot_id: str
    status: str
    sensor_status: str
    sensor_ip: str
    last_update: datetime
    last_event: str


class VehicleEntryRequest(BaseModel):
    registration_number: str = Field(..., min_length=3, max_length=20)
    slot_id: str | None = Field(default=None, min_length=1, max_length=8)

    @field_validator("registration_number")
    @classmethod
    def normalize_registration(cls, value: str) -> str:
        registration = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9 -]{3,20}", registration):
            raise ValueError("Registration number must be 3–20 letters or numbers, with optional spaces or hyphens")
        normalized = registration.replace("-", "").replace(" ", "")
        if len(normalized) < 3:
            raise ValueError("Registration number must contain at least 3 letters or numbers")
        return normalized

    @field_validator("slot_id", mode="before")
    @classmethod
    def normalize_slot_id(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class VehicleRecordOut(BaseModel):
    id: int
    registration_number: str
    slot_id: str
    entry_time: datetime
    exit_time: datetime | None = None
    status: str


class DeviceOut(BaseModel):
    id: int
    name: str
    device_type: str
    ip: str
    status: str
    last_seen: datetime
    associated_events: str


class ConnectivityTestRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=80)
    destination: str = Field(..., min_length=1, max_length=80)
    test_type: Literal["ping", "traceroute"] = "ping"

    @field_validator("source", "destination", mode="before")
    @classmethod
    def trim_device_name(cls, value: str) -> str:
        return value.strip()


class ConnectivityTestOut(BaseModel):
    source_ip: str
    destination_ip: str
    test_status: str
    latency_ms: int
    timestamp: datetime
    failure_reason: str | None = None


class AnalyticsSummary(BaseModel):
    total_capacity: int
    available_slots: int
    occupied_slots: int
    offline_slots: int
    occupancy_percentage: float
    active_devices: int
    vehicle_entries: int
    vehicle_exits: int
    connectivity_success: int
    connectivity_failure: int
    avg_latency_ms: float


class EventLogOut(BaseModel):
    id: int
    category: str
    source: str
    destination: str | None
    event_type: str
    details: str
    created_at: datetime


class SuccessResponse(BaseModel):
    success: bool
    message: str
    details: str | None = None
