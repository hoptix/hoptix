# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IntelUpsell frontend - A Next.js analytics dashboard for viewing drive-thru performance metrics (upselling, upsizing, add-ons). Connects to Flask backend API for data.

## Tech Stack

- **Next.js 15** - App Router architecture
- **TypeScript** - Strict mode enabled
- **React 18** - Server and client components
- **TanStack Query** - Data fetching, caching, synchronization
- **shadcn/ui** - UI component library (new-york style)
- **Tailwind CSS** - Styling with CSS variables
- **Recharts** - Data visualization library
- **date-fns** - Date manipulation
- **jsPDF** & **xlsx** - Export functionality

## Architecture

### Directory Structure

```
app/                    # Next.js App Router pages
  ├── dashboard/        # Main dashboard page
  ├── analytics/        # Detailed analytics views
  ├── items/           # Item-specific analytics
  ├── runs/            # Processing run history
  ├── reports/         # Generated reports
  │   ├── [runId]/    # Single run report
  │   └── range/      # Date range reports
  ├── videos/          # Video footage review
  ├── samples/         # Sample data
  └── login/           # Authentication page

components/            # React components
  ├── ui/             # shadcn/ui components (DO NOT edit directly)
  ├── auth/           # Auth-related components
  ├── chart-area-interactive/ # Chart components
  └── *.tsx           # Business components

contexts/              # React Contexts for global state
  ├── authContext.tsx              # Authentication state
  ├── DashboardFilterContext.tsx   # Dashboard filters (locations, dates)
  └── SidebarLockContext.tsx       # Sidebar UI state

hooks/                 # Custom React hooks
  ├── getLocations.tsx             # Fetch locations
  ├── getRuns.tsx                  # Fetch runs
  ├── getRunAnalytics.tsx          # Fetch run analytics
  ├── useDashboardAnalytics.tsx    # Dashboard metrics
  ├── useTopOperators.tsx          # Top operators
  └── use*.tsx                     # TanStack Query hooks

lib/                   # Utility libraries
  ├── api-client.ts    # Authenticated API client with auto token refresh
  ├── auth-api.ts      # Auth API functions (login, refresh, logout)
  ├── token-storage.ts # localStorage wrapper for refresh tokens
  └── utils.ts         # Utility functions (cn for className merging)

types/                 # TypeScript type definitions
  ├── analytics.ts     # Analytics data types
  └── auth.ts          # Auth-related types
```

### State Management

**React Contexts** for global state:

1. **AuthContext** (`contexts/authContext.tsx`)
   - User authentication state
   - Access token in memory, refresh token in localStorage
   - Auto-refresh on 401 responses
   - Usage: `const { user, isAuthenticated } = useAuth()`

2. **DashboardFilterContext** (`contexts/DashboardFilterContext.tsx`)
   - Location and date range filters
   - Syncs across dashboard views
   - Usage: `const { filters, updateLocationIds, updateDateRange } = useDashboardFilters()`

3. **SidebarLockContext** (`contexts/SidebarLockContext.tsx`)
   - Sidebar open/closed state
   - Usage: `const { isLocked, setIsLocked } = useSidebarLock()`

### Data Fetching Pattern

All data fetching uses **TanStack Query** hooks:

```typescript
// Example hook structure (hooks/useDashboardAnalytics.tsx)
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export function useDashboardAnalytics(params) {
  return useQuery({
    queryKey: ['dashboardAnalytics', ...params],
    queryFn: async () => {
      const response = await apiClient.get('/api/analytics/...')
      return response.data
    },
    enabled: !!someCondition,
    staleTime: 5 * 60 * 1000,  // 5 minutes
  })
}
```

**Important patterns:**
- `queryKey` must include all parameters for proper cache invalidation
- Use `apiClient` (not fetch) for automatic JWT token refresh
- Set `enabled: false` when params are missing
- Configure `staleTime` for caching behavior

### API Client

**lib/api-client.ts** handles all API requests:

- Automatically attaches JWT access token to requests
- Intercepts 401 responses and refreshes token
- Redirects to /login if refresh fails
- Access token stored in memory (not localStorage)
- Refresh token stored in localStorage

```typescript
// Usage in hooks
import { apiClient } from '@/lib/api-client'

const data = await apiClient.get('/api/endpoint')
const result = await apiClient.post('/api/endpoint', { payload })
```

**Never** use `fetch()` directly - always use `apiClient` to ensure proper authentication.

### Component Patterns

**Server vs Client Components:**
- Use Server Components by default (no "use client" directive)
- Add "use client" only when needed:
  - Using hooks (useState, useEffect, useContext)
  - Event handlers (onClick, onChange)
  - Browser APIs (localStorage, window)

**shadcn/ui components:**
- Located in `components/ui/`
- DO NOT modify these files directly
- Use `npx shadcn@latest add <component>` to add new components
- Import with `@/components/ui/<component>`

**Path Aliases:**
```typescript
import { Component } from '@/components/...'
import { useHook } from '@/hooks/...'
import { apiClient } from '@/lib/...'
import type { Type } from '@/types/...'
```

## Common Commands

### Development
```bash
npm run dev         # Start dev server (http://localhost:3000)
npm run build       # Production build
npm run start       # Start production server
npm run lint        # Run ESLint
npm run type-check  # TypeScript type checking
```

### Adding shadcn/ui Components
```bash
npx shadcn@latest add <component-name>
```

## Environment Variables

Required in `.env.local`:

```bash
# Backend API URL
NEXT_PUBLIC_FLASK_API_URL=http://localhost:8000

# Optional: Override in production
# NEXT_PUBLIC_FLASK_API_URL=https://api.production.com
```

**Note:** The API client defaults to `http://localhost:8081` if not set (see lib/api-client.ts:8).

## Key Files

### Configuration
- `tsconfig.json` - TypeScript config with path aliases (`@/*`)
- `tailwind.config.js` - Tailwind CSS config with shadcn theming
- `components.json` - shadcn/ui configuration (new-york style)
- `next.config.js` - Next.js config (standalone output for Docker)

### Core Application
- `app/layout.tsx` - Root layout with Providers and GlobalLayout
- `components/providers.tsx` - Query Client and AuthProvider wrapper
- `components/global-layout.tsx` - App shell with navigation

### Type Definitions
- `types/analytics.ts` - Analytics metrics, daily metrics, chart types
  - Key types: `DailyMetrics`, `CategoryMetrics`, `MetricType`, `CategoryType`
- `types/auth.ts` - User, tokens, login/refresh responses

## Data Flow

1. User logs in → `auth-api.login()` → Tokens stored (access in memory, refresh in localStorage)
2. Component uses hook → TanStack Query hook → `apiClient.get()`
3. API client attaches access token to request
4. If 401 response → Refresh token → Retry request
5. If refresh fails → Redirect to /login
6. Component receives data → Renders UI

## Important Notes

### Authentication
- Access tokens stored in memory (cleared on page refresh)
- Refresh tokens stored in localStorage (persist across sessions)
- Token refresh is automatic via API client
- Manual login required on page refresh (app/page.tsx redirects to /dashboard if authenticated)

### Analytics Metrics
Three main categories tracked:
- **Upsell** - Upgrading items to meals/combos
- **Upsize** - Increasing size (medium → large)
- **Add-on** - Additional toppings/extras

For each category, we track:
- **Opportunities** - How many chances existed
- **Offers** - How many were offered by operator
- **Successes** - How many were accepted by customer
- **Conversion Rate** - `(successes / offers) * 100`
- **Revenue** - Dollar value generated

### UI Components
- Use existing shadcn/ui components from `components/ui/`
- For custom components, create in `components/` (not in `ui/`)
- All components use Tailwind CSS via `className` prop
- Use `cn()` utility from `lib/utils.ts` for conditional classes

### Data Tables
- Large data tables use TanStack Table (`components/data-table.tsx`, `components/runs-data-table.tsx`)
- Include column sorting, filtering, pagination
- Export functionality via CSV/Excel (lib/csv-export.ts)

### Charts
- Built with Recharts (`recharts` package)
- Interactive charts in `components/chart-area-interactive/`
- Use types from `types/analytics.ts` for type safety

### Debugging
- Check Network tab for API calls (should have `Authorization: Bearer <token>`)
- Check Console for TanStack Query devtools (appears in dev mode)
- If 401 errors persist, check token storage in Application tab
- Use React DevTools to inspect context values
