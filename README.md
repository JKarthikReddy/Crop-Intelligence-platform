# Crop Intelligence Platform

AI-powered agricultural intelligence platform for yield forecasting, irrigation optimization, and crop analytics.

## Monorepo Architecture

```
crop-intelligence/
├── frontend/          # Next.js UI layer
├── backend/           # FastAPI + geospatial + DB
├── ml/                # ML training & experiments
├── docker/            # Container configurations
└── .github/
    └── workflows/     # CI/CD automation
```

| Directory | Responsibility | Tech Stack |
|-----------|---------------|------------|
| `frontend/` | UI layer only | Next.js 16, React 19, Tailwind CSS 4, Recharts |
| `backend/` | API + geospatial + DB | FastAPI, GDAL, PostGIS, SQLAlchemy |
| `ml/` | Model training & experiments | PyTorch, scikit-learn, MLflow |
| `docker/` | All container configs | Docker, Docker Compose |
| `.github/` | CI/CD automation | GitHub Actions |

**Architectural boundaries are strict:**
- No ML logic inside `backend/`
- No API logic inside `frontend/`
- No Docker files scattered outside `docker/`

## Quick Start

### Prerequisites

- Node.js >= 18
- Python >= 3.11
- Docker (optional, for containerized setup)

### Frontend

```bash
cd frontend
cp .env.local.example .env.local  # or create manually
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Environment Variables

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:3000/api
```

## Frontend Tech Stack

- **Framework:** Next.js 16 (App Router)
- **UI:** React 19, Tailwind CSS 4
- **Animation:** Framer Motion
- **Charts:** Recharts
- **Icons:** Lucide React
- **Styling:** CVA + clsx + tailwind-merge
- **Testing:** Vitest + React Testing Library
- **Linting:** ESLint 9 + TypeScript strict mode

## Frontend Structure

```
frontend/src/
├── app/
│   ├── api/yield/route.ts      # Mock yield forecast API
│   ├── globals.css              # Global styles + Tailwind
│   ├── layout.tsx               # Root layout with metadata
│   └── page.tsx                 # Main dashboard page
├── components/
│   ├── charts/
│   │   ├── ChartContainer.tsx   # Reusable chart wrapper
│   │   ├── NDVIChart.tsx        # NDVI vegetation index chart
│   │   └── YieldChart.tsx       # Yield forecast line chart
│   ├── layout/
│   │   ├── Navbar.tsx           # Top navigation bar
│   │   └── Sidebar.tsx          # Side navigation
│   └── ui/
│       ├── Button.tsx           # CVA-based button component
│       ├── Card.tsx             # CVA-based card component
│       └── DataStat.tsx         # KPI stat card component
├── lib/
│   ├── motion.ts                # Framer Motion presets
│   └── utils.ts                 # cn() utility (clsx + tailwind-merge)
└── __tests__/
    └── Card.test.tsx            # Component tests
```

## Scripts (Frontend)

```bash
npm run dev        # Start development server
npm run build      # Production build
npm run start      # Start production server
npm run lint       # Run ESLint
npm run test       # Run Vitest tests
npm run test:watch # Run tests in watch mode
```

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready only |
| `dev` | Integration branch |
| `feature/*` | Isolated feature development |

## CI/CD

GitHub Actions workflow runs on every push and PR to `main`:

1. Install dependencies
2. Lint
3. Type check
4. Build

See `.github/workflows/ci.yml` for details.
