# SMART PARK Architecture

## Overview

SMART PARK is a local academic prototype that combines parking operations with a simulated network-monitoring view. Parking sensors are modeled as devices with private example IP addresses. The system does not control real hardware or connect to station infrastructure.

## Components

### Frontend

- React + TypeScript application served by Vite
- Fetches backend JSON endpoints and refreshes data after dashboard actions
- Uses CSS for the responsive control-room dashboard and parking/network views

### Backend

- FastAPI REST API with Pydantic request/response validation
- SQLAlchemy models and session-managed database operations
- SQLite persistence; the default file is `smart_park.db` in the project root
- Seeded demo data initialized on first start and restored by the reset endpoint

## Persistent entities

- `parking_slots`: current slot state, sensor health, IP address, and most recent event
- `vehicle_records`: vehicle registration, assigned slot, entry/exit timestamps, and active/exited state
- `network_devices`: simulated devices, addressing, and health state
- `system_events`: parking and network event history
- `connectivity_tests`: simulated Ping/Traceroute outcomes and example latency

## Data flow

1. The browser requests parking slots, active vehicles, network devices, event history, and analytics from the API.
2. FastAPI validates request data and reads or updates the SQLite records.
3. Parking actions update slot and vehicle state and add a corresponding event in the same database session.
4. Sensor actions update both the slot sensor state and its matching network-device state.
5. The dashboard refreshes its data after an action so the visible counters and event history reflect persisted state.

## Network simulation

The topology and `192.168.10.x` addresses are illustrative seeded data. Ping and Traceroute are simulated by checking device availability and writing a result with an example latency. No packets are sent and no live routes or latency are measured.

## Run instructions

See [README.md](./README.md) for Windows startup and test commands. See [VIVA_GUIDE.md](./VIVA_GUIDE.md) for demonstration flow and Computer Networks concepts.
