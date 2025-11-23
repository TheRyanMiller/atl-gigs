# AGENTS.md

## Build & Run Commands

### Frontend (React)
- `cd atl-gigs && npm install` - Install dependencies
- `cd atl-gigs && npm run dev` - Start development server (Vite)
- `cd atl-gigs && npm run build` - Type-check and build for production
- `cd atl-gigs && npm run lint` - Run ESLint
- No test framework configured

### Scraper (Python)
- `python -m venv venv` - Create virtual environment
- `source venv/bin/activate` - Activate venv (Windows: `venv\Scripts\activate`)
- `pip install -r requirements.txt` - Install Python dependencies
- `python scrape.py` - Run scraper (outputs to `atl-gigs/public/events.json`)

## Code Style Guidelines

### TypeScript/React
- **TypeScript**: Strict mode enabled with `noUnusedLocals`, `noUnusedParameters`
- **Imports**: External packages first, then local modules; use relative paths (`../types`)
- **Formatting**: Double quotes for JSX attributes and strings; trailing commas
- **Components**: Default exports for React components; PascalCase filenames
- **Types**: Define interfaces in `src/types.ts`; use explicit prop interfaces (e.g., `EventCardProps`)
- **Naming**: PascalCase for components/interfaces, camelCase for variables/functions
- **Error handling**: Use try/catch with `.catch()` for async; set error state for UI feedback
- **Styling**: Tailwind CSS with dark mode support (`dark:` prefix classes)
- **React**: Functional components with hooks; use `useState`/`useEffect` patterns
- **ESLint**: React Hooks plugin enforced; react-refresh for HMR compliance

### Python
- **Dependencies**: Always use venv; add new packages to `requirements.txt`
- **Error handling**: Wrap venue scrapers in try/except; log failures but continue
- **Data normalization**: Use `normalize_time()` and `normalize_price()` helpers
- **Validation**: All events must pass `validate_event()` before saving
