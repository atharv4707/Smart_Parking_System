from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'smart_park.db'}")
DEBUG = os.getenv("APP_ENV", "development") == "development"
APP_TITLE = os.getenv("APP_TITLE", "SMART PARK")


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_cors_origins(value: str | None) -> list[str]:
    if value is None:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
