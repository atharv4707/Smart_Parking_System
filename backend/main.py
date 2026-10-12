from __future__ import annotations

import logging
import os
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import config, schemas
from .database import SessionLocal, engine, get_db, init_db, reset_database, utcnow_naive
from .models import ConnectivityTest, NetworkDevice, ParkingSlot, SystemEvent, VehicleRecord

app = FastAPI(title="SMART PARK API", version="1.0.0")
logger = logging.getLogger(__name__)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database operation failed for %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database operation failed. No changes were saved; please retry."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get_cors_origins(os.getenv("CORS_ORIGINS")),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "SMART PARK backend",
        "timestamp": utcnow_naive().isoformat(),
        "database": engine.dialect.name,
    }


@app.get("/api/parking/slots", response_model=list[schemas.ParkingSlotOut])
def get_slots(db: Session = Depends(get_db)) -> list[ParkingSlot]:
    return db.execute(select(ParkingSlot).order_by(ParkingSlot.slot_id)).scalars().all()


@app.get("/api/parking/slots/{slot_id}", response_model=schemas.ParkingSlotOut)
def get_slot(slot_id: str, db: Session = Depends(get_db)) -> ParkingSlot:
    slot = db.execute(select(ParkingSlot).where(ParkingSlot.slot_id == slot_id.upper())).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")
    return slot


@app.post("/api/vehicles/entry", response_model=schemas.SuccessResponse)
def vehicle_entry(payload: schemas.VehicleEntryRequest, db: Session = Depends(get_db)) -> dict:
    registration = payload.registration_number

    active_record = db.execute(
        select(VehicleRecord).where(
            VehicleRecord.registration_number == registration,
            VehicleRecord.status == "ACTIVE",
        )
    ).first()
    if active_record is not None:
        raise HTTPException(status_code=409, detail="Vehicle already has an active parking session")

    slot_statement = select(ParkingSlot).where(
        ParkingSlot.status == "AVAILABLE",
        ParkingSlot.sensor_status == "ONLINE",
    )
    if payload.slot_id:
        slot_statement = slot_statement.where(ParkingSlot.slot_id == payload.slot_id)
    else:
        slot_statement = slot_statement.order_by(ParkingSlot.slot_id)
    slot = db.execute(slot_statement).scalars().first()
    if slot is None:
        if payload.slot_id and db.execute(
            select(ParkingSlot).where(ParkingSlot.slot_id == payload.slot_id)
        ).scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Selected slot not found")
        raise HTTPException(status_code=409, detail="No available slots are currently eligible for entry")

    slot.status = "OCCUPIED"
    slot.last_update = utcnow_naive()
    slot.last_event = f"Vehicle {registration} assigned"

    record = VehicleRecord(
        registration_number=registration,
        slot_id=slot.slot_id,
        entry_time=utcnow_naive(),
        status="ACTIVE",
    )
    db.add(record)
    db.add(
        SystemEvent(
            category="parking",
            source=registration,
            destination=slot.slot_id,
            event_type="ENTRY",
            details=f"Vehicle {registration} entered and assigned to {slot.slot_id}",
            created_at=utcnow_naive(),
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle or slot assignment changed; please retry",
        ) from exc
    return {"success": True, "message": "Vehicle entered successfully", "details": f"Assigned slot {slot.slot_id}"}


@app.post("/api/parking/slots/{slot_id}/exit", response_model=schemas.SuccessResponse)
def exit_slot(slot_id: str, db: Session = Depends(get_db)) -> dict:
    slot = db.execute(select(ParkingSlot).where(ParkingSlot.slot_id == slot_id.upper())).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.status != "OCCUPIED":
        raise HTTPException(status_code=409, detail="Selected slot is not occupied")

    vehicle = db.execute(
        select(VehicleRecord)
        .where(VehicleRecord.slot_id == slot.slot_id, VehicleRecord.status == "ACTIVE")
        .order_by(VehicleRecord.entry_time.desc())
    ).scalars().first()
    if vehicle is not None:
        vehicle.status = "EXITED"
        vehicle.exit_time = utcnow_naive()
        source = vehicle.registration_number
        details = f"Vehicle {vehicle.registration_number} exited from {slot.slot_id}"
    else:
        source = slot.slot_id
        details = f"Occupied demo bay {slot.slot_id} released"

    slot.status = "AVAILABLE" if slot.sensor_status == "ONLINE" else "SENSOR_OFFLINE"
    slot.last_update = utcnow_naive()
    slot.last_event = details
    db.add(
        SystemEvent(
            category="parking",
            source=source,
            destination=slot.slot_id,
            event_type="EXIT",
            details=details,
            created_at=utcnow_naive(),
        )
    )
    db.commit()
    return {"success": True, "message": "Vehicle exited successfully", "details": details}


@app.post("/api/vehicles/{vehicle_id}/exit", response_model=schemas.SuccessResponse)
def vehicle_exit(vehicle_id: str, db: Session = Depends(get_db)) -> dict:
    vehicle = db.execute(
        select(VehicleRecord)
        .where(VehicleRecord.registration_number == vehicle_id.upper(), VehicleRecord.status == "ACTIVE")
        .order_by(VehicleRecord.entry_time.desc())
    ).scalars().first()
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Active vehicle session not found")

    slot = db.execute(select(ParkingSlot).where(ParkingSlot.slot_id == vehicle.slot_id)).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=404, detail="Assigned slot not found")

    vehicle.status = "EXITED"
    vehicle.exit_time = utcnow_naive()
    slot.status = "AVAILABLE" if slot.sensor_status == "ONLINE" else "SENSOR_OFFLINE"
    slot.last_update = utcnow_naive()
    slot.last_event = f"Vehicle {vehicle.registration_number} exited"

    db.add(
        SystemEvent(
            category="parking",
            source=vehicle.registration_number,
            destination=slot.slot_id,
            event_type="EXIT",
            details=f"Vehicle {vehicle.registration_number} exited from {slot.slot_id}",
            created_at=utcnow_naive(),
        )
    )
    db.commit()
    return {"success": True, "message": "Vehicle exited successfully", "details": f"Slot {slot.slot_id} released"}


@app.get("/api/vehicles/active", response_model=list[schemas.VehicleRecordOut])
def active_vehicles(db: Session = Depends(get_db)) -> list[VehicleRecord]:
    return db.execute(select(VehicleRecord).where(VehicleRecord.status == "ACTIVE").order_by(VehicleRecord.entry_time.desc())).scalars().all()


@app.get("/api/vehicles/history", response_model=list[schemas.VehicleRecordOut])
def vehicle_history(db: Session = Depends(get_db)) -> list[VehicleRecord]:
    return db.execute(select(VehicleRecord).order_by(VehicleRecord.entry_time.desc())).scalars().all()


@app.post("/api/sensors/{sensor_id}/disconnect", response_model=schemas.SuccessResponse)
def disconnect_sensor(sensor_id: str, db: Session = Depends(get_db)) -> dict:
    slot = db.execute(select(ParkingSlot).where(ParkingSlot.slot_id == sensor_id.upper())).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=404, detail="Sensor slot not found")
    slot.sensor_status = "OFFLINE"
    slot.status = "OCCUPIED" if slot.status == "OCCUPIED" else "SENSOR_OFFLINE"
    slot.last_update = utcnow_naive()
    slot.last_event = "Sensor disconnected"
    device = db.execute(select(NetworkDevice).where(NetworkDevice.ip == slot.sensor_ip)).scalar_one_or_none()
    if device:
        device.status = "OFFLINE"
        device.last_seen = utcnow_naive()
        device.associated_events = "Sensor disconnected"
    db.add(
        SystemEvent(
            category="network",
            source=slot.slot_id,
            destination="IoT Gateway",
            event_type="FAILURE",
            details=f"Sensor {slot.slot_id} disconnected and stopped reporting telemetry",
            created_at=utcnow_naive(),
        )
    )
    db.commit()
    return {"success": True, "message": "Sensor disconnected", "details": f"{slot.slot_id} marked offline"}


@app.post("/api/sensors/{sensor_id}/reconnect", response_model=schemas.SuccessResponse)
def reconnect_sensor(sensor_id: str, db: Session = Depends(get_db)) -> dict:
    slot = db.execute(select(ParkingSlot).where(ParkingSlot.slot_id == sensor_id.upper())).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=404, detail="Sensor slot not found")
    slot.sensor_status = "ONLINE"
    slot.status = "OCCUPIED" if slot.status == "OCCUPIED" else "AVAILABLE"
    slot.last_update = utcnow_naive()
    slot.last_event = "Sensor reconnected"
    device = db.execute(select(NetworkDevice).where(NetworkDevice.ip == slot.sensor_ip)).scalar_one_or_none()
    if device:
        device.status = "ONLINE"
        device.last_seen = utcnow_naive()
        device.associated_events = "Sensor reconnected"
    db.add(
        SystemEvent(
            category="network",
            source=slot.slot_id,
            destination="IoT Gateway",
            event_type="RECOVERY",
            details=f"Sensor {slot.slot_id} recovered and rejoined the network",
            created_at=utcnow_naive(),
        )
    )
    db.commit()
    return {"success": True, "message": "Sensor reconnected", "details": f"{slot.slot_id} is back online"}


@app.get("/api/network/devices", response_model=list[schemas.DeviceOut])
def list_devices(db: Session = Depends(get_db)) -> list[NetworkDevice]:
    return db.execute(select(NetworkDevice).order_by(NetworkDevice.id)).scalars().all()


@app.post("/api/network/connectivity-test", response_model=schemas.ConnectivityTestOut)
def connectivity_test(payload: schemas.ConnectivityTestRequest, db: Session = Depends(get_db)) -> dict:
    source_device = db.execute(select(NetworkDevice).where(NetworkDevice.name == payload.source)).scalar_one_or_none()
    destination_device = db.execute(select(NetworkDevice).where(NetworkDevice.name == payload.destination)).scalar_one_or_none()
    if source_device is None or destination_device is None:
        raise HTTPException(status_code=404, detail="Selected device not found")
    test_name = "Traceroute" if payload.test_type == "traceroute" else "Ping"

    source_slot = db.execute(select(ParkingSlot).where(ParkingSlot.sensor_ip == source_device.ip)).scalar_one_or_none()
    destination_slot = db.execute(select(ParkingSlot).where(ParkingSlot.sensor_ip == destination_device.ip)).scalar_one_or_none()

    if source_device.status != "ONLINE" or (source_slot and source_slot.sensor_status != "ONLINE"):
        failure_reason = f"Source device {source_device.name} is offline"
        result = ConnectivityTest(
            source_ip=source_device.ip,
            destination_ip=destination_device.ip,
            test_status="FAILURE",
            latency_ms=0,
            tested_at=utcnow_naive(),
            failure_reason=failure_reason,
        )
        db.add(result)
        db.add(
            SystemEvent(
                category="network",
                source=source_device.name,
                destination=destination_device.name,
                event_type="FAILURE",
                details=f"{test_name} failed: {failure_reason}",
                created_at=utcnow_naive(),
            )
        )
        db.commit()
        return {
            "source_ip": source_device.ip,
            "destination_ip": destination_device.ip,
            "test_status": "FAILURE",
            "latency_ms": 0,
            "timestamp": result.tested_at,
            "failure_reason": failure_reason,
        }

    if destination_device.status != "ONLINE" or (destination_slot and destination_slot.sensor_status != "ONLINE"):
        failure_reason = f"Destination device {destination_device.name} is offline"
        result = ConnectivityTest(
            source_ip=source_device.ip,
            destination_ip=destination_device.ip,
            test_status="FAILURE",
            latency_ms=0,
            tested_at=utcnow_naive(),
            failure_reason=failure_reason,
        )
        db.add(result)
        db.add(
            SystemEvent(
                category="network",
                source=source_device.name,
                destination=destination_device.name,
                event_type="FAILURE",
                details=f"{test_name} failed: {failure_reason}",
                created_at=utcnow_naive(),
            )
        )
        db.commit()
        return {
            "source_ip": source_device.ip,
            "destination_ip": destination_device.ip,
            "test_status": "FAILURE",
            "latency_ms": 0,
            "timestamp": result.tested_at,
            "failure_reason": failure_reason,
        }

    latency = 14 if source_device.device_type == "Sensor" else 32
    result = ConnectivityTest(
        source_ip=source_device.ip,
        destination_ip=destination_device.ip,
        test_status="SUCCESS",
        latency_ms=latency,
        tested_at=utcnow_naive(),
    )
    db.add(result)
    db.add(
        SystemEvent(
            category="network",
            source=source_device.name,
            destination=destination_device.name,
            event_type="SUCCESS",
            details=f"{test_name} succeeded with {latency} ms latency",
            created_at=utcnow_naive(),
        )
    )
    db.commit()
    return {
        "source_ip": source_device.ip,
        "destination_ip": destination_device.ip,
        "test_status": "SUCCESS",
        "latency_ms": latency,
        "timestamp": result.tested_at,
        "failure_reason": None,
    }


@app.get("/api/network/logs", response_model=list[schemas.EventLogOut])
def network_logs(
    db: Session = Depends(get_db),
    event_type: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query()] = None,
    destination: Annotated[str | None, Query()] = None,
    result: Annotated[str | None, Query()] = None,
    date: Annotated[date | None, Query()] = None,
) -> list[SystemEvent]:
    statement = select(SystemEvent)
    if event_type:
        statement = statement.where(SystemEvent.event_type == event_type.upper())
    if source:
        statement = statement.where(SystemEvent.source.ilike(f"%{source}%"))
    if destination:
        statement = statement.where(SystemEvent.destination.ilike(f"%{destination}%"))
    if result:
        statement = statement.where(SystemEvent.event_type == result.upper())
    if date:
        statement = statement.where(func.date(SystemEvent.created_at) == date.isoformat())
    return db.execute(statement.order_by(SystemEvent.created_at.desc())).scalars().all()


@app.delete("/api/network/logs")
def clear_network_logs(
    category: Literal["all", "parking", "network"] = Query(default="all"),
    db: Session = Depends(get_db),
) -> dict:
    statement = delete(SystemEvent)
    if category != "all":
        statement = statement.where(SystemEvent.category == category)
    result = db.execute(statement)
    db.commit()
    return {"success": True, "message": f"Cleared {result.rowcount or 0} {category} event(s)"}


@app.post("/api/demo/reset")
def reset_demo() -> dict:
    reset_database()
    return {"success": True, "message": "Demo data reset successfully"}


@app.get("/api/analytics/summary", response_model=schemas.AnalyticsSummary)
def analytics_summary(db: Session = Depends(get_db)) -> dict:
    slots = db.execute(select(ParkingSlot)).scalars().all()
    total_capacity = len(slots)
    available_slots = sum(1 for slot in slots if slot.status == "AVAILABLE" and slot.sensor_status == "ONLINE")
    occupied_slots = sum(1 for slot in slots if slot.status == "OCCUPIED")
    offline_slots = sum(1 for slot in slots if slot.sensor_status != "ONLINE")
    active_devices = db.execute(select(func.count()).select_from(NetworkDevice).where(NetworkDevice.status == "ONLINE")).scalar() or 0
    vehicle_entries = db.execute(select(func.count()).select_from(VehicleRecord)).scalar() or 0
    vehicle_exits = db.execute(select(func.count()).select_from(VehicleRecord).where(VehicleRecord.status == "EXITED")).scalar() or 0
    connectivity_success = db.execute(select(func.count()).select_from(ConnectivityTest).where(ConnectivityTest.test_status == "SUCCESS")).scalar() or 0
    connectivity_failure = db.execute(select(func.count()).select_from(ConnectivityTest).where(ConnectivityTest.test_status == "FAILURE")).scalar() or 0
    avg_latency = db.execute(
        select(func.avg(ConnectivityTest.latency_ms))
        .where(ConnectivityTest.test_status == "SUCCESS")
    ).scalar() or 0

    return {
        "total_capacity": total_capacity,
        "available_slots": available_slots,
        "occupied_slots": occupied_slots,
        "offline_slots": offline_slots,
        "occupancy_percentage": round((occupied_slots / total_capacity) * 100, 2) if total_capacity else 0.0,
        "active_devices": active_devices,
        "vehicle_entries": vehicle_entries,
        "vehicle_exits": vehicle_exits,
        "connectivity_success": connectivity_success,
        "connectivity_failure": connectivity_failure,
        "avg_latency_ms": round(float(avg_latency), 2) if avg_latency else 0.0,
    }


@app.get("/")
def root() -> dict:
    return {"message": "SMART PARK backend is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
