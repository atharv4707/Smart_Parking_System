import { useCallback, useEffect, useMemo, useState } from 'react'

type View = 'parking' | 'network' | 'log'
type ZoneId = 'A' | 'B' | 'C'
type ZoneFilter = 'any' | ZoneId
type LogFilter = 'all' | 'vehicles' | 'network'
type Slot = {
  id: number
  slot_id: string
  status: string
  sensor_status: string
  sensor_ip: string
  last_update: string
  last_event: string
}
type Vehicle = {
  id: number
  registration_number: string
  slot_id: string
  entry_time: string
  exit_time: string | null
  status: string
}
type Device = {
  id: number
  name: string
  device_type: string
  ip: string
  status: string
  last_seen: string
  associated_events: string
}
type EventLog = {
  id: number
  category: string
  source: string
  destination: string | null
  event_type: string
  details: string
  created_at: string
}
type Analytics = {
  total_capacity: number
  available_slots: number
  occupied_slots: number
  offline_slots: number
  occupancy_percentage: number
  active_devices: number
  vehicle_entries: number
  vehicle_exits: number
  connectivity_success: number
  connectivity_failure: number
  avg_latency_ms: number
}
type ConnectivityResult = {
  source_ip: string
  destination_ip: string
  test_status: string
  latency_ms: number
  timestamp: string
  failure_reason: string | null
}
type Zone = {
  id: ZoneId
  name: string
  label: string
  start: number
  end: number
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const ZONES: Zone[] = [
  { id: 'A', name: 'Zone A', label: 'Parking bays 1–4', start: 1, end: 4 },
  { id: 'B', name: 'Zone B', label: 'Parking bays 5–8', start: 5, end: 8 },
  { id: 'C', name: 'Zone C', label: 'Parking bays 9–10', start: 9, end: 10 },
]

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json() as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // Keep the HTTP status message when the server doesn't return JSON.
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

function slotZone(slotId: string): ZoneId {
  const number = Number(slotId.slice(1))
  if (number <= 4) return 'A'
  if (number <= 8) return 'B'
  return 'C'
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function formatPlate(value: string) {
  return value.trim().toUpperCase().replace(/[^A-Z0-9]/g, '')
}

function displayPlate(value: string) {
  const match = value.replace(/[^A-Z0-9]/gi, '').match(/^([A-Z]{2}\d{2})([A-Z]{1,3})(\d{4})$/i)
  return match ? [`${match[1]} ${match[2]}`, match[3]] : [value]
}

function randomPlate() {
  const letters = 'ABCDEFGHJKLMNPRSTUVWXYZ'
  const randomLetters = Array.from({ length: 2 }, () => letters[Math.floor(Math.random() * letters.length)]).join('')
  return `MH12${randomLetters}${Math.floor(1000 + Math.random() * 9000)}`
}

function App() {
  const [activeView, setActiveView] = useState<View>('parking')
  const [zoneFilter, setZoneFilter] = useState<ZoneFilter>('any')
  const [logFilter, setLogFilter] = useState<LogFilter>('all')
  const [autoTraffic, setAutoTraffic] = useState(false)
  const [plate, setPlate] = useState('')
  const [slots, setSlots] = useState<Slot[]>([])
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [events, setEvents] = useState<EventLog[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null)
  const [connectivityResult, setConnectivityResult] = useState<ConnectivityResult | null>(null)
  const [consoleLines, setConsoleLines] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const refresh = useCallback(async () => {
    const [slotData, vehicleData, deviceData, eventData, analyticsData] = await Promise.all([
      api<Slot[]>('/api/parking/slots'),
      api<Vehicle[]>('/api/vehicles/active'),
      api<Device[]>('/api/network/devices'),
      api<EventLog[]>('/api/network/logs'),
      api<Analytics>('/api/analytics/summary'),
    ])
    setSlots(slotData)
    setVehicles(vehicleData)
    setDevices(deviceData)
    setEvents(eventData)
    setAnalytics(analyticsData)
    setSelectedDeviceId((current) => current ?? deviceData[0]?.id ?? null)
  }, [])

  useEffect(() => {
    let cancelled = false
    void refresh()
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Unable to load parking data')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [refresh])

  const runAction = useCallback(async (action: () => Promise<string>) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const message = await action()
      await refresh()
      setNotice(message)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The requested action failed')
    } finally {
      setBusy(false)
    }
  }, [refresh])

  const activeVehicleBySlot = useMemo(
    () => new Map(vehicles.map((vehicle) => [vehicle.slot_id, vehicle])),
    [vehicles],
  )
  const selectedDevice = devices.find((device) => device.id === selectedDeviceId) ?? devices[0]
  const filteredEvents = events.filter((event) => {
    if (logFilter === 'all') return true
    return logFilter === 'vehicles' ? event.category.toLowerCase() === 'parking' : event.category.toLowerCase() === 'network'
  })

  const enterVehicle = useCallback(async (slotId?: string) => {
    const registration = formatPlate(plate) || randomPlate()
    const targetSlot = slotId ?? slots.find((slot) =>
      slot.status === 'AVAILABLE' &&
      slot.sensor_status === 'ONLINE' &&
      (zoneFilter === 'any' || slotZone(slot.slot_id) === zoneFilter),
    )?.slot_id
    if (!targetSlot) {
      setError(`No available bays in ${zoneFilter === 'any' ? 'the parking area' : `Zone ${zoneFilter}`}.`)
      return
    }
    await runAction(async () => {
      const result = await api<{ details?: string }>('/api/vehicles/entry', {
        method: 'POST',
        body: JSON.stringify({ registration_number: registration, slot_id: targetSlot }),
      })
      setPlate('')
      return result.details ?? `Vehicle ${registration} entered`
    })
  }, [plate, runAction, slots, zoneFilter])

  const exitVehicle = useCallback(async (slotId: string) => {
    await runAction(async () => {
      const result = await api<{ details?: string }>(`/api/parking/slots/${encodeURIComponent(slotId)}/exit`, { method: 'POST' })
      return result.details ?? `Bay ${slotId} released`
    })
  }, [runAction])

  const handleBayClick = (slot: Slot) => {
    if (busy || slot.sensor_status !== 'ONLINE') return
    if (slot.status === 'OCCUPIED') void exitVehicle(slot.slot_id)
    else if (slot.status === 'AVAILABLE') void enterVehicle(slot.slot_id)
  }

  const toggleSensor = (slot: Slot) => {
    const action = slot.sensor_status === 'ONLINE' ? 'disconnect' : 'reconnect'
    void runAction(async () => {
      const result = await api<{ details?: string }>(`/api/sensors/${encodeURIComponent(slot.slot_id)}/${action}`, { method: 'POST' })
      return result.details ?? `Sensor ${slot.slot_id} ${action}ed`
    })
  }

  const runConnectivity = (kind: 'Ping' | 'Traceroute') => {
    if (!selectedDevice) return
    void runAction(async () => {
      const result = await api<ConnectivityResult>('/api/network/connectivity-test', {
        method: 'POST',
        body: JSON.stringify({
          source: 'Administrator Client',
          destination: selectedDevice.name,
          test_type: kind.toLowerCase(),
        }),
      })
      setConnectivityResult(result)
      const outcome = result.test_status === 'SUCCESS'
        ? `${kind} to ${result.destination_ip} succeeded (${result.latency_ms} ms)`
        : `${kind} failed: ${result.failure_reason ?? 'No response'}`
      setConsoleLines((lines) => [outcome, ...lines].slice(0, 10))
      return outcome
    })
  }

  const resetDemo = () => {
    if (!window.confirm('Reset the demo data? This will clear the current parking and event state.')) return
    void runAction(async () => {
      const result = await api<{ message: string }>('/api/demo/reset', { method: 'POST' })
      setConsoleLines([])
      setConnectivityResult(null)
      return result.message
    })
  }

  const clearEvents = () => {
    if (!window.confirm('Clear the event log?')) return
    void runAction(async () => {
      const category = logFilter === 'vehicles' ? 'parking' : logFilter === 'network' ? 'network' : 'all'
      const result = await api<{ message: string }>(`/api/network/logs?category=${category}`, { method: 'DELETE' })
      return result.message
    })
  }

  useEffect(() => {
    if (!autoTraffic || slots.length === 0 || busy) return
    const interval = window.setInterval(() => {
      const active = vehicles[Math.floor(Math.random() * vehicles.length)]
      if (active && Math.random() < 0.5) void exitVehicle(active.slot_id)
      else {
        const available = slots.filter((slot) =>
          slot.status === 'AVAILABLE' &&
          slot.sensor_status === 'ONLINE' &&
          (zoneFilter === 'any' || slotZone(slot.slot_id) === zoneFilter),
        )
        if (available.length) void enterVehicle(available[Math.floor(Math.random() * available.length)].slot_id)
      }
    }, 8000)
    return () => window.clearInterval(interval)
  }, [autoTraffic, busy, enterVehicle, exitVehicle, slots, vehicles, zoneFilter])

  const total = analytics?.total_capacity ?? slots.length
  const free = slots.filter((slot) => slot.status === 'AVAILABLE' && slot.sensor_status === 'ONLINE').length
  const occupied = slots.filter((slot) => slot.status === 'OCCUPIED').length
  const offline = slots.filter((slot) => slot.sensor_status !== 'ONLINE').length
  const selectedDeviceSlot = selectedDevice
    ? slots.find((slot) => slot.sensor_ip === selectedDevice.ip)
    : undefined
  const selectedDeviceStatus = selectedDeviceSlot?.sensor_status ?? selectedDevice?.status
  const renderDeviceNode = (device: Device) => {
    const isSensor = device.device_type.toLowerCase() === 'sensor'
    const slot = isSensor ? slots.find((item) => item.sensor_ip === device.ip) : undefined
    const deviceStatus = slot?.sensor_status ?? device.status
    const sensorNumber = device.name.match(/\d+$/)?.[0]
    const label = isSensor && sensorNumber ? `P${sensorNumber.padStart(2, '0')}` : device.name
    return (
      <button
        key={device.id}
        type="button"
        className={`net-device ${isSensor ? 'sensor-node' : ''} ${deviceStatus.toLowerCase()}`}
        onClick={() => setSelectedDeviceId(device.id)}
        aria-pressed={selectedDevice?.id === device.id}
        title={`${device.name} — ${device.ip} — ${deviceStatus}`}
      >
        <span className="status-dot" />
        <span>{label}</span>
        <small>{device.ip}</small>
      </button>
    )
  }

  return (
    <div className="page-shell">
      <header className="board">
        <div className="wrap bar">
          <div className="brand">
            <div className="mark" aria-hidden="true">P</div>
            <div>
              <h1>Pune Railway Station parking</h1>
              <p>Smart Parking Network prototype</p>
            </div>
          </div>
          <button type="button" className="ghost" onClick={resetDemo} disabled={busy}>Reset demo</button>
        </div>
        <nav className="wrap tabs" aria-label="Primary navigation">
          {(['parking', 'network', 'log'] as const).map((view) => (
            <button key={view} type="button" className="tab" aria-selected={activeView === view} onClick={() => setActiveView(view)}>
              {view === 'parking' ? 'Parking' : view === 'network' ? 'Network' : 'Events'}
              {view === 'network' && offline > 0 && <span className="badge">{offline}</span>}
            </button>
          ))}
        </nav>
      </header>

      <main className="wrap">
        {(error || notice) && (
          <div className={`feedback ${error ? 'error' : 'success'}`} role={error ? 'alert' : 'status'}>
            <span>{error || notice}</span>
            <button type="button" aria-label="Dismiss message" onClick={() => { setError(''); setNotice('') }}>×</button>
          </div>
        )}

        {activeView === 'parking' && (
          <section aria-label="Parking">
            <div className="boards" aria-label="Parking availability overview">
              <div className={`disp main ${free === 0 && total > 0 ? 'full' : ''}`}>
                <span className="lbl">Free bays, whole lot</span>
                <span className="num">{loading ? '—' : free}</span>
                <span className="sub">{occupied} taken, {offline} no signal, {total} total</span>
              </div>
              {ZONES.map((zone) => {
                const zoneSlots = slots.filter((slot) => {
                  const number = Number(slot.slot_id.slice(1))
                  return number >= zone.start && number <= zone.end
                })
                const zoneFree = zoneSlots.filter((slot) => slot.status === 'AVAILABLE').length
                return (
                  <button
                    type="button"
                    key={zone.id}
                    className={`disp zone-disp ${zoneFree === 0 && zoneSlots.length > 0 ? 'full' : ''}`}
                    aria-pressed={zoneFilter === zone.id}
                    onClick={() => setZoneFilter(zoneFilter === zone.id ? 'any' : zone.id)}
                  >
                    <span className="lbl">{zone.name}</span>
                    <span className="num">{loading ? '—' : zoneFree}</span>
                    <span className="sub">{zone.label}</span>
                  </button>
                )
              })}
            </div>

            {offline > 0 && (
              <div className="banner">
                <span><strong>{offline} {offline === 1 ? 'bay has' : 'bays have'} no signal.</strong> Offline sensor bays are excluded from the available count.</span>
                <button type="button" className="link" onClick={() => setActiveView('network')}>Open network tools</button>
              </div>
            )}

            <div className="split">
              <div className="lot">
                {loading ? <div className="card loading">Loading live parking data…</div> : ZONES.map((zone) => {
                  const zoneSlots = slots.filter((slot) => {
                    const number = Number(slot.slot_id.slice(1))
                    return number >= zone.start && number <= zone.end
                  })
                  if (zoneFilter !== 'any' && zoneFilter !== zone.id) return null
                  return (
                    <section key={zone.id} className="zone">
                      <header>
                        <span className="zid">{zone.id}</span>
                        <div><h3>{zone.name}</h3><p>{zone.label}</p></div>
                        <span className="zfree">{zoneSlots.filter((slot) => slot.status === 'AVAILABLE').length} free</span>
                      </header>
                      <div className="bays">
                        {zoneSlots.map((slot) => {
                          const vehicle = activeVehicleBySlot.get(slot.slot_id)
                          const state = slot.sensor_status !== 'ONLINE' || slot.status === 'SENSOR_OFFLINE'
                            ? 'off'
                            : slot.status === 'OCCUPIED' ? 'busy' : 'free'
                          const label = state === 'busy'
                            ? `Bay ${slot.slot_id}, taken${vehicle ? ` by ${vehicle.registration_number}` : ''}. Release this bay`
                            : state === 'off' ? `Bay ${slot.slot_id}, sensor offline. Reconnect it in Network.` : `Bay ${slot.slot_id}, free. Park a vehicle here`
                          return (
                            <button
                              key={slot.slot_id}
                              type="button"
                              className={`bay ${state}`}
                              aria-label={label}
                              title={`${slot.slot_id}: ${slot.last_event}`}
                              disabled={busy || state === 'off'}
                              onClick={() => handleBayClick(slot)}
                            >
                              <span className="bid">{slot.slot_id}</span>
                              {state === 'busy' ? (
                                <>
                                  <svg className="car" viewBox="0 0 24 40" aria-hidden="true">
                                    <rect x="3" y="2" width="18" height="36" rx="7" fill="currentColor" />
                                    <rect x="6" y="9" width="12" height="7" rx="2" fill="#27323E" />
                                    <rect x="6" y="25" width="12" height="5" rx="2" fill="#27323E" />
                                  </svg>
                                  <span className="plate">
                                    {displayPlate(vehicle?.registration_number ?? 'Occupied').map((part) => <span key={part}>{part}</span>)}
                                  </span>
                                </>
                              ) : <span className="state">{state === 'off' ? 'No signal' : 'Free'}</span>}
                            </button>
                          )
                        })}
                      </div>
                    </section>
                  )
                })}
              </div>

              <aside className="side">
                <div className="card">
                  <h2>Simulate a vehicle</h2>
                  <fieldset className="field">
                    <legend>Zone</legend>
                    <div className="seg" aria-label="Zone selector">
                      {(['any', 'A', 'B', 'C'] as const).map((zone) => (
                        <button key={zone} type="button" aria-pressed={zoneFilter === zone} onClick={() => setZoneFilter(zone)}>
                          {zone === 'any' ? 'Any' : zone}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                  <label className="field">
                    <span>Number plate</span>
                    <input type="text" value={plate} onChange={(event) => setPlate(event.target.value)} placeholder="Leave blank for a random plate" maxLength={14} autoComplete="off" />
                  </label>
                  <div className="btns">
                    <button type="button" className="btn primary" onClick={() => void enterVehicle()} disabled={busy}>Vehicle enters</button>
                    <button type="button" className="btn" onClick={() => {
                      const first = vehicles[0]?.slot_id ?? slots.find((slot) => slot.status === 'OCCUPIED')?.slot_id
                      if (first) void exitVehicle(first)
                      else setError('There are no active vehicles to exit.')
                    }} disabled={busy || !slots.some((slot) => slot.status === 'OCCUPIED')}>Vehicle exits</button>
                  </div>
                  <p className="hint" style={{ marginTop: 10 }}>You can also select a bay on the map: a free bay parks a vehicle, a taken bay releases it.</p>
                  <div className="sw">
                    <div><b>Auto traffic</b><span className="hint">Vehicles arrive and leave on their own</span></div>
                    <button type="button" className="toggle" aria-pressed={autoTraffic} onClick={() => setAutoTraffic((value) => !value)} aria-label="Auto traffic" />
                  </div>
                </div>
                <div className="card">
                  <h2>Latest events</h2>
                  <ol className="recent">
                    {events.slice(0, 6).map((event) => (
                      <li key={event.id}><time>{formatTime(event.created_at)}</time><span>{event.details}</span></li>
                    ))}
                    {!events.length && <li className="empty">No events recorded yet.</li>}
                  </ol>
                </div>
              </aside>
            </div>
          </section>
        )}

        {activeView === 'network' && (
          <section aria-label="Network" className="network-view">
            <div className="net-top">
              <div className="card">
                <h2>Network topology</h2>
                <div className="topology-graph">
                  <div className="topology-map" aria-label="Network device layers">
                    <div className="topology-row">
                      {devices.filter((device) => ['server', 'client'].includes(device.device_type.toLowerCase())).map(renderDeviceNode)}
                    </div>
                    <div className="topology-connector" aria-hidden="true">↓</div>
                    <div className="topology-row">
                      {devices.filter((device) => device.device_type.toLowerCase() === 'router').map(renderDeviceNode)}
                    </div>
                    <div className="topology-connector" aria-hidden="true">↓</div>
                    <div className="topology-row">
                      {devices.filter((device) => ['gateway', 'switch'].includes(device.device_type.toLowerCase())).map(renderDeviceNode)}
                    </div>
                    <div className="topology-connector" aria-hidden="true">↓</div>
                    <div className="topology-row sensors">
                      {devices.filter((device) => device.device_type.toLowerCase() === 'sensor').map(renderDeviceNode)}
                    </div>
                  </div>
                </div>
                <div className="legend">
                  <span><i style={{ background: 'var(--free)' }} />Online</span>
                  <span><i style={{ background: 'var(--busy)' }} />Offline</span>
                  <span><i style={{ background: 'var(--off)' }} />Unreachable</span>
                </div>
                <p className="hint" style={{ marginTop: 8 }}>Select a device to inspect it. Sensor devices match the bays shown in Parking.</p>
              </div>
              <div className="card device-panel">
                <h2>Selected device</h2>
                {selectedDevice ? (
                  <div className="device-panel-body">
                    <div className="device-kind">{selectedDevice.device_type}</div>
                    <h3>{selectedDevice.name}</h3>
                    <p>{selectedDevice.associated_events}</p>
                    <dl>
                      <div><dt>IP</dt><dd>{selectedDevice.ip}</dd></div>
                      <div><dt>Status</dt><dd>{selectedDeviceStatus}</dd></div>
                      <div><dt>Last seen</dt><dd>{formatTime(selectedDevice.last_seen)}</dd></div>
                    </dl>
                    {selectedDevice.device_type.toLowerCase() === 'sensor' && (() => {
                      const sensorSlot = slots.find((slot) => slot.sensor_ip === selectedDevice.ip)
                      return sensorSlot ? (
                        <button type="button" className={`btn ${sensorSlot.sensor_status === 'ONLINE' ? 'danger' : 'primary'}`} onClick={() => toggleSensor(sensorSlot)} disabled={busy}>
                          {sensorSlot.sensor_status === 'ONLINE' ? 'Disconnect sensor' : 'Reconnect sensor'}
                        </button>
                      ) : null
                    })()}
                  </div>
                ) : <p className="hint">Loading device inventory…</p>}
              </div>
            </div>

            <div className="net-bot">
              <div className="card">
                <h2>Troubleshooting console</h2>
                <div className="cmdbar">
                  <select aria-label="Target device" value={selectedDeviceId ?? ''} onChange={(event) => setSelectedDeviceId(Number(event.target.value))}>
                    {devices.map((device) => <option key={device.id} value={device.id}>{device.name}</option>)}
                  </select>
                  <button type="button" className="btn" onClick={() => runConnectivity('Ping')} disabled={!selectedDevice || busy}>Ping</button>
                  <button type="button" className="btn" onClick={() => runConnectivity('Traceroute')} disabled={!selectedDevice || busy}>Traceroute</button>
                </div>
                <div className="term" role="log" aria-live="polite">
                  {!consoleLines.length && <div>Select a device and run Ping or Traceroute.</div>}
                  {connectivityResult && <div>From {connectivityResult.source_ip} to {connectivityResult.destination_ip}</div>}
                  {consoleLines.map((line, index) => <div key={`${index}-${line}`} className={`term-line ${line.includes('succeeded') ? 'ok' : 'bad'}`}>{line}</div>)}
                </div>
              </div>
              <div className="card">
                <h2>When a sensor stops reporting</h2>
                <ol className="steps">
                  <li>Check the link light and cable on the switch port.</li>
                  <li>Confirm the IP address, subnet mask and default gateway.</li>
                  <li>Ping the gateway first, then the sensor.</li>
                  <li>Compare the VLAN and port settings on the switch.</li>
                  <li>Look in the event log for the sensor's last report.</li>
                </ol>
              </div>
            </div>

            <div className="card">
              <h2>Addressing plan</h2>
              <div className="tablewrap">
                <table>
                  <thead><tr><th>Device</th><th>Type</th><th>IP</th><th>Status</th></tr></thead>
                  <tbody>{devices.map((device) => {
                    const slot = slots.find((item) => item.sensor_ip === device.ip)
                    const status = slot?.sensor_status ?? device.status
                    return <tr key={device.id}><td>{device.name}</td><td>{device.device_type}</td><td>{device.ip}</td><td>{status}</td></tr>
                  })}</tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {activeView === 'log' && (
          <section aria-label="Event log">
            <div className="logbar">
              <div className="chips">
                {(['all', 'vehicles', 'network'] as const).map((filter) => (
                  <button key={filter} type="button" className="chip" aria-pressed={logFilter === filter} onClick={() => setLogFilter(filter)}>
                    {filter === 'all' ? 'All' : filter === 'vehicles' ? 'Vehicles' : 'Network'}
                  </button>
                ))}
              </div>
              <span className="sp" />
              <span className="hint">{filteredEvents.length} entries</span>
              <button type="button" className="btn" onClick={clearEvents} disabled={busy || filteredEvents.length === 0}>Clear log</button>
            </div>
            <div className="card table-card">
              <div className="tablewrap">
                <table>
                  <thead><tr><th>Time</th><th>Category</th><th>Source</th><th>Destination</th><th>Event</th><th>Details</th></tr></thead>
                  <tbody>{filteredEvents.map((event) => (
                    <tr key={event.id}>
                      <td>{formatTime(event.created_at)}</td><td>{event.category}</td><td>{event.source}</td>
                      <td>{event.destination ?? '—'}</td><td>{event.event_type}</td><td>{event.details}</td>
                    </tr>
                  ))}</tbody>
                </table>
                {!filteredEvents.length && <p className="empty table-empty">No events match this filter.</p>}
              </div>
            </div>
            {analytics && (
              <div className="card analytics-card">
                <h2>Demo analytics</h2>
                <div className="analytics-grid">
                  <div><strong>{analytics.occupancy_percentage}%</strong><span>Occupancy</span></div>
                  <div><strong>{analytics.active_devices}</strong><span>Online devices</span></div>
                  <div><strong>{analytics.connectivity_success}</strong><span>Successful tests</span></div>
                  <div><strong>{analytics.connectivity_failure}</strong><span>Failed tests</span></div>
                </div>
              </div>
            )}
          </section>
        )}
      </main>
      <footer className="wrap foot">
        <span>Prototype for demonstration. Not connected to railway station infrastructure.</span>
        <button className="link" type="button" onClick={resetDemo} disabled={busy}>Reset demo</button>
      </footer>
    </div>
  )
}

export default App
