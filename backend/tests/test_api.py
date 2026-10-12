from fastapi.testclient import TestClient
import pytest
from sqlalchemy.schema import CreateIndex
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.dialects import postgresql

from backend.config import get_cors_origins, normalize_database_url
from backend.database import SessionLocal, get_db, reset_database
from backend.main import app
from backend.models import VehicleRecord

client = TestClient(app)


def test_postgres_database_urls_use_psycopg_driver():
    assert normalize_database_url("postgres://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"
    assert normalize_database_url("postgresql://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"
    assert normalize_database_url("sqlite:///demo.db") == "sqlite:///demo.db"


def test_postgres_keeps_vehicle_uniqueness_constraints_partial():
    indexes = {index.name: index for index in VehicleRecord.__table__.indexes}
    for name in ("uq_vehicle_records_active_registration", "uq_vehicle_records_active_slot"):
        statement = str(CreateIndex(indexes[name]).compile(dialect=postgresql.dialect()))
        assert "WHERE status = 'ACTIVE'" in statement


def test_cors_origins_are_configurable_without_wildcards():
    assert get_cors_origins(None) == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert get_cors_origins(" https://demo.example.com/, https://admin.example.com ") == [
        "https://demo.example.com",
        "https://admin.example.com",
    ]


def setup_function():
    reset_database()


def test_health_endpoint():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_database_errors_return_service_unavailable_without_exposing_details():
    def broken_db():
        raise OperationalError('SELECT 1', {}, RuntimeError('private database detail'))
        yield

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get('/api/parking/slots')
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json()['detail'] == 'Database operation failed. No changes were saved; please retry.'
    assert 'private database detail' not in response.text


def test_parking_slots_seeded():
    response = client.get('/api/parking/slots')
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10
    assert data[0]['slot_id'] == 'P01'


def test_vehicle_entry_success():
    response = client.post('/api/vehicles/entry', json={'registration_number': 'MH12AB3456'})
    assert response.status_code == 200
    assert response.json()['success'] is True


def test_entry_normalizes_registration_and_rejects_invalid_characters():
    response = client.post('/api/vehicles/entry', json={'registration_number': ' mh12 ab 3456 '})
    assert response.status_code == 200
    history = client.get('/api/vehicles/history').json()
    assert history[0]['registration_number'] == 'MH12AB3456'
    invalid = client.post('/api/vehicles/entry', json={'registration_number': 'MH12@AB'})
    assert invalid.status_code == 422
    duplicate = client.post('/api/vehicles/entry', json={'registration_number': 'MH12-AB-1234'})
    assert duplicate.status_code == 409


def test_vehicle_entry_into_selected_slot():
    response = client.post(
        '/api/vehicles/entry',
        json={'registration_number': 'MH12AB3456', 'slot_id': 'P01'},
    )
    assert response.status_code == 200
    assert response.json()['details'] == 'Assigned slot P01'
    assert client.get('/api/parking/slots/P01').json()['status'] == 'OCCUPIED'


def test_entry_rejects_unavailable_and_offline_slots():
    active_before = client.get('/api/vehicles/active').json()
    occupied = client.post(
        '/api/vehicles/entry',
        json={'registration_number': 'MH99ZZ9999', 'slot_id': 'P03'},
    )
    offline = client.post(
        '/api/vehicles/entry',
        json={'registration_number': 'MH99YY9999', 'slot_id': 'P07'},
    )
    assert occupied.status_code == 409
    assert offline.status_code == 409
    assert client.get('/api/vehicles/active').json() == active_before


def test_entry_rejects_blank_selected_slot_instead_of_assigning_another_bay():
    response = client.post(
        '/api/vehicles/entry',
        json={'registration_number': 'MH99ZZ9999', 'slot_id': '   '},
    )
    assert response.status_code == 422
    assert client.get('/api/vehicles/active').json()


def test_release_seeded_occupied_slot():
    response = client.post('/api/parking/slots/P03/exit')
    assert response.status_code == 200
    assert client.get('/api/parking/slots/P03').json()['status'] == 'AVAILABLE'


def test_slot_exit_rejects_unknown_or_already_available_slot():
    assert client.post('/api/parking/slots/P99/exit').status_code == 404
    assert client.post('/api/parking/slots/P01/exit').status_code == 409


def test_vehicle_exit_success():
    response = client.post('/api/vehicles/entry', json={'registration_number': 'MH12AB3456'})
    assert response.status_code == 200
    exit_response = client.post('/api/vehicles/MH12AB3456/exit')
    assert exit_response.status_code == 200
    assert exit_response.json()['success'] is True


def test_reject_occupied_slot_entry():
    first = client.post('/api/vehicles/entry', json={'registration_number': 'MH99ZZ9999'})
    assert first.status_code == 200
    second = client.post('/api/vehicles/entry', json={'registration_number': 'MH99ZZ9999'})
    assert second.status_code == 409


def test_database_prevents_duplicate_active_vehicles_and_slot_assignments():
    with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            db.add(VehicleRecord(registration_number='MH12AB1234', slot_id='P01', status='ACTIVE'))
            db.commit()
        db.rollback()

        with pytest.raises(IntegrityError):
            db.add(VehicleRecord(registration_number='MH99ZZ9999', slot_id='P03', status='ACTIVE'))
            db.commit()
        db.rollback()

    active = client.get('/api/vehicles/active').json()
    assert len(active) == 2
    assert {vehicle['slot_id'] for vehicle in active} == {'P03', 'P05'}


def test_sensor_disconnect_and_connectivity_failure():
    devices = {device['name']: device for device in client.get('/api/network/devices').json()}
    assert devices['Parking Sensor 7']['status'] == 'OFFLINE'
    disconnect = client.post('/api/sensors/P07/disconnect')
    assert disconnect.status_code == 200
    connectivity = client.post('/api/network/connectivity-test', json={'source': 'Parking Sensor 7', 'destination': 'IoT Gateway'})
    assert connectivity.status_code == 200
    assert connectivity.json()['test_status'] == 'FAILURE'
    destination_connectivity = client.post(
        '/api/network/connectivity-test',
        json={'source': 'Administrator Client', 'destination': 'Parking Sensor 7'},
    )
    assert destination_connectivity.status_code == 200
    assert destination_connectivity.json()['test_status'] == 'FAILURE'
    reconnect = client.post('/api/sensors/P07/reconnect')
    assert reconnect.status_code == 200


def test_offline_occupied_sensor_does_not_erase_vehicle_or_count_as_available():
    entry = client.post(
        '/api/vehicles/entry',
        json={'registration_number': 'MH12AB3456', 'slot_id': 'P01'},
    )
    assert entry.status_code == 200
    assert client.post('/api/sensors/P01/disconnect').status_code == 200
    slot = client.get('/api/parking/slots/P01').json()
    assert slot['status'] == 'OCCUPIED'
    assert slot['sensor_status'] == 'OFFLINE'
    metrics = client.get('/api/analytics/summary').json()
    assert metrics['occupied_slots'] == 3
    assert metrics['available_slots'] == 6
    assert metrics['offline_slots'] == 2
    exit_response = client.post('/api/vehicles/MH12AB3456/exit')
    assert exit_response.status_code == 200
    assert client.get('/api/parking/slots/P01').json()['status'] == 'SENSOR_OFFLINE'


def test_traceroute_type_is_recorded():
    response = client.post(
        '/api/network/connectivity-test',
        json={
            'source': 'Administrator Client',
            'destination': 'Router',
            'test_type': 'traceroute',
        },
    )
    assert response.status_code == 200
    event = client.get('/api/network/logs?event_type=SUCCESS').json()[0]
    assert event['details'].startswith('Traceroute succeeded')


def test_failed_connectivity_test_does_not_reduce_successful_average_latency():
    client.post('/api/sensors/P07/disconnect')
    client.post(
        '/api/network/connectivity-test',
        json={'source': 'Administrator Client', 'destination': 'Parking Sensor 7'},
    )
    client.post(
        '/api/network/connectivity-test',
        json={'source': 'Administrator Client', 'destination': 'Router'},
    )
    metrics = client.get('/api/analytics/summary').json()
    assert metrics['connectivity_success'] == 1
    assert metrics['connectivity_failure'] == 1
    assert metrics['avg_latency_ms'] == 32


def test_clear_network_events_preserves_parking_events():
    response = client.delete('/api/network/logs?category=network')
    assert response.status_code == 200
    events = client.get('/api/network/logs').json()
    assert events
    assert all(event['category'] != 'network' for event in events)


def test_reset_demo_restores_seed_data():
    client.post('/api/vehicles/entry', json={'registration_number': 'MH12AB3456'})
    response = client.post('/api/demo/reset')
    assert response.status_code == 200
    slots = {slot['slot_id']: slot for slot in client.get('/api/parking/slots').json()}
    vehicles = client.get('/api/vehicles/active').json()
    assert slots['P03']['status'] == 'OCCUPIED'
    assert slots['P05']['status'] == 'OCCUPIED'
    assert {vehicle['slot_id'] for vehicle in vehicles} == {'P03', 'P05'}
