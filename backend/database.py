from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


database_url = config.normalize_database_url(config.DATABASE_URL)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite:") else {}
engine = create_engine(database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from .models import Base as ModelBase

    ModelBase.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.execute(text("SELECT 1 FROM parking_slots LIMIT 1")).first() is None:
            seed_demo_data(db)
        if db.execute(text("SELECT 1 FROM network_devices LIMIT 1")).first() is None:
            seed_device_data(db)
        if db.execute(text("SELECT 1 FROM system_events LIMIT 1")).first() is None:
            seed_event_data(db)


def reset_database() -> None:
    from .models import Base as ModelBase

    ModelBase.metadata.drop_all(bind=engine)
    ModelBase.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_data(db)
        seed_device_data(db)
        seed_event_data(db)


def seed_demo_data(db: Session) -> None:
    from .models import ParkingSlot, VehicleRecord

    slots = [
        ("P01", "AVAILABLE", "ONLINE", "192.168.10.101", "System booted", "2026-10-12T08:00:00"),
        ("P02", "AVAILABLE", "ONLINE", "192.168.10.102", "Awaiting vehicle", "2026-10-12T08:05:00"),
        ("P03", "OCCUPIED", "ONLINE", "192.168.10.103", "Vehicle entry assigned", "2026-10-12T08:10:00"),
        ("P04", "AVAILABLE", "ONLINE", "192.168.10.104", "Awaiting vehicle", "2026-10-12T08:12:00"),
        ("P05", "OCCUPIED", "ONLINE", "192.168.10.105", "Vehicle entry assigned", "2026-10-12T08:18:00"),
        ("P06", "AVAILABLE", "ONLINE", "192.168.10.106", "Awaiting vehicle", "2026-10-12T08:20:00"),
        ("P07", "SENSOR_OFFLINE", "OFFLINE", "192.168.10.107", "Sensor disconnect", "2026-10-12T08:29:00"),
        ("P08", "AVAILABLE", "ONLINE", "192.168.10.108", "Awaiting vehicle", "2026-10-12T08:30:00"),
        ("P09", "AVAILABLE", "ONLINE", "192.168.10.109", "Awaiting vehicle", "2026-10-12T08:32:00"),
        ("P10", "AVAILABLE", "ONLINE", "192.168.10.110", "Awaiting vehicle", "2026-10-12T08:35:00"),
    ]

    for slot_id, status, sensor_status, sensor_ip, last_event, last_update in slots:
        db.add(
            ParkingSlot(
                slot_id=slot_id,
                status=status,
                sensor_status=sensor_status,
                sensor_ip=sensor_ip,
                last_event=last_event,
                last_update=datetime.fromisoformat(last_update),
            )
        )
    db.add_all(
        [
            VehicleRecord(
                registration_number="MH12AB1234",
                slot_id="P03",
                entry_time=datetime.fromisoformat("2026-10-12T08:10:00"),
                status="ACTIVE",
            ),
            VehicleRecord(
                registration_number="MH12CD5678",
                slot_id="P05",
                entry_time=datetime.fromisoformat("2026-10-12T08:18:00"),
                status="ACTIVE",
            ),
        ]
    )
    db.commit()


def seed_device_data(db: Session) -> None:
    from .models import NetworkDevice

    devices = [
        ("Router", "Router", "192.168.10.1", "ONLINE", "2026-10-12T08:00:00", "Routing table active"),
        ("IoT Gateway", "Gateway", "192.168.10.2", "ONLINE", "2026-10-12T08:02:00", "Gateway heartbeat OK"),
        ("Network Switch", "Switch", "192.168.10.3", "ONLINE", "2026-10-12T08:03:00", "Port mirroring active"),
        ("Application Server", "Server", "192.168.10.10", "ONLINE", "2026-10-12T08:02:30", "API service healthy"),
        ("Database Server", "Server", "192.168.10.20", "ONLINE", "2026-10-12T08:04:00", "Database synchronized"),
        ("Administrator Client", "Client", "192.168.10.100", "ONLINE", "2026-10-12T08:06:00", "Dashboard online"),
        *[
            (
                f"Parking Sensor {i}",
                "Sensor",
                f"192.168.10.{100 + i}",
                "OFFLINE" if i == 7 else "ONLINE",
                f"2026-10-12T08:{(i * 3) % 60:02d}:00",
                "Sensor disconnected" if i == 7 else "Sensor heartbeat OK",
            )
            for i in range(1, 11)
        ],
    ]

    for name, device_type, ip, status, last_seen, event in devices:
        db.add(
            NetworkDevice(
                name=name,
                device_type=device_type,
                ip=ip,
                status=status,
                last_seen=datetime.fromisoformat(last_seen),
                associated_events=event,
            )
        )
    db.commit()


def seed_event_data(db: Session) -> None:
    from .models import SystemEvent

    events = [
        ("parking", "MH12AB1234", "P03", "ENTRY", "Vehicle MH12AB1234 entered and assigned to P03", "2026-10-12T08:10:00"),
        ("parking", "MH12CD5678", "P05", "ENTRY", "Vehicle MH12CD5678 entered and assigned to P05", "2026-10-12T08:18:00"),
        ("network", "Parking Sensor 7", "IoT Gateway", "FAILURE", "Sensor disconnected from gateway", "2026-10-12T08:29:00"),
        ("network", "Administrator Client", "Application Server", "SUCCESS", "Connectivity test successful", "2026-10-12T08:35:00"),
    ]
    for category, source, destination, event_type, details, timestamp in events:
        db.add(
            SystemEvent(
                category=category,
                source=source,
                destination=destination,
                event_type=event_type,
                details=details,
                created_at=datetime.fromisoformat(timestamp),
            )
        )
    db.commit()
