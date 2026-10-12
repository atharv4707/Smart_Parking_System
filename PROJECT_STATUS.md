# Project Status

## Current state

The React dashboard and FastAPI/SQLite backend are implemented as a local academic demo. The dashboard supports parking zones and slot interactions, vehicle entry/exit, simulated sensor connectivity, network-device inspection, event logs, and database-backed analytics. Demo data is seeded on first run and can be restored with **Reset demo**.

This project does not connect to real parking sensors or railway infrastructure. Ping and Traceroute are simulated API operations, not operating-system network tests.

## Verification

The frontend Vitest suite and production build passed in the current workspace. Backend tests are run from the project root with `PYTHONPATH=.`; see [README.md](./README.md) for the Windows commands. The latest backend regression coverage includes invalid plate input, unavailable bays, exits, offline occupied sensors, and latency statistics.

## Remaining before any live deployment

- Authentication, authorization, production hosting, and operational monitoring
- Real sensor/device integration and security review
- A production database and deployment-specific backup/migration strategy

These are outside the academic demonstration scope.

## Last updated

2026-10-12
