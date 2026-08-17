# UC10 Frontend - React

Professional React dashboard for UC10 anomaly detection results.

## Quick Start

```bash
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

## Project Structure

```
frontend/
├── src/
│   ├── main.jsx                   # React entry point
│   ├── App.jsx                    # Main component
│   ├── App.css                    # App styling
│   ├── index.css                  # Global styles
│   ├── pages/
│   │   ├── Upload.jsx             # File upload page
│   │   ├── Upload.css
│   │   ├── Dashboard.jsx          # Results dashboard
│   │   └── Dashboard.css
│   ├── components/
│   │   ├── SummaryCards.jsx       # Summary statistics cards
│   │   ├── SummaryCards.css
│   │   ├── AnomaliesTable.jsx     # Anomalies table
│   │   ├── AnomaliesTable.css
│   │   ├── Filters.jsx            # Severity filter & search
│   │   ├── Filters.css
│   │   ├── AnomalyDetail.jsx      # Anomaly detail modal
│   │   └── AnomalyDetail.css
│   ├── services/
│   │   └── api.js                 # API client (axios)
│   ├── hooks/
│   │   └── useStore.js            # Zustand store
│   └── types/
│       └── constants.js           # TypeScript-style constants
├── package.json
├── vite.config.js
├── index.html
└── .env.example
```

## Pages

### Upload Page
- Drag-and-drop file upload
- File validation (type, size)
- Processing stage indicators
- Error messages
- Beautiful gradient background

### Dashboard Page
- Summary cards (records, anomalies, by severity)
- Anomalies table with sortable/searchable columns
- Severity filter buttons (ALL, HIGH, MEDIUM, LOW)
- Search input (by record ID, type, anomaly type)
- Pagination controls
- Download results as CSV
- Anomaly detail modal on click

## Components

### SummaryCards
Displays key statistics:
- Total records
- Total anomalies
- HIGH count (red accent)
- MEDIUM count (orange accent)
- LOW count (green accent)

### AnomaliesTable
Interactive table with:
- Priority badge (color-coded)
- Record ID (monospace code formatting)
- Record type badge
- Severity badge
- Anomaly type
- Primary signal (truncated with tooltip)
- Confidence percentage
- View button to open detail modal

### Filters
Search and filter controls:
- Severity buttons (ALL, HIGH, MEDIUM, LOW)
- Search input field
- Download results button
- Responsive layout

### AnomalyDetail
Full-screen modal with:
- Close button
- Key information grid
- Why was it flagged section
- Root cause section
- Recommended action section
- Business impact section
- Additional checks section
- Technical details (JSON)
- Footer with close button

## Services

### api.js
Axios API client with:
- Base URL configuration
- Error interceptors
- Functions for all endpoints:
  - `uploadAndAnalyze(file)` - POST /api/analyze
  - `getRunInfo(runId)` - GET /api/runs/{run_id}
  - `getAnomalies(runId, options)` - GET /api/runs/{run_id}/anomalies
  - `getAnomalyDetail(anomalyId)` - GET /api/anomalies/{anomaly_id}
  - `downloadResults(runId, options)` - GET /api/runs/{run_id}/download
  - `healthCheck()` - GET /api/health

## State Management

### Zustand Store (useStore.js)
Lightweight state management:
- `currentRun` - Current analysis run
- `anomalies` - List of anomalies
- `page`, `pageSize` - Pagination
- `totalAnomalies` - Total count
- `severityFilter` - Current filter
- `searchQuery` - Search query
- `isLoading`, `isUploading` - Loading states
- `error` - Error message
- `selectedAnomaly` - Detail modal state
- `statistics` - Run statistics
- `reset()` - Clear all state

Usage:
```javascript
const currentRun = useStore(state => state.currentRun)
const setCurrentRun = useStore(state => state.setCurrentRun)
```

## Styling

### Global Styles (index.css)
- Typography
- Colors
- Severity badges
- Priority badges
- Utility classes
- Loading spinner
- Scrollbar styling

### Component Styles
Each component has a corresponding `.css` file with:
- Component-specific styling
- Hover/active states
- Responsive media queries
- Color coding for severity/priority

### Color Scheme
- Primary: #667eea (indigo)
- Secondary: #764ba2 (purple)
- Success: #388e3c (green)
- Warning: #f57c00 (orange)
- Error: #d32f2f (red)

## Features

- ✅ Drag-and-drop file upload
- ✅ Processing stage indicators
- ✅ Summary statistics
- ✅ Sortable/searchable table
- ✅ Severity filtering
- ✅ Pagination
- ✅ Anomaly detail modal
- ✅ Download results as CSV
- ✅ Responsive design
- ✅ Professional UI
- ✅ Business-friendly language
- ✅ Error handling
- ✅ Loading states

## Configuration

Create `.env.local` (copy from `.env.example`):
```
VITE_API_URL=http://localhost:8000/api
```

## Development

### Install dependencies
```bash
npm install
```

### Run dev server
```bash
npm run dev
```

### Build for production
```bash
npm run build
```

### Preview production build
```bash
npm run preview
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Modern browsers (ES2020+)

## Dependencies

See `package.json`:
- `react` - UI framework
- `react-dom` - React DOM binding
- `axios` - HTTP client
- `zustand` - State management

## Build Tool

- `vite` - Fast build tool and dev server
- `@vitejs/plugin-react` - React plugin

## Performance

- Client-side filtering: Pagination handled server-side
- Component memoization: Avoid unnecessary re-renders
- Lazy loading: Data loaded as needed
- Efficient state updates: Zustand subscription
- CSS modules: Scoped styling

## Responsive Design

Breakpoints:
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

Components adapt layout at each breakpoint for optimal viewing.

## Accessibility

- Semantic HTML
- ARIA labels where appropriate
- Keyboard navigation support
- Color contrast meeting WCAG standards
- Focus states on interactive elements

## Error Handling

- Invalid file type alert
- File size validation
- Network error display
- API error messages
- User-friendly messaging

## Testing

To manually test:

1. Upload a CSV/XLSX file
2. Wait for analysis to complete
3. Verify summary cards
4. Test severity filters
5. Search for a record ID
6. Click "View" on an anomaly
7. Check all fields in detail modal
8. Download results
9. Test pagination

## Debugging

### Console Logs
- API calls logged to browser console
- State changes can be logged in useStore.js
- Component renders can be tracked

### Browser DevTools
- React Components tab (install React DevTools browser extension)
- Network tab to see API calls
- Storage tab to inspect local/session storage

### Network Request Debugging
All API calls go through `services/api.js` and can be intercepted there.

## Deployment

### Static Build
```bash
npm run build
# Output in dist/ folder
```

### Deploy to CDN/Server
```bash
# Copy dist/ contents to your server
scp -r dist/* user@server:/var/www/html
```

### Docker Example
```dockerfile
FROM node:16-alpine as builder
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

## Troubleshooting

### API connection error
- Check backend is running on http://localhost:8000
- Check VITE_API_URL in .env.local
- Check browser console for CORS errors

### File upload fails
- Check file size (< 100MB)
- Check file format (.csv, .xls, .xlsx)
- Check backend logs for validation errors

### Data not appearing
- Check browser Network tab for API response
- Verify backend has data in SQLite
- Check pagination - data might be on another page

## Future Enhancements

- [ ] Add charts and visualizations
- [ ] Add bulk operations (select multiple)
- [ ] Add anomaly status tracking (OPEN, INVESTIGATING, RESOLVED)
- [ ] Add comment/notes functionality
- [ ] Add export to Excel/PDF
- [ ] Add anomaly history/versioning
- [ ] Add dark mode
- [ ] Add user preferences
- [ ] Add advanced filtering/facets
- [ ] Add anomaly recommendations engine

---

For detailed integration guide, see `INTEGRATION_GUIDE.md` in project root.
