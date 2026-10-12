# SMART PARK

SMART PARK is an academic demonstration of parking operations and a small, simulated device network. It is **not connected to Pune Railway Station or real sensors**, and its Ping/Traceroute results are simulated by the API.

## Technologies

- Frontend: React, TypeScript, Vite, CSS
- Backend: FastAPI, Pydantic, SQLAlchemy
- Storage: SQLite (`smart_park.db` by default)
- Tests: Vitest, React Testing Library, pytest

## Run on Windows

Requirements: Python 3.10+ and Node.js/npm. Open two PowerShell terminals in the project root.

### 1. Start the API

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
$env:PYTHONPATH = "."
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again. The API is at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

### 2. Start the dashboard

```powershell
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). Stop either server with `Ctrl+C`. The SQLite file remains on disk between restarts; use **Reset demo** in the dashboard to restore the seeded demonstration data.

## Deploy on Render (college demo)

The repository includes [render.yaml](./render.yaml) to provision a FastAPI service, a static dashboard, and a PostgreSQL database. From the Render dashboard, create a **Blueprint** from this repository and deploy it. After Render creates the services, configure these two service environment variables:

1. In `smart-park-api`, set `CORS_ORIGINS` to the exact dashboard origin, for example `https://smart-park-dashboard.onrender.com` (no trailing slash).
2. In `smart-park-dashboard`, set `VITE_API_BASE_URL` to the API service's public URL, for example `https://smart-park-api.onrender.com` (no trailing slash), then trigger a new deploy so Vite rebuilds with that URL.

The API health check is available at `/api/health`; interactive API documentation is at `/docs`. The backend uses the provisioned PostgreSQL database in deployment and continues to use local SQLite by default. Render's free PostgreSQL plan is intended for evaluation and may have plan-specific expiration or availability limits; check the current Render plan terms before relying on it. This remains a demonstration application: sensor and connectivity behavior are simulated, and the app does not include authentication or authorization. Do not use it for real parking operations or store sensitive personal data.

## Demo workflows

- Review the parking bays, zones, and current sensor state.
- Enter a vehicle with an optional plate, then release a bay to record its exit.
- Active vehicle sessions and occupied bays are protected by database-level uniqueness constraints, including concurrent entry attempts.
- In Network, inspect device IPs and simulated status; disconnect/reconnect sensor devices and run simulated Ping/Traceroute checks.
- Review filtered events and analytics. The counters are derived from database records.
- Reset the demo to restore seed data.

## Validation

Run from the project root:

```powershell
$env:PYTHONPATH = "."
python -m pytest backend\tests -q
cd frontend
npm run test:run
npm run build
```

See [VIVA_GUIDE.md](./VIVA_GUIDE.md) for the short presentation walkthrough, concepts, and limitations.
