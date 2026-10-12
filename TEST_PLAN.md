# SMART PARK Test Plan

## Automated checks

From the project root in PowerShell:

```powershell
$env:PYTHONPATH = "."
python -m pytest backend\tests -q
cd frontend
npm run test:run
npm run build
```

Backend tests cover seeded slot/device state, valid and invalid plate input, duplicate active-session and slot-assignment prevention, unavailable or offline bays, slot and vehicle exits, offline occupied sensors, simulated connectivity, event filtering/clearing, analytics, and reset behavior. Frontend tests cover dashboard rendering and bay-specific vehicle entry.

## Manual demo checks

1. Start API and Vite using the instructions in [README.md](./README.md).
2. Confirm seeded parking/network state is displayed.
3. Enter a vehicle, verify assignment and event history, then exit it.
4. Disconnect and reconnect a sensor; confirm status and availability update.
5. Run simulated Ping/Traceroute and inspect the generated event.
6. Reset the demo and verify the seeded state returns.

Connectivity outcomes are simulated; these checks do not test live network traffic or hardware.
