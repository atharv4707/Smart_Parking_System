# SMART PARK Viva Guide

## Project summary

SMART PARK demonstrates how a parking dashboard could combine bay occupancy with the health of networked sensors. It is a local academic prototype for Pune Railway Station as a scenario only. It is not connected to that station, actual IoT hardware, or Cisco Packet Tracer.

## Architecture and technologies

- **React + TypeScript + Vite:** renders the browser dashboard and calls the JSON API.
- **FastAPI + Pydantic:** exposes validated REST endpoints for slots, vehicles, sensors, network devices, events, and summary metrics.
- **SQLAlchemy + SQLite:** stores parking state, vehicle history, simulated connectivity tests, and event history. The default database file is `smart_park.db` in the project root.
- **Vitest / React Testing Library / pytest:** cover frontend rendering and core backend API workflows.

The frontend requests API data when it loads and refreshes state after user actions. The backend updates related slot, vehicle, device, and event records in SQLite, so the demonstration state survives an application restart. **Reset demo** intentionally recreates the seeded state.

## Computer Networks concepts shown

- **IP addressing:** the device inventory uses a private `192.168.10.x` example address plan.
- **Network topology:** the UI groups server/client, router, gateway/switch, and sensor devices into logical layers.
- **Gateway and switch roles:** the simulated IoT gateway and network switch illustrate how sensors may connect to an application network.
- **Availability and monitoring:** online/offline sensor status affects whether an available bay can be assigned and appears in the event history.
- **Ping, Traceroute, and latency:** the console records simulated success/failure and example latency. It does not send ICMP packets, discover real routes, or measure live network latency.

## Suggested demonstration (3–5 minutes)

1. Start the backend and frontend using the commands in [README.md](./README.md).
2. On Parking, explain zones, free/occupied bays, and sensor health.
3. Enter a vehicle with a sample plate, then show its assigned bay and generated event.
4. Release that bay and show the vehicle exit/event history.
5. Open Network, inspect a sensor's IP and status, disconnect it, and show its effect on bay availability.
6. Run a simulated Ping or Traceroute to show recorded success/failure and latency; reconnect the sensor.
7. Open Events to explain the database-backed history and analytics.
8. Use Reset demo if you need a clean seeded state for another run.

## Limitations to state clearly

- The station, sensors, IPs, latency, and connectivity outcomes are demonstration data.
- No real hardware control, network packet testing, authentication, or production deployment is included.
- SQLite is suitable for this local demonstration, not a multi-user production service.
- The project is an educational prototype, not an operational parking system.
