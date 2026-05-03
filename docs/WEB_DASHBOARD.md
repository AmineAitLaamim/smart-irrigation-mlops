# Web Dashboard Documentation

## Overview

The Web Dashboard is a React/Next.js application that provides a user-friendly interface for:
- **Authentication** - Login, register, session management
- **Zone Monitoring** - Real-time sensor data visualization
- **Predictions** - Model prediction display
- **Irrigation History** - Historical irrigation events
- **Zone Management** - Create and configure zones

**Location:** `services/web-dashboard/`

**Port:** 3000

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         WEB DASHBOARD (Next.js App)                           │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        Next.js Pages                                     │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │ (auth)      │  │ (dashboard)  │  │             │  │            │  │   │
│  │  │             │  │              │  │             │  │            │  │   │
│  │  │ - Login    │  │ - Dashboard │  │ - Zones     │  │ - History  │  │   │
│  │  │ - Register│  │ - Overview  │  │ - Zone [id] │  │ - Settings │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        Custom Hooks                                       │   │
│  │                                                                          │   │
│  │  useZones()          - Zone CRUD operations                              │   │
│  │  useSensorData()    - Sensor readings (moisture, temperature)          │   │
│  │  usePredictions()   - Model predictions                                │   │
│  │  useIrrigationEvents() - Irrigation event history                     │   │
│  │  useZonesOverviewChart() - Chart data for dashboard                   │   │
│  │                                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        State Management                                  │   │
│  │                                                                          │   │
│  │  authStore   - User authentication state                               │   │
│  │  uiStore     - UI state (sidebar, theme, etc)                         │   │
│  │                                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            API Layer                                          │
│                                                                                 │
│  lib/api.ts ───► API Client with:                                           │
│  - Auto token refresh                                                        │
│  - Error handling                                                           │
│  - Cookie-based auth                                                        │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        API Gateway (8080)                                     │
│                                                                                 │
│  Proxied to: user-service, irrigation-controller, model-server, etc.         │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Technology | Purpose |
|------------|----------|
| Next.js 14+ | React framework with App Router |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| Zustand | State management |
| Recharts | Data visualization |
| shadcn/ui | UI components |

---

## Page Structure

### Authentication Pages

```
/login    - User login
/register - User registration
```

### Dashboard Pages

```
/dashboard      - Overview with charts and metrics
/zones          - List all zones
/zones/[id]     - Zone detail with sensor data
/history        - Irrigation event history
/settings       - User settings
```

---

## Custom Hooks

### useZones

```typescript
const { zones, loading, createZone, updateZone, deleteZone } = useZones()
```

**Features:**
- Fetch all zones
- Create new zone
- Update existing zone
- Delete zone (owner only)

### useSensorData

```typescript
const { readings, latest, loading } = useSensorData(zoneId, hours)
```

**Features:**
- Fetch sensor readings for last N hours
- Get latest reading per sensor
- Real-time updates

### usePredictions

```typescript
const { predictions, loading } = usePredictions(zoneId, hours)
```

**Features:**
- Fetch model predictions
- Display prediction confidence

### useIrrigationEvents

```typescript
const { events, loading } = useIrrigationEvents(zoneId, limit)
```

**Features:**
- Fetch irrigation events
- Show trigger reason
- Display status (pending/completed)

### useZonesOverviewChart

```typescript
const { chartData, loading } = useZonesOverviewChart()
```

**Features:**
- Aggregated data for dashboard charts
- Zone comparison

---

## API Client

### lib/api.ts

The API client provides a wrapper around fetch with automatic token refresh:

```typescript
export const api = {
  get:    <T>(path: string) => request<T>(path),
  post:   <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: ... }),
  put:    <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: ... }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
}
```

**Features:**
- Automatic token refresh on 401
- Cookie-based authentication (httpOnly cookies)
- JSON content type
- Error handling

### Token Refresh Flow

```
Request fails with 401
        │
        ▼
POST /api/auth/refresh (uses cookie)
        │
        ├── Success ──► Retry original request
        │
        └── Failure ──► Redirect to /login
```

---

## State Management

### authStore

```typescript
interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (email, password) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<void>
}
```

### uiStore

```typescript
interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  toggleSidebar: () => void
  setTheme: (theme) => void
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | (empty string) | Backend API base URL |

---

## Configuration

### Docker Compose

```yaml
web-dashboard:
  image: web-dashboard:latest
  ports:
    - "3000:3000"
  environment:
    - NEXT_PUBLIC_API_URL=http://api-gateway:8080
  depends_on:
    - api-gateway
```

### Next.js Config (next.config.ts)

```typescript
const nextConfig = {
  // Output: 'standalone' for minimal container size
  // API rewrites for proxying
}
```

---

## Data Visualization

### Dashboard Overview

- Zone status cards (active zones, sensors online)
- Moisture trends chart (line chart)
- Recent irrigation events
- Quick stats (total water used, events today)

### Zone Detail

- Real-time sensor readings
- Temperature and moisture gauges
- Historical data charts
- Irrigation event timeline

### History Page

- Pagination of all irrigation events
- Filter by zone
- Sort by date/status

---

## Authentication Flow

### Login

1. User submits credentials to `/api/auth/login`
2. Backend returns access + refresh tokens (as cookies)
3. Redirect to `/dashboard`

### Protected Routes

All dashboard routes are protected and redirect to `/login` if not authenticated.

### Token Refresh

- Access token expires after 15 minutes
- Automatic refresh via `/api/auth/refresh`
- Refresh token valid for 7 days

---

## Example Usage

### Using the API Client

```typescript
import { api } from '@/lib/api'

// Get zones
const zones = await api.get<Zone[]>('/v1/zones')

// Create zone
await api.post('/v1/zones', {
  zone_name: 'Garden',
  soil_type: 'loam',
  moisture_min: 30,
  moisture_max: 60
})

// Get sensor data
const readings = await api.get<SensorReading[]>(`/v1/zones/${zoneId}/sensors?hours=24`)
```

### Using Hooks

```typescript
import { useZones, useSensorData, useIrrigationEvents } from '@/hooks'

function ZoneDetail({ zoneId }) {
  const { zone, loading } = useZone(zoneId)
  const { readings } = useSensorData(zoneId, 24)
  const { events } = useIrrigationEvents(zoneId, 20)

  return (
    <div>
      <h1>{zone?.zone_name}</h1>
      <Chart data={readings} />
      <EventList events={events} />
    </div>
  )
}
```

---

## Component Library

The dashboard uses shadcn/ui components:
- Button, Card, Input, Select
- Dialog, Dropdown, Popover
- Table, Pagination
- Form components
- Charts (Recharts)

---

## Monitoring

### Development

```bash
npm run dev
# Open http://localhost:3000
```

### Production Build

```bash
npm run build
npm start
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | Next.js 14+ (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| State | Zustand |
| Charts | Recharts |
| API | REST via API Gateway |
| Auth | JWT + Cookies |
| Port | 3000 |

The Web Dashboard provides a complete user interface for monitoring and managing the Smart Irrigation System, with real-time sensor data, predictions display, and irrigation history.