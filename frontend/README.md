# Strava Trends Frontend

React + TypeScript + Vite frontend for the Strava Trends analytics platform.

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **React Query** for server state management
- **React Router** for navigation
- **Tailwind CSS** for styling
- **Recharts** for data visualization
- **Mapbox GL** for route mapping
- **Axios** for HTTP requests

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000` (or update `VITE_API_URL`)

### Installation

```bash
npm install
```

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` and add your Strava API credentials:

```env
VITE_STRAVA_CLIENT_ID=your_strava_client_id
VITE_STRAVA_REDIRECT_URI=http://localhost:3000/auth/callback
VITE_API_URL=http://localhost:8000
VITE_MAPBOX_TOKEN=your_mapbox_token
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

Vite is configured to proxy `/api` requests to the backend at `http://localhost:8000`.

### Build

Build for production:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

### Linting

Run ESLint:

```bash
npm run lint
```

## Project Structure

```
src/
├── api/              # API client and endpoint functions
│   ├── client.ts     # Axios instance with auth interceptors
│   ├── activities.ts # Activity-related API calls
│   ├── trends.ts     # Trend analytics API calls
│   ├── auth.ts       # Authentication API calls
│   └── routes.ts     # Route-related API calls
├── components/       # Reusable UI components
│   ├── Layout.tsx    # Main app layout with navigation
│   └── StatCard.tsx  # Dashboard stat card component
├── hooks/            # React Query hooks
│   ├── useActivities.ts
│   ├── useTrends.ts
│   ├── useUser.ts
│   └── useRoutes.ts
├── pages/            # Route page components
│   ├── Dashboard.tsx # Overview dashboard
│   ├── Activities.tsx# Activity list and details
│   ├── Trends.tsx    # Trend analytics
│   ├── RouteMap.tsx  # Route visualization
│   └── Login.tsx     # Strava OAuth login
├── types/            # TypeScript type definitions
│   └── index.ts
├── utils/            # Utility functions
│   ├── format.ts     # Data formatting helpers
│   └── classnames.ts # CSS class merging
├── App.tsx           # Main app component with routing
├── main.tsx          # App entry point
└── index.css         # Global styles
```

## Authentication Flow

1. User clicks "Connect with Strava" on the Login page
2. Redirected to Strava OAuth authorization
3. Strava redirects back with authorization code
4. Frontend exchanges code for access token via backend
5. Token stored in localStorage
6. Subsequent API requests include token in Authorization header

## API Integration

All API calls go through the Axios client in `src/api/client.ts`, which:
- Adds auth token from localStorage to requests
- Handles 401 responses by clearing token and redirecting to login
- Proxies requests to backend via Vite dev server

React Query hooks in `src/hooks/` handle:
- Caching and refetching
- Loading and error states
- Optimistic updates
- Query invalidation after mutations

## Styling

Tailwind CSS is configured with custom colors:
- `strava-orange`: #FC4C02 (Strava brand color)
- Custom spacing and typography

Use the `cn()` utility from `utils/classnames.ts` to merge conditional classes:

```tsx
import { cn } from '../utils/classnames'

<div className={cn('base-class', isActive && 'active-class')} />
```

## Data Visualization

- **Recharts** for trend charts (line, bar, area charts)
- **Mapbox GL** for route maps and GPS visualization
- **Plotly** for advanced statistical visualizations

## Deployment

Build output goes to `dist/` directory. Deploy to any static hosting service:

- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages

Make sure to configure environment variables in your hosting platform.
