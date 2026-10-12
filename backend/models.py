from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, utcnow_naive


class ParkingSlot(Base):
    __tablename__ = "parking_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slot_id: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="AVAILABLE")
    sensor_status: Mapped[str] = mapped_column(String(30), default="ONLINE")
    sensor_ip: Mapped[str] = mapped_column(String(30), nullable=False)
    last_update: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    last_event: Mapped[str] = mapped_column(String(200), default="System initialized")

    vehicle_records: Mapped[list["VehicleRecord"]] = relationship(back_populates="slot")


class VehicleRecord(Base):
    __tablename__ = "vehicle_records"
    __table_args__ = (
        Index(
            "uq_vehicle_records_active_registration",
            "registration_number",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_vehicle_records_active_slot",
            "slot_id",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    registration_number: Mapped[str] = mapped_column(String(20), index=True)
    slot_id: Mapped[str] = mapped_column(String(8), ForeignKey("parking_slots.slot_id"))
    entry_time: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")

    slot: Mapped[ParkingSlot] = relationship(back_populates="vehicle_records")


class NetworkDevice(Base):
    __tablename__ = "network_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    device_type: Mapped[str] = mapped_column(String(40), default="Device")
    ip: Mapped[str] = mapped_column(String(30), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="ONLINE")
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    associated_events: Mapped[str] = mapped_column(String(200), default="No associated events")


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(30), default="system")
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(80), nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), default="INFO")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)


class ConnectivityTest(Base):
    __tablename__ = "connectivity_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_ip: Mapped[str] = mapped_column(String(30), nullable=False)
    destination_ip: Mapped[str] = mapped_column(String(30), nullable=False)
    test_status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    tested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    failure_reason: Mapped[str | None] = mapped_column(String(150), nullable=True)
