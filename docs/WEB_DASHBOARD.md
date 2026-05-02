# Web Dashboard Architecture & Documentation

The Web Dashboard is the primary user interface for the Smart Irrigation System. It is built using **Next.js 16 (App Router)**, styled with **Tailwind CSS 4** and **shadcn/ui**, and relies exclusively on the **API Gateway** for data access and authentication.

## 🏗 Technology Stack
- **Framework**: Next.js 16 (React 19)
- **Styling**: Tailwind CSS 4 + `shadcn/ui` components
- **State Management**: Zustand (global auth state) + React Context/Hooks (local state)
- **Data Fetching**: Native `fetch` with custom polling hooks, wrapped in an API client
- **Data Visualization**: Recharts (Line charts for moisture/predictions)
- **Forms & Validation**: `react-hook-form` with `zod` schema validation
- **Authentication**: JWT stored in `httpOnly` cookies managed by Next.js Server Actions/API routes.

## 📂 Directory Structure (`src/`)

```text
src/
├── app/                  # Next.js App Router endpoints & pages
│   ├── (auth)/login/     # Login interface
│   ├── (dashboard)/      # Main application layout & protected routes
│   │   ├── dashboard/    # System overview & visualizations
│   │   ├── zones/        # Zone management (CRUD operations)
│   │   ├── history/      # Historical irrigation logs
│   ├── api/auth/         # Server-side route handlers for cookie management
├── components/           # Reusable UI components
│   ├── ui/               # shadcn/ui generic primitives (buttons, dialogs, forms)
│   ├── layout/           # Structural components (Navbar, Sidebar, Page wrappers)
│   ├── dashboard/        # Domain-specific components (ZoneCard, Charts)
├── hooks/                # Custom React hooks (e.g., usePolling, useZones)
├── lib/                  # Utilities, configuration, and API client wrappers
│   └── validations/      # Zod schemas (mirroring Python Pydantic models)
├── store/                # Zustand state stores (e.g., authStore)
├── types/                # TypeScript interfaces (Zone, User, SensorReading)
└── middleware.ts         # Next.js edge middleware for route protection
```

## 🔐 Authentication Flow

The dashboard uses a secure, modern approach to JWT authentication to prevent XSS and CSRF attacks:
1. **Login**: User submits credentials to the Next.js API route (`/api/auth/login`).
2. **Proxy Request**: The Next.js API forwards the credentials to the backend API Gateway (`http://api-gateway:8080/v1/auth/login`).
3. **Cookie Setting**: The API Gateway returns an `access_token` and `refresh_token`. The Next.js API handler sets these as `httpOnly`, `Secure` cookies.
4. **Middleware Protection**: `middleware.ts` intercepts requests to `/(dashboard)/*`. If the `access_token` cookie is missing, the user is redirected to `/login`.
5. **API Client**: The custom API client (`lib/api.ts`) automatically attaches the cookies to backend requests and handles `401 Unauthorized` errors by attempting a token refresh.

## 📊 Real-Time Data (REST Polling)
Due to architectural constraints prioritizing reliability over persistent connections, the dashboard uses **REST Polling** instead of WebSockets.

- **`usePolling` Hook**: Custom hooks periodically fetch data from the API Gateway (e.g., every 10 seconds).
- **Sensor Charts**: `SensorChart.tsx` renders live soil moisture levels, mapping incoming telemetry over time against configured zone thresholds (`moisture_min`, `moisture_max`).
- **Prediction Charts**: `PredictionChart.tsx` visually compares actual moisture readings with the ML model's predictions.

## 🌾 Zone Management (CRUD)
The zone configuration interface allows users and administrators to manage physical irrigation areas.

- **Forms**: Implemented using `react-hook-form` paired with `@hookform/resolvers/zod`.
- **Validation**: Strict client-side validation (`lib/validations/zone.ts`) ensures that forms cannot be submitted if constraints are violated (e.g., `moisture_min` must be less than `moisture_max`).
- **Authorization**: The "Assign Owner" feature in the `EditZoneDialog` is conditionally rendered based on the user's `is_admin` flag, enforcing RBAC at the UI level.

## 🚀 Development & Deployment
The dashboard runs inside a Docker container defined in `docker-compose.app.yml`.

**Local Development Environment Variables:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8080 # Points to the API Gateway
```

**Running Locally (Outside Docker):**
```bash
cd services/web-dashboard
npm install
npm run dev
```
