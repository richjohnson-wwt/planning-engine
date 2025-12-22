# Route Planning Engine - Vue.js Frontend

This is the Vue.js frontend for the Route Planning Engine. It provides a web interface for the FastAPI backend.

## 🎨 For WWT IT Team

This frontend is built with **placeholder styling** and is ready for WWT branding. To apply WWT's design system:

1. Install `@wwt/atc-ui-components` (or your internal component library)
2. Replace placeholder components with WWT-branded components
3. Update `src/assets/main.css` with WWT theme variables
4. Apply WWT color scheme, typography, and styling

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm (or yarn/pnpm)
- FastAPI backend running on `http://localhost:8000`

### Installation

```bash
cd apps/web
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

Built files will be in `dist/` directory.

## 📁 Project Structure

```
apps/web/
├── src/
│   ├── assets/          # CSS and static assets
│   ├── components/      # Reusable Vue components
│   │   ├── WorkspaceSelector.vue
│   │   ├── WorkflowSteps.vue
│   │   ├── PlanningForm.vue
│   │   ├── RouteMap.vue
│   │   └── TeamSchedule.vue
│   ├── views/           # Page views
│   │   ├── Home.vue
│   │   ├── Planning.vue
│   │   └── Results.vue
│   ├── router/          # Vue Router configuration
│   ├── services/        # API client for FastAPI
│   │   └── api.js
│   ├── stores/          # Pinia state management
│   │   └── planning.js
│   ├── App.vue          # Root component
│   └── main.js          # App entry point
├── index.html
├── package.json
└── vite.config.js
```

## 🔌 API Integration

The frontend communicates with the FastAPI backend via the API service layer (`src/services/api.js`).

### API Proxy

Vite dev server proxies `/api/*` requests to `http://localhost:8000`:

```javascript
// Example API call
import { planningAPI } from '@/services/api'

const result = await planningAPI.plan(planRequest)
```

### Available API Methods

- `workspaceAPI.create(name)` - Create workspace
- `excelAPI.parse(workspace, state, file)` - Upload Excel
- `geocodeAPI.geocode(workspace, state)` - Geocode addresses
- `clusterAPI.cluster(workspace, state, numClusters)` - Cluster sites
- `planningAPI.plan(planRequest)` - Generate route plan

## 🗺️ Features

### 1. Workspace Management
- Create new workspaces
- Select workspace and state

### 2. Data Pipeline
- Upload Excel files with site addresses
- Geocode addresses to GPS coordinates
- Optional clustering for geographic grouping

### 3. Planning Configuration
- **Fixed Crew Mode**: Set number of teams, calculate end date
- **Fixed Calendar Mode**: Set date range, calculate crews needed
- Configure team workday hours
- Set route parameters (max minutes, service time, breaks)
- Enable/disable clustering

### 4. Results Dashboard
- Summary statistics (sites, team-days, date range)
- Team schedule table with site details
- Map visualization (auto-generated server-side)
- Export JSON results

## 🎨 Styling & Theming

### Current Theme

The app uses a clean, professional theme with:
- Primary color: Navy blue (`#1e3a8a`)
- Neutral grays for text and backgrounds
- Responsive design
- Accessible color contrast

### Applying WWT Branding

Replace the CSS variables in `src/assets/main.css`:

```css
:root {
  --primary-color: #YOUR_PRIMARY_COLOR;
  --primary-hover: #YOUR_HOVER_COLOR;
  /* ... other WWT brand colors */
}
```

Or import WWT's component library and replace components:

```javascript
// Instead of custom components
import { Button, Input, Card } from '@wwt/atc-ui-components'
```

## 📦 State Management

Uses **Pinia** for state management:

```javascript
import { usePlanningStore } from '@/stores/planning'

const store = usePlanningStore()
store.setWorkspace('my-workspace')
store.updatePlanRequest({ teams: 3 })
```

## 🔧 Configuration

### Vite Config

API proxy and build settings in `vite.config.js`:

```javascript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

## 🚀 Deployment

### Option 1: Static Hosting
Build and deploy to Netlify, Vercel, or S3:

```bash
npm run build
# Deploy dist/ folder
```

### Option 2: Serve from FastAPI
Build and serve from FastAPI backend:

```bash
npm run build
# Copy dist/ to FastAPI static folder
```

## 📝 Notes for Development

- **CORS**: Ensure FastAPI has CORS enabled for `http://localhost:5173` during development
- **File Uploads**: Excel file uploads use `multipart/form-data`
- **Date Formats**: Dates use ISO format (`YYYY-MM-DD`)
- **Time Formats**: Times use `HH:MM:SS` format

## 🤝 Contributing

This frontend is designed to be customized by the WWT IT team. Key areas for customization:

1. **Components**: Replace with `@wwt/atc-ui-components`
2. **Styling**: Apply WWT brand colors and typography
3. **Layout**: Adjust to match WWT's design system
4. **Features**: Add additional functionality as needed

## 📄 License

Internal WWT project
