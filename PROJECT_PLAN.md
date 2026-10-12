# SMART PARK Project Plan

## Mission
Build a production-style academic project for a smart parking network at Pune Railway Station, with a clear dashboard for parking management and network monitoring.

## Scope
- Frontend dashboard in React + TypeScript + Vite
- FastAPI backend with SQLite persistence
- Parking slot simulation with live status, sensor alarms, and event history
- Network monitor and analytics views
- Clear viva-oriented documentation and demo workflow

## Project Phases
1. Repository setup and planning docs
2. Backend API, schema, validation, and seed data
3. Frontend dashboard and interactive controls
4. Integration, polish, and test verification
5. Final documentation and demo readiness

## Acceptance criteria
- App loads with dashboard as the default landing page
- Dashboard shows capacity, occupancy, offline sensors, and active devices
- Users can view slots, search/filter, open details, and simulate device disconnect/reconnect
- Vehicle entry workflow assigns an available slot and records the event
- Backend validates slot transitions and input
- Data persists in SQLite and is returned through HTTP API endpoints
- Frontend communicates via real API calls, not mock-only success states
- Project includes docs, setup steps, and a basic validation suite

## Deliverables
- `frontend/` React app
- `backend/` FastAPI project
- docs and support files in root
- test scripts covering core functionality
