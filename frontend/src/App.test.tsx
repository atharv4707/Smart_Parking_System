import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

const slots = [
  { id: 1, slot_id: 'P01', status: 'AVAILABLE', sensor_status: 'ONLINE', sensor_ip: '192.168.10.101', last_update: '2026-10-12T08:00:00', last_event: 'Awaiting vehicle' },
  { id: 2, slot_id: 'P02', status: 'OCCUPIED', sensor_status: 'ONLINE', sensor_ip: '192.168.10.102', last_update: '2026-10-12T08:05:00', last_event: 'Vehicle entered' },
  { id: 7, slot_id: 'P07', status: 'SENSOR_OFFLINE', sensor_status: 'OFFLINE', sensor_ip: '192.168.10.107', last_update: '2026-10-12T08:29:00', last_event: 'Sensor disconnect' },
]

const devices = [
  { id: 1, name: 'Administrator Client', device_type: 'Client', ip: '192.168.10.100', status: 'ONLINE', last_seen: '2026-10-12T08:06:00', associated_events: 'Dashboard online' },
  { id: 2, name: 'Parking Sensor 7', device_type: 'Sensor', ip: '192.168.10.107', status: 'OFFLINE', last_seen: '2026-10-12T08:29:00', associated_events: 'Sensor disconnected' },
]

const analytics = {
  total_capacity: 3,
  available_slots: 1,
  occupied_slots: 1,
  offline_slots: 1,
  occupancy_percentage: 33.33,
  active_devices: 1,
  vehicle_entries: 1,
  vehicle_exits: 0,
  connectivity_success: 0,
  connectivity_failure: 0,
  avg_latency_ms: 0,
}

function mockResponse(body: unknown, ok = true) {
  return Promise.resolve({ ok, json: async () => body }) as Promise<Response>
}

describe('SMART PARK app', () => {
  it('renders backend parking state and the provided station design', async () => {
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/parking/slots')) return mockResponse(slots)
      if (url.includes('/api/vehicles/active')) return mockResponse([])
      if (url.includes('/api/network/devices')) return mockResponse(devices)
      if (url.includes('/api/network/logs')) return mockResponse([])
      if (url.includes('/api/analytics/summary')) return mockResponse(analytics)
      return mockResponse({})
    }) as typeof fetch

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Pune Railway Station parking' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /Bay P01, free/ })).toBeInTheDocument()
    expect(screen.getByText('Free bays, whole lot')).toBeInTheDocument()
    expect(screen.getByText('1 taken, 1 no signal, 3 total')).toBeInTheDocument()
  })

  it('posts a bay-specific vehicle entry to the backend', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/api/parking/slots')) return mockResponse(slots)
      if (url.includes('/api/vehicles/active')) return mockResponse([])
      if (url.includes('/api/network/devices')) return mockResponse(devices)
      if (url.includes('/api/network/logs')) return mockResponse([])
      if (url.includes('/api/analytics/summary')) return mockResponse(analytics)
      if (url.includes('/api/vehicles/entry')) {
        expect(init?.method).toBe('POST')
        expect(JSON.parse(String(init?.body))).toEqual({ registration_number: 'MH12AB3456', slot_id: 'P01' })
        return mockResponse({ success: true, details: 'Assigned slot P01' })
      }
      return mockResponse({})
    })
    globalThis.fetch = fetchMock as typeof fetch

    render(<App />)
    fireEvent.change(screen.getByLabelText('Number plate'), { target: { value: 'MH12 AB 3456' } })
    fireEvent.click(await screen.findByRole('button', { name: /Bay P01, free/ }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/vehicles/entry'),
      expect.objectContaining({ method: 'POST' }),
    ))
    expect(await screen.findByRole('status')).toHaveTextContent('Assigned slot P01')
  })
})
